"""
Macro Event Store — categories, dataclass, and in-memory event store.

History note: This module used to call ``worldmonitor.app`` directly; that
provider became too expensive for a single-user setup, so the live feed now
comes from GDELT (multi-source-confirmed news) and GDACS (structured natural
disasters). See :mod:`app.macro.gdelt_client` and :mod:`app.macro.gdacs_client`.

What lives here:
- ``EventCategory`` / ``EventImpact`` / ``EventDirection`` enums.
- ``MacroEvent`` dataclass (naive-UTC timestamps for legacy reasons).
- ``MacroEventFetcher`` — in-memory dedup store + JSON cache + historical
  seed events used by the backtest simulator.
- ``poll_live_events`` — runs one GDELT + GDACS polling cycle and pushes
  events into the store. Called by the lifespan loop in
  :mod:`app.main`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class EventCategory(Enum):
    """Macro event categories."""

    MONETARY_POLICY = "Monetary Policy"
    FISCAL_POLICY = "Fiscal Policy"
    GEOPOLITICAL = "Geopolitical"
    ECONOMIC_DATA = "Economic Data"
    ON_CHAIN = "On-Chain"


class EventImpact(Enum):
    """Event market impact level."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EventDirection(Enum):
    """Event direction bias."""

    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


@dataclass
class MacroEvent:
    """Single macro event record. Timestamps are naive UTC."""

    event_id: str
    category: EventCategory
    title: str
    description: str
    timestamp: datetime
    impact: EventImpact
    direction: EventDirection

    source: str = "manual"
    assets_affected: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)

    forecast_value: float | None = None
    actual_value: float | None = None
    previous_value: float | None = None

    risk_on_support: bool = False
    risk_off_support: bool = False
    volatility_expected: bool = False

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "impact": self.impact.value,
            "direction": self.direction.value,
            "source": self.source,
            "assets_affected": self.assets_affected,
            "countries": self.countries,
            "forecast_value": self.forecast_value,
            "actual_value": self.actual_value,
            "previous_value": self.previous_value,
            "risk_on_support": self.risk_on_support,
            "risk_off_support": self.risk_off_support,
            "volatility_expected": self.volatility_expected,
            "created_at": self.created_at.isoformat(),
        }


