"""
Normalisers — convert raw GDELT/GDACS records into the shared
:class:`MacroEvent` shape that the rest of the app (filter, scorer, endpoints,
autopilot grader) already consumes.

MacroEvent stores naive UTC timestamps for historical compatibility with the
older worldmonitor.app-based code, so we strip ``tzinfo`` at the boundary.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime

from .event_fetcher import EventCategory, EventDirection, EventImpact, MacroEvent
from .gdacs_client import GdacsRecord
from .gdelt_client import GdeltArticle
from .keyword_packs import KeywordPack

logger = logging.getLogger(__name__)


_ALERT_TO_IMPACT = {
    "Red": EventImpact.CRITICAL,
    "Orange": EventImpact.HIGH,
    "Green": EventImpact.MEDIUM,
}

# Heuristic mapping eventtype → which markets typically move.
# Refine these by backtest evidence; today they are first-principles guesses.
_GDACS_TYPE_TO_ASSETS: dict[str, tuple[str, ...]] = {
    "EQ": ("GLD", "JPY", "USD"),
    "TC": ("CL", "BZ", "NG", "USD"),
    "FL": ("CORN", "WEAT", "SOYB"),
    "VO": ("USD", "GLD"),
    "TS": ("GLD", "JPY", "USD"),
    "DR": ("CORN", "WEAT", "SOYB"),
    "WF": ("CL", "USD"),
}

_GDACS_TYPE_TO_LABEL = {
    "EQ": "Earthquake",
    "TC": "Tropical Cyclone",
    "FL": "Flood",
    "VO": "Volcanic Activity",
    "TS": "Tsunami",
    "DR": "Drought",
    "WF": "Wildfire",
}


def _to_naive_utc(dt: datetime) -> datetime:
    """Strip tzinfo (assumes input is already UTC)."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def gdacs_to_macro_event(r: GdacsRecord) -> MacroEvent:
    impact = _ALERT_TO_IMPACT.get(r.alertlevel, EventImpact.MEDIUM)
    label = _GDACS_TYPE_TO_LABEL.get(r.eventtype, r.eventtype or "Event")
    title = f"{label}: {r.eventname or r.country or 'Unknown'}".strip()
    countries = [r.country] if r.country else []
    return MacroEvent(
        event_id=f"gdacs-{r.eventtype}-{r.eventid}-{r.episodeid}",
        category=EventCategory.GEOPOLITICAL,
        title=title,
        description=r.description or label,
        timestamp=_to_naive_utc(r.fromdate),
        impact=impact,
        direction=EventDirection.BEARISH,
        source="gdacs",
        assets_affected=list(_GDACS_TYPE_TO_ASSETS.get(r.eventtype, ("USD",))),
        countries=countries,
        risk_off_support=True,
        volatility_expected=impact in (EventImpact.CRITICAL, EventImpact.HIGH),
    )


def gdelt_pack_to_macro_event(
    pack: KeywordPack,
    confirmed_articles: list[GdeltArticle],
) -> MacroEvent | None:
    """Aggregate a confirmed batch of GDELT articles into one MacroEvent.

    Caller should pass the output of :func:`confirm_articles`; this returns
    ``None`` when the batch is empty.
    """
    if not confirmed_articles:
        return None

    ts = max(a.seendate for a in confirmed_articles)
    domains = sorted({a.domain for a in confirmed_articles if a.domain})
    n = len(domains)

    if n >= 5:
        impact = EventImpact.CRITICAL
    elif n >= 3:
        impact = EventImpact.HIGH
    else:
        impact = EventImpact.MEDIUM

    # Stable id: pack + hourly bucket + domain fingerprint. Same news cluster
    # within an hour stays the same id, so the fetcher deduplicates re-poll
    # results naturally.
    bucket = ts.strftime("%Y%m%dT%H")
    fingerprint = "|".join(domains[:5])
    digest = hashlib.sha1(
        f"{pack.name}-{bucket}-{fingerprint}".encode(), usedforsecurity=False
    ).hexdigest()[:12]
    eid = f"gdelt-{pack.name}-{digest}"

    countries = sorted({a.sourcecountry for a in confirmed_articles if a.sourcecountry})

    return MacroEvent(
        event_id=eid,
        category=pack.category,
        title=f"{pack.description} ({n} sources)",
        description="Confirmed via: " + ", ".join(domains[:5]) + ("…" if len(domains) > 5 else ""),
        timestamp=_to_naive_utc(ts),
        impact=impact,
        direction=pack.default_direction,
        source="gdelt",
        assets_affected=list(pack.assets_affected),
        countries=countries,
        risk_on_support=pack.risk_on_support,
        risk_off_support=pack.risk_off_support,
        volatility_expected=pack.volatility_expected,
    )
