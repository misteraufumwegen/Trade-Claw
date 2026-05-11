"""
GDACS event client — structured natural-disaster signals.

GDACS gives us pre-prioritised hazard events (earthquakes, tropical cyclones,
floods, volcanic activity, etc.) with alert levels and geometries. Compared to
GDELT's free-text news search this is the lower-noise, higher-precision feed
for catastrophe-driven trades.

We poll the SEARCH endpoint with a Red+Orange filter by default. Dedupe is
done by the caller via ``event_id`` (we mint a stable id from
``eventtype-eventid-episodeid``).
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

GDACS_SEARCH_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
USER_AGENT = "Trade-Claw/0.3 (+https://github.com/misteraufumwegen/Trade-Claw)"

# Hazard codes: Earthquake, Tropical Cyclone, Flood, Volcano, Tsunami,
# Drought, Wildfire.
DEFAULT_HAZARDS: tuple[str, ...] = ("EQ", "TC", "FL", "VO", "TS", "DR", "WF")


@dataclass(frozen=True)
class GdacsRecord:
    eventid: int
    episodeid: int
    eventtype: str
    eventname: str
    description: str
    alertlevel: str  # "Red" | "Orange" | "Green"
    alertscore: float
    fromdate: datetime  # tz-aware UTC
    todate: datetime | None
    datemodified: datetime
    country: str | None
    iso3: str | None
    coordinates: tuple[float, float] | None  # (lon, lat)
    severity: float | None
    severitytext: str | None

    @staticmethod
    def from_geojson_feature(feat: dict) -> GdacsRecord | None:
        try:
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            coords = None
            if geom.get("type") == "Point":
                pt = geom.get("coordinates") or []
                if len(pt) >= 2:
                    coords = (float(pt[0]), float(pt[1]))
            sev = props.get("severitydata") or {}
            return GdacsRecord(
                eventid=int(props["eventid"]),
                episodeid=int(props.get("episodeid", 0)),
                eventtype=str(props.get("eventtype", "")),
                eventname=str(props.get("eventname") or props.get("name") or ""),
                description=str(props.get("description") or ""),
                alertlevel=str(props.get("alertlevel", "Green")),
                alertscore=float(props.get("alertscore", 0.0)),
                fromdate=_parse_iso(props.get("fromdate"), default_now=True),  # type: ignore[arg-type]
                todate=_parse_iso(props.get("todate"), default_now=False),
                datemodified=_parse_iso(props.get("datemodified"), default_now=True),  # type: ignore[arg-type]
                country=props.get("country") or None,
                iso3=props.get("iso3") or None,
                coordinates=coords,
                severity=(float(sev["severity"]) if sev.get("severity") is not None else None),
                severitytext=sev.get("severitytext") or None,
            )
        except (KeyError, TypeError, ValueError):
            logger.debug("Could not parse GDACS feature: %r", feat)
            return None


def _parse_iso(value, *, default_now: bool) -> datetime | None:
    """Parse GDACS ISO-ish dates. Returns tz-aware UTC, or None when
    ``default_now`` is False and the input is missing."""
    if value is None or value == "":
        return datetime.now(UTC) if default_now else None
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (TypeError, ValueError):
        return datetime.now(UTC) if default_now else None


@dataclass
class GdacsClient:
    hazards: tuple[str, ...] = DEFAULT_HAZARDS
    alert_levels: tuple[str, ...] = ("Red", "Orange")
    timeout_seconds: float = 10.0
    max_retries: int = 3
    days_back: int = 7
    transport: httpx.AsyncBaseTransport | None = None  # test injection

    def _build_client(self) -> httpx.AsyncClient:
        kwargs: dict = {
            "timeout": self.timeout_seconds,
            "headers": {"User-Agent": USER_AGENT},
        }
        if self.transport is not None:
            kwargs["transport"] = self.transport
        return httpx.AsyncClient(**kwargs)

    async def fetch_recent(self) -> list[GdacsRecord]:
        today = datetime.now(UTC).date()
        params = {
            "eventlist": ";".join(self.hazards),
            "fromdate": (today - timedelta(days=self.days_back)).isoformat(),
            "todate": today.isoformat(),
            "alertlevel": ";".join(self.alert_levels),
        }
        last_status: int | None = None
        for attempt in range(self.max_retries):
            try:
                async with self._build_client() as client:
                    resp = await client.get(GDACS_SEARCH_URL, params=params)
                last_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    body = resp.text.strip()
                    if not body:
                        return []
                    try:
                        data = resp.json()
                    except ValueError:
                        logger.warning("GDACS returned non-JSON body")
                        return []
                    feats = data.get("features", []) if isinstance(data, dict) else []
                    parsed = [GdacsRecord.from_geojson_feature(f) for f in feats]
                    return [r for r in parsed if r is not None]
                if resp.status_code in (429, 500, 502, 503, 504):
                    delay = (2**attempt) + random.uniform(0, 1)  # noqa: S311 (jitter, not crypto)
                    logger.warning(
                        "GDACS %s, retrying in %.1fs (%d/%d)",
                        resp.status_code,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.warning("GDACS %s — not retryable", resp.status_code)
                return []
            except httpx.HTTPError as exc:
                delay = (2**attempt) + random.uniform(0, 1)  # noqa: S311 (jitter, not crypto)
                logger.warning(
                    "GDACS %s, retrying in %.1fs: %s",
                    type(exc).__name__,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        logger.warning(
            "GDACS poll gave up after %d attempts (last_status=%s)",
            self.max_retries,
            last_status,
        )
        return []