class MacroEventFetcher:
    """In-memory event store with dedup, JSON cache, and historical seed."""

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.events: list[MacroEvent] = []
        self._seen_event_ids: set[str] = set()
        self.cache_path = Path(__file__).parent / "historical_events.json"

        logger.info("MacroEventFetcher initialized (cache=%s)", self.cache_path)
        self._load_historical_events()

    # -- core store ----------------------------------------------------------

    def add_event(self, event: MacroEvent) -> bool:
        """Append an event if its event_id has not been seen.

        Returns True when the event was new, False when it was a duplicate.
        """
        if event.event_id in self._seen_event_ids:
            return False
        self._seen_event_ids.add(event.event_id)
        self.events.append(event)
        return True

    def get_events_by_category(self, category: EventCategory) -> list[MacroEvent]:
        return [e for e in self.events if e.category == category]

    def get_events_by_date_range(self, start: datetime, end: datetime) -> list[MacroEvent]:
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_events_for_backtest(self, start_date: datetime, end_date: datetime) -> list[MacroEvent]:
        return self.get_events_by_date_range(start_date, end_date)

    def get_live_feed(self) -> list[MacroEvent]:
        """Events from the last 7 days."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        return self.get_events_by_date_range(cutoff, datetime.utcnow())

    # -- live polling --------------------------------------------------------

    async def poll_live_events(
        self,
        gdelt_client=None,
        gdacs_client=None,
        min_confirmations: int = 2,
        confirmation_window_minutes: int = 60,
    ) -> dict[str, int]:
        """Run one polling cycle against GDELT and GDACS.

        Returns a small stats dict like ``{"gdelt_new": 2, "gdacs_new": 4}``
        so callers/tests can verify activity. Quiet polls return zeros.

        Either client may be ``None`` to disable that source.
        """
        # Local imports to keep import-time light and let tests stub easily.
        from .gdacs_client import GdacsClient
        from .gdelt_client import GdeltClient, confirm_articles
        from .normalizer import gdacs_to_macro_event, gdelt_pack_to_macro_event

        gdelt_new = 0
        gdacs_new = 0

        if isinstance(gdelt_client, GdeltClient):
            try:
                results = await gdelt_client.fetch_all()
                for pack in gdelt_client.packs:
                    arts = results.get(pack.name, [])
                    confirmed = confirm_articles(
                        arts,
                        min_unique_domains=min_confirmations,
                        window_minutes=confirmation_window_minutes,
                    )
                    event = gdelt_pack_to_macro_event(pack, confirmed)
                    if event and self.add_event(event):
                        gdelt_new += 1
            except Exception:  # noqa: BLE001
                logger.exception("GDELT poll cycle failed")

        if isinstance(gdacs_client, GdacsClient):
            try:
                records = await gdacs_client.fetch_recent()
                for r in records:
                    event = gdacs_to_macro_event(r)
                    if self.add_event(event):
                        gdacs_new += 1
            except Exception:  # noqa: BLE001
                logger.exception("GDACS poll cycle failed")

        return {"gdelt_new": gdelt_new, "gdacs_new": gdacs_new}

    # -- persistence helpers -------------------------------------------------

    def save_events_to_cache(self) -> None:
        try:
            data = {
                "events": [e.to_dict() for e in self.events],
                "cached_at": datetime.utcnow().isoformat(),
            }
            with open(self.cache_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("Saved %d events to cache", len(self.events))
        except OSError as exc:
            logger.error("Cache save failed: %s", exc)

    # -- internals -----------------------------------------------------------

    def _load_historical_events(self) -> None:
        if not self.cache_path.exists():
            logger.warning("No historical events cache at %s — seeding mock", self.cache_path)
            self._seed_mock_historical_events()
            return
        try:
            with open(self.cache_path) as f:
                data = json.load(f)
            for event_data in data.get("events", []):
                event = self._parse_event_dict(event_data)
                if event:
                    self.add_event(event)
            logger.info("Loaded %d historical events from cache", len(self.events))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Cache load failed: %s", exc)

    def _seed_mock_historical_events(self) -> None:
        """Hardcoded landmark events used as backtest seed data on first run."""
        mock_events = [
            {
                "event_id": "BTC_HALVING_2016",
                "category": EventCategory.ON_CHAIN.value,
                "title": "Bitcoin Halving",
                "description": "Bitcoin block reward halved from 25 to 12.5 BTC",
                "timestamp": datetime(2016, 7, 9),
                "impact": EventImpact.CRITICAL.value,
                "direction": EventDirection.BULLISH.value,
                "assets_affected": ["BTC"],
                "risk_on_support": True,
                "volatility_expected": True,
            },
            {
                "event_id": "BTC_HALVING_2020",
                "category": EventCategory.ON_CHAIN.value,
                "title": "Bitcoin Halving",
                "description": "Bitcoin block reward halved from 12.5 to 6.25 BTC",
                "timestamp": datetime(2020, 5, 11),
                "impact": EventImpact.CRITICAL.value,
                "direction": EventDirection.BULLISH.value,
                "assets_affected": ["BTC"],
                "risk_on_support": True,
                "volatility_expected": True,
            },
            {
                "event_id": "BTC_HALVING_2024",
                "category": EventCategory.ON_CHAIN.value,
                "title": "Bitcoin Halving",
                "description": "Bitcoin block reward halved from 6.25 to 3.125 BTC",
                "timestamp": datetime(2024, 4, 19),
                "impact": EventImpact.CRITICAL.value,
                "direction": EventDirection.BULLISH.value,
                "assets_affected": ["BTC"],
                "risk_on_support": True,
                "volatility_expected": True,
            },
            {
                "event_id": "UKRAINE_WAR_START",
                "category": EventCategory.GEOPOLITICAL.value,
                "title": "Russia Invades Ukraine",
                "description": "Russia launches military invasion of Ukraine",
                "timestamp": datetime(2022, 2, 24),
                "impact": EventImpact.CRITICAL.value,
                "direction": EventDirection.BEARISH.value,
                "countries": ["RU", "UA", "EU"],
                "assets_affected": ["BTC", "GLD", "JPY"],
                "risk_off_support": True,
                "volatility_expected": True,
            },
            {
                "event_id": "ETH_SHANGHAI",
                "category": EventCategory.ON_CHAIN.value,
                "title": "Ethereum Shanghai Upgrade",
                "description": "Ethereum enables staking withdrawals",
                "timestamp": datetime(2023, 4, 12),
                "impact": EventImpact.HIGH.value,
                "direction": EventDirection.BULLISH.value,
                "assets_affected": ["ETH"],
                "risk_on_support": True,
                "volatility_expected": True,
            },
        ]

        for event_data in mock_events:
            event = self._parse_event_dict(event_data)
            if event:
                self.add_event(event)
        logger.info("Seeded %d mock historical events", len(self.events))

    def _parse_event_dict(self, data: dict) -> MacroEvent | None:
        try:
            return MacroEvent(
                event_id=data.get("event_id", "UNKNOWN"),
                category=EventCategory(data.get("category", "Economic Data")),
                title=data.get("title", ""),
                description=data.get("description", ""),
                timestamp=self._parse_datetime(data.get("timestamp")),
                impact=EventImpact(data.get("impact", "Medium")),
                direction=EventDirection(data.get("direction", "Neutral")),
                source=data.get("source", "manual"),
                assets_affected=data.get("assets_affected", []),
                countries=data.get("countries", []),
                forecast_value=data.get("forecast_value"),
                actual_value=data.get("actual_value"),
                previous_value=data.get("previous_value"),
                risk_on_support=data.get("risk_on_support", False),
                risk_off_support=data.get("risk_off_support", False),
                volatility_expected=data.get("volatility_expected", False),
            )
        except (ValueError, KeyError) as exc:
            logger.error("Error parsing event: %s", exc)
            return None

    @staticmethod
    def _parse_datetime(dt_str) -> datetime:
        if isinstance(dt_str, datetime):
            return dt_str
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return datetime.utcnow()
