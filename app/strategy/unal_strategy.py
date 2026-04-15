"""
Ünal's Complete Live-Trading Strategy

Implements:
1. Grade-Scoring Logic (A+ through F)
2. Entry/Exit Rules (Structural Levels, Liquidity Sweeps, Momentum, Volume)
3. R/R Ratio Enforcement (minimum 1:3)
4. Risk-Adjusted Position Sizing
5. Trade Selection Filter (only A+ & A grades for live trading)

Author: Ünal
Date: April 2026
"""

import logging
from enum import Enum
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class TradeGrade(Enum):
    """Trade quality grades based on setup score."""
    A_PLUS = "A+"  # Score 7: Excellent
    A = "A"        # Score 6: Very Good
    B = "B"        # Score 5: Good
    C = "C"        # Score 4: Fair
    D = "D"        # Score 3: Poor
    F = "F"        # Score 2-0: Fail


class MarketContext(Enum):
    """Market structure context."""
    BREAKOUT = "Breakout"        # Price breaking structural resistance
    TRENDING_UP = "Trending Up"   # Strong uptrend
    TRENDING_DOWN = "Trending Down"  # Strong downtrend
    RANGING = "Ranging"           # Consolidation
    REVERSING = "Reversing"       # Potential reversal zone


class MacroEnvironment(Enum):
    """Macro environment classification."""
    RISK_ON = "Risk-On Expansion"
    RISK_OFF = "Risk-Off"
    TRANSITION = "Risk-Off → Risk-On"
    NEUTRAL = "Neutral"


@dataclass
class EntryRules:
    """Entry trigger rules."""
    structural_break: bool = False      # Price breaks above/below structural level
    liquidity_sweep: bool = False       # Liquidity sweep confirmation
    momentum_aligned: bool = False      # RSI/Momentum aligned with direction
    volume_confirmed: bool = False      # Volume > 20-day average
    macro_aligned: bool = False         # Macro environment supports trade direction
    
    def is_valid(self) -> bool:
        """Trade is valid if at least 4 of 5 rules triggered."""
        rules = [
            self.structural_break,
            self.liquidity_sweep,
            self.momentum_aligned,
            self.volume_confirmed,
            self.macro_aligned,
        ]
        return sum(rules) >= 4


@dataclass
class ExitRules:
    """Exit rules."""
    tp1_target: float = 0.0        # First target (33% position)
    tp2_target: float = 0.0        # Second target (33% position)
    trailing_target: float = 0.0   # Trailing stop target (34% position)
    hard_stop_loss: float = 0.0    # Hard stop loss level (immutable)
    
    def calculate_targets(self, entry: float, stop_loss: float, r_multiple: float = 3.0):
        """
        Calculate TP levels based on R/R ratio.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            r_multiple: Risk multiplier (e.g., 3.0 for 1:3)
        """
        risk = abs(entry - stop_loss)
        
        if entry > stop_loss:  # Long
            self.tp1_target = entry + (risk * r_multiple * 0.66)  # 2R
            self.tp2_target = entry + (risk * r_multiple)         # 3R
            self.trailing_target = entry + (risk * 1.5)           # 1.5R
        else:  # Short
            self.tp1_target = entry - (risk * r_multiple * 0.66)  # 2R
            self.tp2_target = entry - (risk * r_multiple)         # 3R
            self.trailing_target = entry - (risk * 1.5)           # 1.5R
        
        self.hard_stop_loss = stop_loss


