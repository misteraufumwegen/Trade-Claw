"""
Tests for the GDELT/GDACS → MacroEvent normalizers and the in-memory
event store dedup behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.macro import (
    DEFAULT_PACKS,
    EventCategory,
    EventImpact,
    GdacsRecord,
    GdeltArticle,
    MacroEventFetcher,
    gdacs_to_macro_event,
    gdelt_pack_to_macro_event,
    get_pack,
)

# ---------------------------------------------------------------------------
# GDACS normalizer
# ---------------------------------------------------------------------------


def _gdacs_record(alertlevel="Orange", eventtype="EQ", eventid=42):
    return GdacsRecord(
        eventid=eventid,
        episodeid=1,
        eventtype=eventtype,
        eventname="Test",
        description="An event",
        alertlevel=alertlevel,
        alertscore=2.0,
        fromdate=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
        todate=None,
        datemodified=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
        country="Japan",
        iso3="JPN",
        coordinates=(143.0, 39.9),
        severity=7.4,
        severitytext="M 7.4",
    )


def test_gdacs_red_maps_to_critical():
    ev = gdacs_to_macro_event(_gdacs_record(alertlevel="Red"))
    assert ev.impact == EventImpact.CRITICAL
    assert ev.volatility_expected is True
    assert ev.risk_off_support is True
    assert ev.category == EventCategory.GEOPOLITICAL
    assert ev.source == "gdacs"
    assert "Japan" in ev.countries


def test_gdacs_orange_maps_to_high():
    ev = gdacs_to_macro_event(_gdacs_record(alertlevel="Orange"))
    assert ev.impact == EventImpact.HIGH


def test_gdacs_eq_assets_include_safe_haven():
    ev = gdacs_to_macro_event(_gdacs_record(eventtype="EQ"))
    assert "GLD" in ev.assets_affected
    assert "JPY" in ev.assets_affected


def test_gdacs_event_id_is_stable():
    r = _gdacs_record(eventid=42)
    assert gdacs_to_macro_event(r).event_id == "gdacs-EQ-42-1"


def test_gdacs_timestamp_is_naive_utc():
    ev = gdacs_to_macro_event(_gdacs_record())
    assert ev.timestamp.tzinfo is None


# ---------------------------------------------------------------------------
# GDELT pack aggregation
# ---------------------------------------------------------------------------


def _art(domain: str, when: datetime) -> GdeltArticle:
    return GdeltArticle(
        title="x",
        url=f"https://{domain}/n",
        domain=domain,
        seendate=when,
    )


def test_gdelt_pack_returns_none_for_empty_batch():
    pack = DEFAULT_PACKS[0]
    assert gdelt_pack_to_macro_event(pack, []) is None


def test_gdelt_pack_two_domains_yields_medium_impact():
    pack = DEFAULT_PACKS[0]
    t = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    ev = gdelt_pack_to_macro_event(pack, [_art("a.com", t), _art("b.com", t)])
    assert ev is not None
    assert ev.impact == EventImpact.MEDIUM


def test_gdelt_pack_three_domains_yields_high_impact():
    pack = DEFAULT_PACKS[0]
    t = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    ev = gdelt_pack_to_macro_event(pack, [_art("a.com", t), _art("b.com", t), _art("c.com", t)])
    assert ev is not None
    assert ev.impact == EventImpact.HIGH


def test_gdelt_pack_five_domains_yields_critical():
    pack = DEFAULT_PACKS[0]
    t = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    ev = gdelt_pack_to_macro_event(
        pack,
        [
            _art("a.com", t),
            _art("b.com", t),
            _art("c.com", t),
            _art("d.com", t),
            _art("e.com", t),
        ],
    )
    assert ev is not None
    assert ev.impact == EventImpact.CRITICAL


def test_gdelt_event_id_is_stable_within_hourly_bucket():
    pack = DEFAULT_PACKS[0]
    t1 = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    t2 = datetime(2026, 5, 11, 12, 30, tzinfo=UTC)  # same hour
    e1 = gdelt_pack_to_macro_event(pack, [_art("a.com", t1), _art("b.com", t1)])
    e2 = gdelt_pack_to_macro_event(pack, [_art("a.com", t2), _art("b.com", t2)])
    assert e1 and e2
    assert e1.event_id == e2.event_id


def test_gdelt_event_id_changes_across_hours():
    pack = DEFAULT_PACKS[0]
    t1 = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    t2 = datetime(2026, 5, 11, 13, 0, tzinfo=UTC)
    e1 = gdelt_pack_to_macro_event(pack, [_art("a.com", t1), _art("b.com", t1)])
    e2 = gdelt_pack_to_macro_event(pack, [_art("a.com", t2), _art("b.com", t2)])
    assert e1 and e2
    assert e1.event_id != e2.event_id


def test_get_pack_lookup():
    assert get_pack("energy_shipping") is not None
    assert get_pack("does_not_exist") is None


# ---------------------------------------------------------------------------
# MacroEventFetcher dedup
# ---------------------------------------------------------------------------


def test_add_event_dedups_by_id():
    fetcher = MacroEventFetcher()
    ev = gdacs_to_macro_event(_gdacs_record(eventid=99))
    assert fetcher.add_event(ev) is True
    assert fetcher.add_event(ev) is False  # second add ignored
    assert sum(1 for e in fetcher.events if e.event_id == ev.event_id) == 1


async def test_poll_live_events_with_mock_clients_is_idempotent():
    """Same upstream payload twice → second cycle adds zero new events."""
    from app.macro import GdacsClient, GdeltClient

    class _MockGdelt(GdeltClient):
        async def fetch_all(self):
            # Use the first default pack but return no articles → no event.
            return {DEFAULT_PACKS[0].name: []}

    class _MockGdacs(GdacsClient):
        async def fetch_recent(self):
            return [_gdacs_record(eventid=1), _gdacs_record(eventid=2)]

    fetcher = MacroEventFetcher()
    gdelt = _MockGdelt(packs=DEFAULT_PACKS[:1])
    gdacs = _MockGdacs()

    first = await fetcher.poll_live_events(gdelt_client=gdelt, gdacs_client=gdacs)
    second = await fetcher.poll_live_events(gdelt_client=gdelt, gdacs_client=gdacs)
    assert first["gdacs_new"] == 2
    assert second["gdacs_new"] == 0
