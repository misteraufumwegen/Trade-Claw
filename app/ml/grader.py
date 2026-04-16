"""
Ünal's Setup-Scoring Engine for Trade Grading
Surgical Precision Trading System v2.0
Grades trades A+, A, B, C, F based on 7-criteria framework
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TradeGrade(str, Enum):
    """Trade quality grades"""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    F = "F"


@dataclass
class SetupCriteria:
    """7 Criteria for evaluating trade setups (from memory layer 5)"""
    structural_level: bool = False          # 1. Structural support/resistance
    liquidity_sweep: bool = False           # 2. Liquidity sweep confirmation
    momentum: bool = False                  # 3. Momentum confirmation
    volume: bool = False                    # 4. Volume confirmation
    risk_reward: bool = False               # 5. R/R >= 1:3 (MANDATORY)
    macro_alignment: bool = False           # 6. Macro environment aligned
    no_contradiction: bool = False          # 7. No on-chain/technical contradiction


@dataclass
class TradeSetup:
    """A trade setup with grading information"""
    symbol: str
    direction: str                          # "LONG" or "SHORT"
    entry_price: float
    stop_loss_price: float
    tp1_price: float                        # First target (2R typically)
    tp2_price: float                        # Second target (3R typically)
    
    criteria: SetupCriteria
    
    # Grade information
    setup_score: int                        # 0-7 (count of met criteria)
    grade: str                              # A+, A, B, C, F
    confidence: float = 50.0                # Confidence percentage
    
    # Risk management
    risk_percent: float = 2.0               # % of account risked
    position_size: float = 0.0              # Units/shares
    
    # Market context
    macro_regime: Optional[str] = None      # Risk-On, Risk-Off, etc.
    market_regime: Optional[str] = None     # Trending, Ranging, etc.
    timeframe_alignment: Optional[str] = None  # Weekly-Daily-4H aligned?
    
    # Metadata
    entry_id: Optional[str] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert setup to dictionary"""
        data = asdict(self)
        data['criteria'] = asdict(self.criteria)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data


