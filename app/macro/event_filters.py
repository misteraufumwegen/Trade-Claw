"""
Event Scoring & Filtering - Macro Event Analysis for Trading

Implements:
- Event scoring (impact + alignment + volatility)
- Green/Amber/Red light signals
- Asset-event correlation mapping
- Trade eligibility based on macro environment
"""

import logging
from datetime import datetime
from enum import Enum

from .event_fetcher import EventDirection, EventImpact, MacroEvent

logger = logging.getLogger(__name__)


class MacroSignal(Enum):
    """Macro event trading signal."""

    GREEN_LIGHT = "✅ Green Light"  # Event aligns, trade entry OK
    AMBER_LIGHT = "⚠️ Amber Light"  # Uncertainty, reduce size
    RED_LIGHT = "❌ Red Light"  # Event contradicts, cancel/exit


class EventScorer:
    """
    Scores macro events for trading impact and alignment.

    Scoring criteria:
    - Event impact magnitude (Critical=10, High=7, Medium=5, Low=3)
    - Direction alignment with intended trade
    - Volatility expectation (multiplier)
    - Asset-event relevance
    """

    # Impact score weights
    IMPACT_SCORES = {
        EventImpact.CRITICAL: 10,
        EventImpact.HIGH: 7,
        EventImpact.MEDIUM: 5,
        EventImpact.LOW: 3,
    }

    def __init__(self):
        """Initialize event scorer."""
        logger.info("🎯 EventScorer initialized")

    def score_event(self, event: MacroEvent) -> float:
        """
        Calculate overall event score (0-100).

        Args:
            event: MacroEvent to score

        Returns:
            Score 0-100
        """
        score = 0.0

        # Impact weight (max 40 points)
        impact_score = self.IMPACT_SCORES.get(event.impact, 0)
        score += impact_score * 4  # 10 * 4 = 40 points max

        # Volatility bonus (max 20 points)
        if event.volatility_expected:
            score += 20

        # Asset relevance (max 20 points)
        if event.assets_affected:
            score += min(20, len(event.assets_affected) * 5)

        # Direction clarity bonus (max 20 points)
        if event.direction in [EventDirection.BULLISH, EventDirection.BEARISH]:
            score += 20

        # Cap at 100
        return min(100, score)

    def score_for_direction(self, event: MacroEvent, intended_direction: str) -> float:
        """
        Score event alignment with intended trade direction.

        Args:
            event: MacroEvent
            intended_direction: "Long" or "Short"

        Returns:
            Score 0-100 (100 = perfect alignment, 0 = contradicts)
        """
        base_score = self.score_event(event)

        # Check alignment
        if intended_direction == "Long":
            if event.direction == EventDirection.BULLISH or event.risk_on_support:
                return base_score  # Fully aligned
            elif event.direction == EventDirection.BEARISH or event.risk_off_support:
                return 0  # Contradicts
            else:
                return base_score * 0.5  # Neutral

        elif intended_direction == "Short":
            if event.direction == EventDirection.BEARISH or event.risk_off_support:
                return base_score  # Fully aligned
            elif event.direction == EventDirection.BULLISH or event.risk_on_support:
                return 0  # Contradicts
            else:
                return base_score * 0.5  # Neutral

        return base_score * 0.5