@dataclass
class TradeSetup:
    """Complete trade setup with all parameters."""
    trade_id: str
    asset: str
    direction: str                  # "Long" or "Short"
    entry_price: float
    stop_loss: float
    grade: TradeGrade
    score: int                      # 0-7
    confidence: float               # 0-100%
    
    # Context
    market_context: MarketContext
    macro_environment: MacroEnvironment
    macro_event: Optional[str] = None
    
    # Rules
    entry_rules: EntryRules = field(default_factory=EntryRules)
    exit_rules: ExitRules = field(default_factory=ExitRules)
    
    # Risk Management
    position_size: float = 0.0      # In units/contracts
    risk_amount_chf: float = 0.0    # Risk amount in CHF
    r_multiple: float = 1.0         # Risk/Reward multiple
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    live_tradeable: bool = False    # Only A+ & A are live tradeable
    
    def calculate_position_size(self, account_equity: float, risk_pct: float = 2.0):
        """
        Calculate position size based on account equity and risk percentage.
        
        Args:
            account_equity: Current account equity in CHF
            risk_pct: Risk percentage per trade (default 2%)
        """
        self.risk_amount_chf = account_equity * (risk_pct / 100.0)
        risk_distance = abs(self.entry_price - self.stop_loss)
        
        if risk_distance > 0:
            self.position_size = self.risk_amount_chf / risk_distance
        else:
            self.position_size = 0.0
        
        return self.position_size
    
    def set_tradeable(self):
        """Mark setup as live tradeable (A+ or A grade)."""
        self.live_tradeable = self.grade in [TradeGrade.A_PLUS, TradeGrade.A]
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'trade_id': self.trade_id,
            'asset': self.asset,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'grade': self.grade.value,
            'score': self.score,
            'confidence': self.confidence,
            'market_context': self.market_context.value,
            'macro_environment': self.macro_environment.value,
            'macro_event': self.macro_event,
            'entry_rules': {
                'structural_break': self.entry_rules.structural_break,
                'liquidity_sweep': self.entry_rules.liquidity_sweep,
                'momentum_aligned': self.entry_rules.momentum_aligned,
                'volume_confirmed': self.entry_rules.volume_confirmed,
                'macro_aligned': self.entry_rules.macro_aligned,
            },
            'exit_rules': {
                'tp1_target': self.exit_rules.tp1_target,
                'tp2_target': self.exit_rules.tp2_target,
                'trailing_target': self.exit_rules.trailing_target,
                'hard_stop_loss': self.exit_rules.hard_stop_loss,
            },
            'position_size': self.position_size,
            'risk_amount_chf': self.risk_amount_chf,
            'r_multiple': self.r_multiple,
            'live_tradeable': self.live_tradeable,
            'created_at': self.created_at.isoformat(),
        }


class GradeScoringEngine:
    """
    Grades trades on a scale of 0-7 (A+ down to F).
    
    Criteria (each worth 1 point):
    1. Structural Level (Price at key S/R)
    2. Liquidity Sweep (Sweep confirmation)
    3. Momentum (RSI/Stochastic aligned)
    4. Volume (Volume > 20-day SMA)
    5. Macro Aligned (Event/Environment support)
    6. Risk/Reward >= 1:3
    7. Confidence >= 75%
    
    Scoring:
    - 7 points: A+ (Excellent)
    - 6 points: A (Very Good)
    - 5 points: B (Good)
    - 4 points: C (Fair)
    - 3 points: D (Poor)
    - 0-2 points: F (Fail)
    """
    
    @staticmethod
    def calculate_score(
        structural_break: bool,
        liquidity_sweep: bool,
        momentum_aligned: bool,
        volume_confirmed: bool,
        macro_aligned: bool,
        rr_ratio: float,
        confidence: float,
    ) -> Tuple[int, TradeGrade]:
        """
        Calculate trade grade score.
        
        Returns: (score, grade)
        """
        score = 0
        
        # Award points for each criteria (max 7)
        if structural_break:
            score += 1
        if liquidity_sweep:
            score += 1
        if momentum_aligned:
            score += 1
        if volume_confirmed:
            score += 1
        if macro_aligned:
            score += 1
        if rr_ratio >= 3.0:  # 1:3 or better
            score += 1
        if confidence >= 75.0:
            score += 1
        
        # Map score to grade
        if score == 7:
            grade = TradeGrade.A_PLUS
        elif score == 6:
            grade = TradeGrade.A
        elif score == 5:
            grade = TradeGrade.B
        elif score == 4:
            grade = TradeGrade.C
        elif score == 3:
            grade = TradeGrade.D
        else:
            grade = TradeGrade.F
        
        logger.debug(f"Score calculated: {score} → {grade.value}")
        return score, grade


