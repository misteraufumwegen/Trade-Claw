"""
Unit tests for Ünal's Setup Grading Engine
"""

import pytest
from app.ml.grader import (
    SetupCriteria,
    TradeSetup,
    GraderEngine,
    TradeGrader,
    TradeGrade,
)


class TestSetupCriteria:
    """Tests for SetupCriteria dataclass"""
    
    def test_criteria_initialization(self):
        """Test criteria can be initialized with defaults"""
        criteria = SetupCriteria()
        assert criteria.structural_level is False
        assert criteria.risk_reward is False
    
    def test_criteria_with_values(self):
        """Test criteria can be initialized with values"""
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            risk_reward=True,
            macro_alignment=True,
            no_contradiction=True
        )
        assert criteria.structural_level is True
        assert criteria.risk_reward is True


class TestGraderEngineScoring:
    """Tests for score calculation"""
    
    def test_score_all_criteria_met(self):
        """Test score = 7 when all criteria met"""
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            risk_reward=True,
            macro_alignment=True,
            no_contradiction=True
        )
        score = GraderEngine.calculate_score(criteria)
        assert score == 7
    
    def test_score_no_criteria_met(self):
        """Test score = 0 when no criteria met"""
        criteria = SetupCriteria()
        score = GraderEngine.calculate_score(criteria)
        assert score == 0
    
    def test_score_partial_criteria(self):
        """Test score with partial criteria met"""
        criteria = SetupCriteria(
            structural_level=True,
            momentum=True,
            risk_reward=True
        )
        score = GraderEngine.calculate_score(criteria)
        assert score == 3


class TestGraderEngineGrading:
    """Tests for grade assignment"""
    
    def test_grade_a_plus(self):
        """Test A+ grade for perfect setup (7/7)"""
        grade = GraderEngine.assign_grade(score=7, risk_reward_met=True)
        assert grade == TradeGrade.A_PLUS
    
    def test_grade_a(self):
        """Test A grade for 6/7 criteria"""
        grade = GraderEngine.assign_grade(score=6, risk_reward_met=True)
        assert grade == TradeGrade.A
    
    def test_grade_b(self):
        """Test B grade for 5/7 criteria"""
        grade = GraderEngine.assign_grade(score=5, risk_reward_met=True)
        assert grade == TradeGrade.B
    
    def test_grade_c_insufficient_score(self):
        """Test C grade for insufficient criteria (4 or fewer)"""
        grade = GraderEngine.assign_grade(score=4, risk_reward_met=True)
        assert grade == TradeGrade.C
    
    def test_grade_c_no_risk_reward(self):
        """Test C grade when R/R requirement not met (HARD RULE)"""
        # Even if score is high, no R/R means grade C
        grade = GraderEngine.assign_grade(score=7, risk_reward_met=False)
        assert grade == TradeGrade.C


class TestGraderEngineSetupGrading:
    """Tests for full setup grading"""
    
    def test_grade_perfect_long_setup(self):
        """Test grading a perfect long setup (A+)"""
        engine = GraderEngine()
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            risk_reward=True,
            macro_alignment=True,
            no_contradiction=True
        )
        
        setup = engine.grade_setup(
            symbol="BTC",
            direction="LONG",
            entry_price=42000,
            stop_loss_price=40000,
            tp1_price=45000,
            tp2_price=48000,
            criteria=criteria
        )
        
        assert setup.grade == TradeGrade.A_PLUS.value
        assert setup.setup_score == 7
        assert setup.symbol == "BTC"
        assert setup.direction == "LONG"
    
    def test_grade_short_setup(self):
        """Test grading a short setup"""
        engine = GraderEngine()
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            risk_reward=True,
            macro_alignment=True,
            no_contradiction=True
        )
        
        setup = engine.grade_setup(
            symbol="ETH",
            direction="SHORT",
            entry_price=2500,
            stop_loss_price=2700,
            tp1_price=2300,
            tp2_price=2100,
            criteria=criteria
        )
        
        assert setup.grade == TradeGrade.A_PLUS.value
        assert setup.direction == "SHORT"
    
    def test_grade_insufficient_rr_ratio(self):
        """Test setup with insufficient R/R ratio"""
        engine = GraderEngine()
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            macro_alignment=True,
            no_contradiction=True
        )
        
        setup = engine.grade_setup(
            symbol="BTC",
            direction="LONG",
            entry_price=42000,
            stop_loss_price=41000,  # Only 1% risk
            tp1_price=42500,  # Only 1.2% reward
            tp2_price=43000,  # Only 2.4% reward - NOT 1:3
            criteria=criteria
        )
        
        # Should be C grade due to insufficient R/R
        assert setup.grade == TradeGrade.C.value
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        engine = GraderEngine()
        pos = engine._calculate_position_size(
            entry_price=42000,
            stop_loss_price=40000,
            risk_percent=2.0,
            account_value=100000
        )
        
        # Risk amount: 100000 * 0.02 = 2000
        # Price risk: 42000 - 40000 = 2000
        # Position size: 2000 / 2000 = 1.0
        assert pos == 1.0
    
    def test_position_size_half_risk(self):
        """Test position size with 1% risk"""
        engine = GraderEngine()
        pos = engine._calculate_position_size(
            entry_price=42000,
            stop_loss_price=40000,
            risk_percent=1.0,
            account_value=100000
        )
        
        # Risk amount: 100000 * 0.01 = 1000
        # Price risk: 42000 - 40000 = 2000
        # Position size: 1000 / 2000 = 0.5
        assert pos == 0.5


