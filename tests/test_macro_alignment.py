"""
Tests for EventFilter.derive_alignment_for_direction — the macro-engine →
autopilot fallback that the TradingView webhook uses when the payload does
not set ``macro_aligned`` explicitly.
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
    direction: EventDirection = EventDirection.NEUTRAL,
    risk_on: bool = False,
    risk_off: bool = False,
    impact: EventImpact = EventImpact.MEDIUM,
    age_minutes: int = 30,
) -> MacroEvent:
    return MacroEvent(
        event_id=f"e-{age_minutes}-{direction.name}-{risk_on}{risk_off}",
        category=EventCategory.GEOPOLITICAL,
        title="t",
        description="d",
        timestamp=datetime.utcnow() - timedelta(minutes=age_minutes),
        impact=impact,
        direction=direction,
        risk_on_support=risk_on,
        risk_off_support=risk_off,
    )


def test_no_recent_events_returns_none():
    flt = EventFilter()
    # All events older than the lookback window
    events = [_ev(age_minutes=60 * 24)]  # 24h old
    aligned, reason = flt.derive_alignment_for_direction(events, side="BUY", lookback_hours=6)
    assert aligned is None
    assert "no macro events" in reason


def test_buy_with_risk_on_sentiment_aligned():
    flt = EventFilter()
    events = [
        _ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=10),
        _ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=30),
    ]
    aligned, reason = flt.derive_alignment_for_direction(events, side="BUY")
    assert aligned is True
    assert "Risk-On" in reason
    assert "aligned" in reason


def test_buy_with_risk_off_sentiment_contradicts():
    flt = EventFilter()
    events = [
        _ev(direction=EventDirection.BEARISH, risk_off=True, age_minutes=10),
        _ev(direction=EventDirection.BEARISH, risk_off=True, age_minutes=30),
    ]
    aligned, reason = flt.derive_alignment_for_direction(events, side="BUY")
    assert aligned is False
    assert "contradicts" in reason


def test_sell_with_risk_off_sentiment_aligned():
    flt = EventFilter()
    events = [
        _ev(direction=EventDirection.BEARISH, risk_off=True, age_minutes=15),
        _ev(direction=EventDirection.BEARISH, risk_off=True, age_minutes=45),
    ]
    aligned, reason = flt.derive_alignment_for_direction(events, side="SELL")
    assert aligned is True
    assert "Risk-Off" in reason


def test_sell_with_risk_on_sentiment_contradicts():
    flt = EventFilter()
    events = [
        _ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=15),
        _ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=45),
    ]
    aligned, _ = flt.derive_alignment_for_direction(events, side="SELL")
    assert aligned is False


def test_neutral_sentiment_aligns_both_directions():
    """When recent macro signals are mixed (Neutral sentiment), neither
    direction should be contradicted — only a clear opposite tilt should
    block a trade."""
    flt = EventFilter()
    events = [
        _ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=10),
        _ev(direction=EventDirection.BEARISH, risk_off=True, age_minutes=20),
    ]
    buy_aligned, _ = flt.derive_alignment_for_direction(events, side="BUY")
    sell_aligned, _ = flt.derive_alignment_for_direction(events, side="SELL")
    assert buy_aligned is True
    assert sell_aligned is True


def test_long_short_aliases_recognised():
    flt = EventFilter()
    events = [_ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=10)]
    long_aligned, _ = flt.derive_alignment_for_direction(events, side="LONG")
    short_aligned, _ = flt.derive_alignment_for_direction(events, side="SHORT")
    assert long_aligned is True
    assert short_aligned is False


def test_unknown_side_returns_none():
    flt = EventFilter()
    events = [_ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=10)]
    aligned, reason = flt.derive_alignment_for_direction(events, side="HOLD")
    assert aligned is None
    assert "unsupported side" in reason


def test_lookback_window_excludes_old_events():
    flt = EventFilter()
    events = [
        # 5h ago — inside the 6h window
        _ev(direction=EventDirection.BEARISH, risk_off=True, age_minutes=5 * 60),
        # 8h ago — outside
        _ev(direction=EventDirection.BULLISH, risk_on=True, age_minutes=8 * 60),
    ]
    aligned, reason = flt.derive_alignment_for_direction(events, side="BUY", lookback_hours=6)
    # Only the bearish (risk-off) event counts → BUY contradicts.
    assert aligned is False
    assert "1 events" in reason


def test_approved_dry_run_counts_for_dry_run_minimum():
    """Regression guard: the webhook emits 'approved_dry_run' and that
    decision label must contribute to the dry-run-minimum count, otherwise
    users can never transition to live."""
    from app.risk.safety_gates import count_dry_run_would_submits

    history = [
        {"mode": "dry_run", "decision": "approved_dry_run"},
        {"mode": "dry_run", "decision": "approved_dry_run"},
        {"mode": "dry_run", "decision": "rejected"},
    ]
    assert count_dry_run_would_submits(history) == 2