class UnalLiveStrategy:
    """
    Ünal's Complete Live-Trading Strategy.
    
    Implements:
    - Grade-scoring (A+ through F)
    - Entry/Exit rules
    - R/R enforcement
    - Risk-adjusted position sizing
    - Live trade filtering (A+ & A only)
    """
    
    def __init__(self, account_equity: float = 100.0):
        """
        Initialize strategy.
        
        Args:
            account_equity: Starting account equity in CHF (default 100 for paper trading)
        """
        self.account_equity = account_equity
        self.active_setups: List[TradeSetup] = []
        self.executed_trades: List[TradeSetup] = []
        self.risk_pct_per_trade = 2.0  # 2% risk per trade
        
        logger.info(f"🎯 UnalLiveStrategy initialized (Account: CHF {account_equity})")
    
    def create_setup(
        self,
        trade_id: str,
        asset: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        market_context: str,
        macro_environment: str,
        macro_event: Optional[str] = None,
        confidence: float = 75.0,
        entry_rules_data: Optional[Dict] = None,
        **kwargs
    ) -> TradeSetup:
        """
        Create a new trade setup with full rule evaluation.
        
        Args:
            trade_id: Unique trade identifier
            asset: Asset symbol (BTC, ETH, GLD, etc)
            direction: "Long" or "Short"
            entry_price: Entry price level
            stop_loss: Stop loss price level
            tp1: First target price
            tp2: Second target price
            market_context: Market structure (Breakout, Trending, Ranging, etc)
            macro_environment: Macro context (Risk-On, Risk-Off, etc)
            macro_event: Description of triggering macro event
            confidence: Confidence level (0-100)
            entry_rules_data: Dict with entry rule statuses
        
        Returns:
            TradeSetup object
        """
        
        # Validate inputs
        if direction not in ["Long", "Short"]:
            raise ValueError(f"Invalid direction: {direction}")
        
        # Convert market context to enum
        try:
            market = MarketContext(market_context)
        except ValueError:
            market = MarketContext.RANGING
        
        # Convert macro environment to enum
        try:
            macro = MacroEnvironment(macro_environment)
        except ValueError:
            macro = MacroEnvironment.NEUTRAL
        
        # Calculate R/R ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(tp2 - entry_price) if tp2 != entry_price else 0
        rr_ratio = (reward / risk) if risk > 0 else 0.0
        
        # Validate R/R >= 1:3
        if rr_ratio < 3.0:
            logger.warning(f"⚠️  Trade {trade_id} has R/R {rr_ratio:.2f}:1 < 3:1 minimum")
        
        # Setup entry rules
        entry_rules = EntryRules()
        if entry_rules_data:
            entry_rules.structural_break = entry_rules_data.get('structural_break', False)
            entry_rules.liquidity_sweep = entry_rules_data.get('liquidity_sweep', False)
            entry_rules.momentum_aligned = entry_rules_data.get('momentum_aligned', False)
            entry_rules.volume_confirmed = entry_rules_data.get('volume_confirmed', False)
            entry_rules.macro_aligned = entry_rules_data.get('macro_aligned', False)
        
        # Calculate grade
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=entry_rules.structural_break,
            liquidity_sweep=entry_rules.liquidity_sweep,
            momentum_aligned=entry_rules.momentum_aligned,
            volume_confirmed=entry_rules.volume_confirmed,
            macro_aligned=entry_rules.macro_aligned,
            rr_ratio=rr_ratio,
            confidence=confidence,
        )
        
        # Create setup
        setup = TradeSetup(
            trade_id=trade_id,
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            grade=grade,
            score=score,
            confidence=confidence,
            market_context=market,
            macro_environment=macro,
            macro_event=macro_event,
            entry_rules=entry_rules,
        )
        
        # Setup exit rules
        setup.exit_rules.calculate_targets(entry_price, stop_loss, r_multiple=rr_ratio)
        setup.r_multiple = rr_ratio
        
        # Calculate position size based on account equity
        setup.calculate_position_size(self.account_equity, self.risk_pct_per_trade)
        
        # Determine if tradeable (A+ or A grade)
        setup.set_tradeable()
        
        # Log
        tradeable_status = "✅ LIVE TRADEABLE" if setup.live_tradeable else "⏸️  BACKTEST ONLY"
        logger.info(
            f"📊 Setup created: {trade_id} | {asset} {direction} | "
            f"Grade: {grade.value} ({score}/7) | R/R: {rr_ratio:.1f}:1 | {tradeable_status}"
        )
        
        self.active_setups.append(setup)
        return setup
    
    def filter_tradeable_setups(self) -> List[TradeSetup]:
        """
        Filter and return only tradeable setups (A+ & A grades).
        
        Returns:
            List of tradeable TradeSetup objects
        """
        tradeable = [s for s in self.active_setups if s.live_tradeable]
        logger.info(f"🎯 {len(tradeable)} tradeable setups (A+/A) from {len(self.active_setups)} total")
        return tradeable
    
    def get_setup_status(self) -> Dict:
        """Get current strategy status."""
        tradeable = self.filter_tradeable_setups()
        
        return {
            'total_setups': len(self.active_setups),
            'tradeable_setups': len(tradeable),
            'executed_trades': len(self.executed_trades),
            'account_equity': self.account_equity,
            'risk_pct_per_trade': self.risk_pct_per_trade,
            'tradeable_list': [s.to_dict() for s in tradeable],
        }


# Example usage demonstrating the strategy
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    strategy = UnalLiveStrategy(account_equity=100.0)
    
    # Example setup
    setup = strategy.create_setup(
        trade_id="TRADE_001",
        asset="BTC",
        direction="Long",
        entry_price=41750,
        stop_loss=40200,
        tp1=44900,
        tp2=47500,
        market_context="Breakout",
        macro_environment="Risk-On Expansion",
        macro_event="Fed Pivot bullisch, Zinssenkungs-Erwartung",
        confidence=85.0,
        entry_rules_data={
            'structural_break': True,
            'liquidity_sweep': True,
            'momentum_aligned': True,
            'volume_confirmed': True,
            'macro_aligned': True,
        }
    )
    
    print("\n" + "="*70)
    print(f"Setup: {setup.to_dict()}")
    print("="*70)
