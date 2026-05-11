"""
GDELT DOC API client — multi-domain-confirmed news signals.

worldmonitor.app pricing made the previous integration unworkable.
GDELT v2 DOC is free and public (no auth) but has no documented rate limit
and returns HTTP 429 under load; this client applies exponential backoff
with jitter to stay polite.

A single article from one outlet is noise. We only count a pack as
confirmed when articles from ``min_unique_domains`` distinct domains appear
within a ``window_minutes`` time window — see :func:`confirm_articles`.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from .keyword_packs import DEFAULT_PACKS, KeywordPack

logger = logging.getLogger(__name__)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
USER_AGENT = "Trade-Claw/0.3 (+https://github.com/misteraufumwegen/Trade-Claw)"


@dataclass(frozen=True)
class GdeltArticle:
    title: str
    url: str
    domain: str
    seendate: datetime  # tz-aware UTC
    sourcecountry: str | None = None
    language: str | None = None

    @staticmethod
    def from_api(item: dict) -> GdeltArticle | None:
        raw = item.get("seendate", "")
        try:
            ts = datetime.strptime(str(raw), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except (TypeError, ValueError):
            logger.debug("GDELT article without parseable seendate: %r", raw)
            return None
        return GdeltArticle(
            title=(item.get("title") or "").strip(),
            url=str(item.get("url") or "").strip(),
            domain=str(item.get("domain") or "").strip().lower(),
            seendate=ts,
            sourcecountry=item.get("sourcecountry") or None,
            language=item.get("language") or None,
        )


@dataclass
class GdeltClient:
    """Polls GDELT DOC artlist for each keyword pack with backoff."""

    packs: tuple[KeywordPack, ...] = DEFAULT_PACKS
    timespan: str = "1h"
    maxrecords: int = 50
    timeout_seconds: float = 10.0
    max_retries: int = 3
    transport: httpx.AsyncBaseTransport | None = None  # test injection

    def _build_client(self) -> httpx.AsyncClient:
        kwargs: dict = {
            "timeout": self.timeout_seconds,
            "headers": {"User-Agent": USER_AGENT},
        }
        if self.transport is not None:
            kwargs["transport"] = self.transport
        return httpx.AsyncClient(**kwargs)

    async def fetch_pack(self, pack: KeywordPack) -> list[GdeltArticle]:
        params = {
            "query": pack.gdelt_query,
            "mode": "ArtList",
            "maxrecords": str(self.maxrecords),
            "timespan": self.timespan,
            "sort": "DateDesc",
            "format": "json",
        }
        last_status: int | None = None
        for attempt in range(self.max_retries):
            try:
                async with self._build_client() as client:
                    resp = await client.get(GDELT_DOC_URL, params=params)
                last_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    body = resp.text.strip()
                    if not body:
                        return []
                    try:
                        data = resp.json()
                    except ValueError:
                        logger.warning("GDELT pack=%r returned non-JSON body", pack.name)
                        return []
                    items = data.get("articles", []) if isinstance(data, dict) else []
                    parsed = [GdeltArticle.from_api(i) for i in items]
                    return [a for a in parsed if a is not None]
                if resp.status_code in (429, 500, 502, 503, 504):
                    delay = (2**attempt) + random.uniform(0, 1)  # noqa: S311 (jitter, not crypto)
                    logger.warning(
                        "GDELT %s for pack=%r, retrying in %.1fs (%d/%d)",
                        resp.status_code,
                        pack.name,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.warning("GDELT %s for pack=%r — not retryable", resp.status_code, pack.name)
                return []
            except httpx.HTTPError as exc:
                delay = (2**attempt) + random.uniform(0, 1)  # noqa: S311 (jitter, not crypto)
                logger.warning(
                    "GDELT %s for pack=%r, retrying in %.1fs: %s",
                    type(exc).__name__,
                    pack.name,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        logger.warning(
            "GDELT poll gave up on pack=%r after %d attempts (last_status=%s)",
            pack.name,
            self.max_retries,
            last_status,
        )
        return []

    async def fetch_all(self) -> dict[str, list[GdeltArticle]]:
        results: dict[str, list[GdeltArticle]] = {}
        for pack in self.packs:
            results[pack.name] = await self.fetch_pack(pack)
            await asyncio.sleep(0.5)  # tiny inter-pack delay, be polite
        return results


def confirm_articles(
    articles: list[GdeltArticle],
    min_unique_domains: int = 2,
    window_minutes: int = 60,
    now: datetime | None = None,
) -> list[GdeltArticle]:
    """Return the recent subset of articles, but only if at least
    ``min_unique_domains`` distinct domains are present within the window.

    Empty list means "not yet confirmed" — caller should not emit a signal.
    """
    if not articles:
        return []
    if now is None:
        now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=window_minutes)
    recent = [a for a in articles if a.seendate >= cutoff]
    domains = {a.domain for a in recent if a.domain}
    if len(domains) < min_unique_domains:
        return []
    return recent