class EventFilter:
    """
    Filters macro events and provides trading signal (Green/Amber/Red).

    Rules:
    - Green Light: Event aligns with setup, score > 70, proceed with entry
    - Amber Light: Event creates uncertainty, reduce position size
    - Red Light: Event contradicts setup, cancel/exit position
    """

    def __init__(self):
        """Initialize event filter."""
        self.scorer = EventScorer()
        logger.info("📋 EventFilter initialized")

    def evaluate_event(
        self,
        event: MacroEvent,
        intended_direction: str,
        entry_price: float,
        stop_loss: float,
        current_price: float | None = None,
    ) -> tuple[MacroSignal, float, str]:
        """
        Evaluate macro event for trade entry/exit signal.

        Args:
            event: MacroEvent to evaluate
            intended_direction: "Long" or "Short"
            entry_price: Intended entry price
            stop_loss: Stop loss price
            current_price: Current price (optional)

        Returns:
            (signal, score, reason)
        """
        score = self.scorer.score_for_direction(event, intended_direction)

        # Determine signal
        if score >= 70:
            signal = MacroSignal.GREEN_LIGHT
            reason = "Event aligns with setup (score > 70)"
        elif score >= 40:
            signal = MacroSignal.AMBER_LIGHT
            reason = "Event creates uncertainty (40-70), reduce size"
        else:
            signal = MacroSignal.RED_LIGHT
            reason = "Event contradicts setup (score < 40)"

        # Log
        logger.info(
            f"📊 Event Evaluation: {event.title}\n"
            f"   Direction: {intended_direction}\n"
            f"   Signal: {signal.value}\n"
            f"   Score: {score:.1f}/100\n"
            f"   Reason: {reason}"
        )

        return signal, score, reason

    def filter_events_by_asset(
        self,
        events: list[MacroEvent],
        asset: str,
    ) -> list[MacroEvent]:
        """
        Filter events relevant to specific asset.

        Args:
            events: List of events to filter
            asset: Asset symbol (BTC, ETH, GLD, etc)

        Returns:
            Filtered list of relevant events
        """
        relevant = [e for e in events if asset in e.assets_affected]
        logger.info(f"🔍 Filtered {len(relevant)}/{len(events)} events relevant to {asset}")
        return relevant

    def filter_events_by_impact(
        self,
        events: list[MacroEvent],
        min_impact: EventImpact = EventImpact.MEDIUM,
    ) -> list[MacroEvent]:
        """
        Filter events by minimum impact level.

        Args:
            events: List of events
            min_impact: Minimum impact threshold

        Returns:
            Filtered list
        """
        impact_order = [EventImpact.CRITICAL, EventImpact.HIGH, EventImpact.MEDIUM, EventImpact.LOW]
        min_index = impact_order.index(min_impact)

        relevant = [e for e in events if impact_order.index(e.impact) <= min_index]
        logger.info(
            f"🔍 Filtered {len(relevant)}/{len(events)} events with impact >= {min_impact.value}"
        )
        return relevant

    def get_macro_sentiment(self, events: list[MacroEvent]) -> tuple[str, float]:
        """
        Calculate overall macro sentiment from recent events.

        Args:
            events: List of recent macro events

        Returns:
            (sentiment, score) where sentiment is Risk-On, Risk-Off, or Neutral
        """
        if not events:
            return "Neutral", 50.0

        bullish_count = sum(
            1 for e in events if e.direction == EventDirection.BULLISH or e.risk_on_support
        )
        bearish_count = sum(
            1 for e in events if e.direction == EventDirection.BEARISH or e.risk_off_support
        )

        net_score = ((bullish_count - bearish_count) / len(events)) * 100 + 50
        net_score = max(0, min(100, net_score))  # Clamp to 0-100

        if net_score > 60:
            return "Risk-On", net_score
        elif net_score < 40:
            return "Risk-Off", net_score
        else:
            return "Neutral", net_score

    def derive_alignment_for_direction(
        self,
        events: list["MacroEvent"],
        side: str,
        lookback_hours: int = 6,
    ) -> tuple[bool | None, str]:
        """Derive a macro_alignment flag for a trade in ``side`` direction.

        Used by the TradingView webhook as a fallback when the payload does
        not set ``macro_aligned`` explicitly. Maps the recent macro sentiment
        to a per-direction alignment:

        - BUY  (long risk asset)  → aligned when sentiment is Risk-On or Neutral
        - SELL (short risk asset) → aligned when sentiment is Risk-Off or Neutral

        Returns ``(None, reason)`` when there is not enough data (recent event
        list is empty) so the caller can fall through to its own default
        instead of making things up.
        """
        from datetime import timedelta  # noqa: PLC0415

        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent = [e for e in events if e.timestamp >= cutoff]
        if not recent:
            return None, f"no macro events in last {lookback_hours}h"

        sentiment, score = self.get_macro_sentiment(recent)
        side_norm = (side or "").upper().strip()
        if side_norm in {"BUY", "LONG"}:
            aligned = sentiment in {"Risk-On", "Neutral"}
        elif side_norm in {"SELL", "SHORT"}:
            aligned = sentiment in {"Risk-Off", "Neutral"}
        else:
            return None, f"unsupported side: {side!r}"

        verdict = "aligned" if aligned else "contradicts"
        return (
            aligned,
            f"sentiment={sentiment} ({score:.0f}/100) {verdict} {side_norm} over last {lookback_hours}h "
            f"({len(recent)} events)",
        )

    def find_blocking_red_events(
        self,
        events: list[MacroEvent],
        symbol: str,
        lookback_hours: int = 24,
    ) -> list[MacroEvent]:
        """Return CRITICAL events in the recent window whose assets_affected
        overlap with ``symbol``.

        Used by the autopilot to halt new entries when a disaster-grade
        macro event (e.g. GDACS Red EQ, geopolitical escalation) is touching
        the trade's asset. Match is case-insensitive substring in either
        direction so ``USD`` ∈ ``BTCUSDT`` and ``EURUSD`` ⊇ ``EUR`` both
        qualify — false positives lean toward blocking more, which is the
        right direction for a safety gate.
        """
        from datetime import timedelta  # noqa: PLC0415

        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        symbol_upper = (symbol or "").upper().strip()
        if not symbol_upper:
            return []
        blocking: list[MacroEvent] = []
        for e in events:
            if e.timestamp < cutoff:
                continue
            if e.impact != EventImpact.CRITICAL:
                continue
            for affected in e.assets_affected:
                token = (affected or "").upper().strip()
                if not token:
                    continue
                if token in symbol_upper or symbol_upper in token:
                    blocking.append(e)
                    break
        return blocking

    def volatility_size_multiplier(
        self,
        events: list[MacroEvent],
        lookback_hours: int = 24,
    ) -> tuple[float, str]:
        """Position-size multiplier (∈ [0.3, 1.0]) driven by recent macro
        volatility. Wraps :meth:`get_volatility_outlook` and maps the
        outlook label to a size haircut.
        """
        from datetime import timedelta  # noqa: PLC0415

        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent = [e for e in events if e.timestamp >= cutoff]
        outlook, expected_move = self.get_volatility_outlook(recent)
        multiplier = {
            "Low": 1.0,
            "Medium": 0.8,
            "High": 0.5,
            "Extreme": 0.3,
        }.get(outlook, 1.0)
        return (
            multiplier,
            f"volatility={outlook} (expected move {expected_move:.1f}%) → ×{multiplier:.2f}",
        )

    def get_volatility_outlook(self, events: list[MacroEvent]) -> tuple[str, float]:
        """
        Get expected volatility based on upcoming events.

        Args:
            events: List of recent/upcoming events

        Returns:
            (volatility_level, expected_move_pct) where level is Low/Medium/High/Extreme
        """
        high_volatility_events = [e for e in events if e.volatility_expected]

        if not high_volatility_events:
            return "Low", 0.5

        critical_count = sum(1 for e in high_volatility_events if e.impact == EventImpact.CRITICAL)
        high_count = sum(1 for e in high_volatility_events if e.impact == EventImpact.HIGH)

        if critical_count >= 2:
            return "Extreme", 5.0  # 5% expected move
        elif critical_count >= 1:
            return "High", 3.0  # 3% expected move
        elif high_count >= 2:
            return "Medium", 1.5  # 1.5% expected move
        else:
            return "Low", 0.5  # 0.5% expected move

    def get_signal_recommendation(
        self,
        signal: MacroSignal,
        position_size: float,
    ) -> dict:
        """
        Get trading recommendation based on signal.

        Args:
            signal: MacroSignal (Green/Amber/Red)
            position_size: Original position size

        Returns:
            Dict with action and adjusted position size
        """
        if signal == MacroSignal.GREEN_LIGHT:
            return {
                "action": "ENTER",
                "position_size_multiplier": 1.0,
                "recommendation": "Proceed with full-size entry",
                "risk_level": "Normal",
            }
        elif signal == MacroSignal.AMBER_LIGHT:
            return {
                "action": "ENTER_REDUCED",
                "position_size_multiplier": 0.5,
                "recommendation": "Enter at 50% position size, monitor for clarity",
                "risk_level": "Reduced",
            }
        else:  # RED_LIGHT
            return {
                "action": "CANCEL",
                "position_size_multiplier": 0.0,
                "recommendation": "Cancel entry or exit existing position",
                "risk_level": "None",
            }


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    from .event_fetcher import MacroEventFetcher

    # Test with real events
    fetcher = MacroEventFetcher()
    filter = EventFilter()

    print("\n" + "=" * 70)
    print("EVENT FILTER DEMO")
    print("=" * 70)

    # Get recent events
    recent_events = fetcher.get_live_feed()

    if recent_events:
        # Evaluate first event for BTC Long
        event = recent_events[0]
        signal, score, reason = filter.evaluate_event(
            event,
            intended_direction="Long",
            entry_price=45000,
            stop_loss=43000,
        )

        print(f"\nEvent: {event.title}")
        print(f"Signal: {signal.value}")
        print(f"Score: {score:.1f}/100")
        print(f"Reason: {reason}")

        rec = filter.get_signal_recommendation(signal, 1.0)
        print(f"\nRecommendation: {rec['recommendation']}")
        print(f"Position Size Multiplier: {rec['position_size_multiplier']:.1%}")

    # Get macro sentiment
    sentiment, score = filter.get_macro_sentiment(recent_events)
    print("\n" + "=" * 70)
    print(f"Macro Sentiment: {sentiment} (Score: {score:.1f}/100)")

    # Get volatility outlook
    vol_level, expected_move = filter.get_volatility_outlook(recent_events)
    print(f"Volatility Outlook: {vol_level} ({expected_move:.1f}% expected move)")
