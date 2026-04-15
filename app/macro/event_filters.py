"""
Event Scoring & Filtering - Macro Event Analysis for Trading

Implements:
- Event scoring (impact + alignment + volatility)
- Green/Amber/Red light signals
- Asset-event correlation mapping
- Trade eligibility based on macro environment
"""

import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime

from .event_fetcher import MacroEvent, EventImpact, EventDirection, EventCategory

logger = logging.getLogger(__name__)


class MacroSignal(Enum):
    """Macro event trading signal."""
    GREEN_LIGHT = "✅ Green Light"      # Event aligns, trade entry OK
    AMBER_LIGHT = "⚠️ Amber Light"      # Uncertainty, reduce size
    RED_LIGHT = "❌ Red Light"          # Event contradicts, cancel/exit


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
        current_price: Optional[float] = None,
    ) -> Tuple[MacroSignal, float, str]:
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
        events: List[MacroEvent],
        asset: str,
    ) -> List[MacroEvent]:
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
        events: List[MacroEvent],
        min_impact: EventImpact = EventImpact.MEDIUM,
    ) -> List[MacroEvent]:
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
        logger.info(f"🔍 Filtered {len(relevant)}/{len(events)} events with impact >= {min_impact.value}")
        return relevant
    
    def get_macro_sentiment(self, events: List[MacroEvent]) -> Tuple[str, float]:
        """
        Calculate overall macro sentiment from recent events.
        
        Args:
            events: List of recent macro events
        
        Returns:
            (sentiment, score) where sentiment is Risk-On, Risk-Off, or Neutral
        """
        if not events:
            return "Neutral", 50.0
        
        bullish_count = sum(1 for e in events if e.direction == EventDirection.BULLISH or e.risk_on_support)
        bearish_count = sum(1 for e in events if e.direction == EventDirection.BEARISH or e.risk_off_support)
        
        net_score = ((bullish_count - bearish_count) / len(events)) * 100 + 50
        net_score = max(0, min(100, net_score))  # Clamp to 0-100
        
        if net_score > 60:
            return "Risk-On", net_score
        elif net_score < 40:
            return "Risk-Off", net_score
        else:
            return "Neutral", net_score
    
    def get_volatility_outlook(self, events: List[MacroEvent]) -> Tuple[str, float]:
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
    ) -> Dict:
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
                'action': 'ENTER',
                'position_size_multiplier': 1.0,
                'recommendation': 'Proceed with full-size entry',
                'risk_level': 'Normal'
            }
        elif signal == MacroSignal.AMBER_LIGHT:
            return {
                'action': 'ENTER_REDUCED',
                'position_size_multiplier': 0.5,
                'recommendation': 'Enter at 50% position size, monitor for clarity',
                'risk_level': 'Reduced'
            }
        else:  # RED_LIGHT
            return {
                'action': 'CANCEL',
                'position_size_multiplier': 0.0,
                'recommendation': 'Cancel entry or exit existing position',
                'risk_level': 'None'
            }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from .event_fetcher import MacroEventFetcher
    
    # Test with real events
    fetcher = MacroEventFetcher()
    filter = EventFilter()
    
    print("\n" + "="*70)
    print("EVENT FILTER DEMO")
    print("="*70)
    
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
    print(f"\n" + "="*70)
    print(f"Macro Sentiment: {sentiment} (Score: {score:.1f}/100)")
    
    # Get volatility outlook
    vol_level, expected_move = filter.get_volatility_outlook(recent_events)
    print(f"Volatility Outlook: {vol_level} ({expected_move:.1f}% expected move)")