class GraderEngine:
    """
    Ünal's Setup Grading Engine
    Evaluates setups against 7-criteria framework and assigns grades
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def calculate_score(criteria: SetupCriteria) -> int:
        """
        Calculate setup score based on met criteria.
        
        Args:
            criteria: SetupCriteria object with boolean flags
            
        Returns:
            Score 0-7 (count of True criteria)
        """
        score = 0
        if criteria.structural_level:
            score += 1
        if criteria.liquidity_sweep:
            score += 1
        if criteria.momentum:
            score += 1
        if criteria.volume:
            score += 1
        if criteria.risk_reward:
            score += 1
        if criteria.macro_alignment:
            score += 1
        if criteria.no_contradiction:
            score += 1
        return score
    
    @staticmethod
    def assign_grade(
        score: int,
        risk_reward_met: bool
    ) -> TradeGrade:
        """
        Assign grade based on score and risk/reward validation.
        
        HARD RULE: Risk/Reward (Criterion 5) is MANDATORY.
        No trade without 1:3 R/R is acceptable.
        
        Args:
            score: Number of met criteria (0-7)
            risk_reward_met: Whether 1:3 R/R requirement is met
            
        Returns:
            TradeGrade (A+, A, B, C, or F)
        """
        # Hard rule: R/R is mandatory
        if not risk_reward_met:
            return TradeGrade.C
        
        if score == 7:
            return TradeGrade.A_PLUS
        elif score == 6:
            return TradeGrade.A
        elif score == 5:
            return TradeGrade.B
        elif score <= 4:
            return TradeGrade.C
        
        return TradeGrade.F
    
    def grade_setup(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss_price: float,
        tp1_price: float,
        tp2_price: float,
        criteria: SetupCriteria,
        confidence: float = 50.0,
        risk_percent: float = 2.0,
        macro_regime: Optional[str] = None,
        market_regime: Optional[str] = None,
        notes: Optional[str] = None
    ) -> TradeSetup:
        """
        Grade a trade setup based on criteria.
        
        Args:
            symbol: Trading symbol (BTC, ETH, GLD, SPY, etc.)
            direction: "LONG" or "SHORT"
            entry_price: Entry price
            stop_loss_price: Stop-loss price
            tp1_price: First target price (2R)
            tp2_price: Second target price (3R)
            criteria: SetupCriteria with met criteria
            confidence: Trader confidence (0-100%)
            risk_percent: % of account to risk
            macro_regime: Macro environment description
            market_regime: Market regime description
            notes: Additional notes
            
        Returns:
            TradeSetup object with grade assigned
        """
        # Calculate score
        score = self.calculate_score(criteria)
        
        # Validate R/R ratio
        if direction == "LONG":
            risk = entry_price - stop_loss_price
            reward1 = tp1_price - entry_price
            reward2 = tp2_price - entry_price
        else:  # SHORT
            risk = stop_loss_price - entry_price
            reward1 = entry_price - tp1_price
            reward2 = entry_price - tp2_price
        
        # Check if 1:3 R/R is met
        risk_reward_met = False
        if risk > 0:
            min_reward = risk * 3
            if reward2 >= min_reward:
                risk_reward_met = True
                criteria.risk_reward = True  # Update criteria
        
        # Update score if R/R was just validated
        if risk_reward_met:
            score = self.calculate_score(criteria)
        
        # Assign grade
        grade = self.assign_grade(score, risk_reward_met)
        
        # Calculate position size
        position_size = self._calculate_position_size(
            entry_price,
            stop_loss_price,
            risk_percent
        )
        
        setup = TradeSetup(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            criteria=criteria,
            setup_score=score,
            grade=grade.value,
            confidence=confidence,
            risk_percent=risk_percent,
            position_size=position_size,
            macro_regime=macro_regime,
            market_regime=market_regime,
            created_at=datetime.utcnow(),
            notes=notes
        )
        
        return setup
    
    @staticmethod
    def _calculate_position_size(
        entry_price: float,
        stop_loss_price: float,
        risk_percent: float,
        account_value: float = 100000.0
    ) -> float:
        """
        Calculate position size based on risk.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop-loss price
            risk_percent: % of account to risk (default 2%)
            account_value: Total account value (default $100k)
            
        Returns:
            Position size in units/shares
        """
        if entry_price == 0:
            return 0.0
        
        risk_amount = account_value * (risk_percent / 100)
        price_risk = abs(entry_price - stop_loss_price)
        
        if price_risk == 0:
            return 0.0
        
        position_size = risk_amount / price_risk
        return position_size
    
    def is_tradeable(
        self,
        grade: str,
        drawdown_stage: int = 1,
        stage: Optional[int] = None,
    ) -> bool:
        """
        Check if setup is tradeable based on grade and drawdown stage.

        ``stage`` is an alias for ``drawdown_stage`` for convenience.

        Trading Matrix (from memory layer 7):
        - Stage 1 (Normal): A+, A, B allowed
        - Stage 2 (Caution): A+, A allowed
        - Stage 3 (Defense): A+ only
        - Stage 4+ (Emergency): No trades

        Args:
            grade: Trade grade (A+, A, B, C, F)
            drawdown_stage: Current drawdown stage (1-4+)
            stage: Alias for drawdown_stage (takes precedence if provided)

        Returns:
            True if trade should be executed, False otherwise
        """
        if stage is not None:
            drawdown_stage = stage
        if drawdown_stage == 1:  # Normal
            return grade in [TradeGrade.A_PLUS.value, TradeGrade.A.value, TradeGrade.B.value]
        elif drawdown_stage == 2:  # Caution
            return grade in [TradeGrade.A_PLUS.value, TradeGrade.A.value]
        elif drawdown_stage == 3:  # Defense
            return grade == TradeGrade.A_PLUS.value
        else:  # Stage 4+
            return False


class TradeGrader:
    """Public API for grading trades"""
    
    def __init__(self):
        self.engine = GraderEngine()
    
    def grade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss_price: float,
        tp1_price: float,
        tp2_price: float,
        **kwargs
    ) -> TradeSetup:
        """
        Grade a trade setup. See GraderEngine.grade_setup for full parameters.
        
        Example:
            grader = TradeGrader()
            setup = grader.grade(
                symbol="BTC",
                direction="LONG",
                entry_price=42000,
                stop_loss_price=40000,
                tp1_price=45000,
                tp2_price=48000,
                criteria=SetupCriteria(
                    structural_level=True,
                    liquidity_sweep=True,
                    momentum=True,
                    volume=True,
                    risk_reward=True,
                    macro_alignment=True,
                    no_contradiction=True
                )
            )
            print(f"Grade: {setup.grade}")  # A+
        """
        return self.engine.grade_setup(symbol, direction, entry_price, stop_loss_price, tp1_price, tp2_price, **kwargs)
    
    def is_tradeable(self, setup: TradeSetup, drawdown_stage: int = 1) -> bool:
        """Check if a setup should be traded given current conditions"""
        return self.engine.is_tradeable(setup.grade, drawdown_stage)