class TestGraderEngineTradeability:
    """Tests for tradeable check"""
    
    def test_tradeable_a_plus_all_stages(self):
        """Test A+ is tradeable in all drawdown stages"""
        engine = GraderEngine()
        assert engine.is_tradeable(TradeGrade.A_PLUS.value, stage=1) is True
        assert engine.is_tradeable(TradeGrade.A_PLUS.value, stage=2) is True
        assert engine.is_tradeable(TradeGrade.A_PLUS.value, stage=3) is True
        assert engine.is_tradeable(TradeGrade.A_PLUS.value, stage=4) is False
    
    def test_tradeable_a_grade_limited(self):
        """Test A is tradeable only in stages 1-2"""
        engine = GraderEngine()
        assert engine.is_tradeable(TradeGrade.A.value, stage=1) is True
        assert engine.is_tradeable(TradeGrade.A.value, stage=2) is True
        assert engine.is_tradeable(TradeGrade.A.value, stage=3) is False
    
    def test_tradeable_b_grade_only_stage1(self):
        """Test B is tradeable only in stage 1"""
        engine = GraderEngine()
        assert engine.is_tradeable(TradeGrade.B.value, stage=1) is True
        assert engine.is_tradeable(TradeGrade.B.value, stage=2) is False
        assert engine.is_tradeable(TradeGrade.B.value, stage=3) is False
    
    def test_tradeable_c_grade_never(self):
        """Test C grade is never tradeable"""
        engine = GraderEngine()
        assert engine.is_tradeable(TradeGrade.C.value, stage=1) is False
        assert engine.is_tradeable(TradeGrade.C.value, stage=2) is False


class TestTradeGrader:
    """Tests for public TradeGrader API"""
    
    def test_grader_grade_setup(self):
        """Test TradeGrader.grade() method"""
        grader = TradeGrader()
        
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            risk_reward=True,
            macro_alignment=True,
            no_contradiction=True
        )
        
        setup = grader.grade(
            symbol="BTC",
            direction="LONG",
            entry_price=42000,
            stop_loss_price=40000,
            tp1_price=45000,
            tp2_price=48000,
            criteria=criteria
        )
        
        assert setup.grade == TradeGrade.A_PLUS.value
        assert setup.setup_score == 7
    
    def test_grader_is_tradeable(self):
        """Test TradeGrader.is_tradeable() method"""
        grader = TradeGrader()
        
        criteria = SetupCriteria(
            structural_level=True,
            liquidity_sweep=True,
            momentum=True,
            volume=True,
            risk_reward=True,
            macro_alignment=True,
            no_contradiction=True
        )
        
        setup = grader.grade(
            symbol="BTC",
            direction="LONG",
            entry_price=42000,
            stop_loss_price=40000,
            tp1_price=45000,
            tp2_price=48000,
            criteria=criteria
        )
        
        assert grader.is_tradeable(setup, drawdown_stage=1) is True
        assert grader.is_tradeable(setup, drawdown_stage=4) is False
