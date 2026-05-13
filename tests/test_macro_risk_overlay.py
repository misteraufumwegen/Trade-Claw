"""
Tests for the two macro-driven risk overlays exposed by EventFilter:
- find_blocking_red_events  (geo-halt)
- volatility_size_multiplier (size haircut driven by macro volatility)
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.macro import (
    EventCategory,
    EventDirection,
    EventFilter,
    EventImpact,
    MacroEvent,
)


def _ev(
    *,
    assets: tuple[str, ...] = (),
    impact: EventImpact = EventImpact.CRITICAL,
    age_minutes: int = 30,
    volatility_expected: bool = True,
    risk_off: bool = True,
) -> MacroEvent:
    return MacroEvent(
        event_id=f"e-{age_minutes}-{impact.name}-{'-'.join(assets) or 'none'}",
        category=EventCategory.GEOPOLITICAL,
        title="t",
        description="d",
        timestamp=datetime.utcnow() - timedelta(minutes=age_minutes),
        impact=impact,
        direction=EventDirection.BEARISH,
        assets_affected=list(assets),
        risk_off_support=risk_off,
        volatility_expected=volatility_expected,
    )


# ---------------------------------------------------------------------------
# find_blocking_red_events
# ---------------------------------------------------------------------------


def test_blocking_substring_match_against_symbol():
    flt = EventFilter()
    events = [_ev(assets=("USD",), age_minutes=30)]
    # USD substring of BTCUSDT → match
    blocking = flt.find_blocking_red_events(events, symbol="BTCUSDT")
    assert len(blocking) == 1


def test_blocking_reverse_substring_match():
    flt = EventFilter()
    # Symbol shorter than asset code: "EUR" ⊇ "EUR" — exact match path
    events = [_ev(assets=("EUR",), age_minutes=30)]
    assert len(flt.find_blocking_red_events(events, symbol="EUR")) == 1


def test_blocking_no_overlap_returns_empty():
    flt = EventFilter()
    events = [_ev(assets=("JPY",), age_minutes=30)]
    assert flt.find_blocking_red_events(events, symbol="BTCUSDT") == []


def test_blocking_non_critical_ignored():
    flt = EventFilter()
    events = [_ev(assets=("USD",), impact=EventImpact.HIGH, age_minutes=30)]
    assert flt.find_blocking_red_events(events, symbol="BTCUSDT") == []


def test_blocking_outside_lookback_ignored():
    flt = EventFilter()
    # 48h ago, default lookback is 24h
    events = [_ev(assets=("USD",), age_minutes=48 * 60)]
    assert flt.find_blocking_red_events(events, symbol="BTCUSDT") == []


def test_blocking_multiple_events_returned():
    flt = EventFilter()
    events = [
        _ev(assets=("USD",), age_minutes=10),
        _ev(assets=("USD",), age_minutes=120),
    ]
    assert len(flt.find_blocking_red_events(events, symbol="EURUSD")) == 2


def test_blocking_empty_symbol_returns_empty():
    flt = EventFilter()
    events = [_ev(assets=("USD",), age_minutes=30)]
    assert flt.find_blocking_red_events(events, symbol="") == []


# ---------------------------------------------------------------------------
# volatility_size_multiplier
# ---------------------------------------------------------------------------


def test_multiplier_low_volatility_is_one():
    flt = EventFilter()
    mult, reason = flt.volatility_size_multiplier([])
    assert mult == 1.0
    assert "Low" in reason


def test_multiplier_extreme_with_two_criticals():
    flt = EventFilter()
    events = [
        _ev(impact=EventImpact.CRITICAL, age_minutes=5, volatility_expected=True),
        _ev(impact=EventImpact.CRITICAL, age_minutes=15, volatility_expected=True),
    ]
    mult, reason = flt.volatility_size_multiplier(events)
    assert mult == 0.3
    assert "Extreme" in reason


def test_multiplier_high_with_one_critical():
    flt = EventFilter()
    events = [_ev(impact=EventImpact.CRITICAL, age_minutes=5, volatility_expected=True)]
    mult, _ = flt.volatility_size_multiplier(events)
    assert mult == 0.5


def test_multiplier_medium_with_two_high():
    flt = EventFilter()
    events = [
        _ev(impact=EventImpact.HIGH, age_minutes=5, volatility_expected=True),
        _ev(impact=EventImpact.HIGH, age_minutes=20, volatility_expected=True),
    ]
    mult, _ = flt.volatility_size_multiplier(events)
    assert mult == 0.8


def test_multiplier_excludes_events_outside_lookback():
    flt = EventFilter()
    # Two CRITICAL events but both older than 24h → recent window is empty → Low
    events = [
        _ev(impact=EventImpact.CRITICAL, age_minutes=48 * 60),
        _ev(impact=EventImpact.CRITICAL, age_minutes=72 * 60),
    ]
    mult, _ = flt.volatility_size_multiplier(events)
    assert mult == 1.0
