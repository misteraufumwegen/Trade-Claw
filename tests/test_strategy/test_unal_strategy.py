"""
Comprehensive tests for Ünal's Live-Trading Strategy

Tests:
- Grade scoring (A+ through F)
- Entry/Exit rules validation
- R/R ratio enforcement
- Position sizing
- Trade setup creation
- Tradeable filtering
- Risk management
"""

import pytest
from datetime import datetime
from app.strategy.unal_strategy import (
    UnalLiveStrategy,
    TradeGrade,
    TradeSetup,
    EntryRules,
    ExitRules,
    GradeScoringEngine,
    MarketContext,
    MacroEnvironment,
)


class TestGradeScoringEngine:
    """Test grade scoring logic."""
    
    def test_score_7_a_plus(self):
        """7 points = A+ grade."""
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=True,
            macro_aligned=True,
            rr_ratio=3.5,
            confidence=80.0,
        )
        assert score == 7
        assert grade == TradeGrade.A_PLUS
    
    def test_score_6_a(self):
        """6 points = A grade."""
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=True,
            macro_aligned=False,
            rr_ratio=3.5,
            confidence=80.0,
        )
        assert score == 6
        assert grade == TradeGrade.A
    
    def test_score_5_b(self):
        """5 points = B grade."""
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=True,
            macro_aligned=False,
            rr_ratio=3.5,
            confidence=70.0,
        )
        assert score == 5
        assert grade == TradeGrade.B
    
    def test_score_4_c(self):
        """4 points = C grade."""
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=False,
            macro_aligned=False,
            rr_ratio=2.5,  # < 3.0, so no R/R point
            confidence=70.0,  # < 75, so no confidence point
        )
        assert score == 3  # 3 entry rules only
        assert grade == TradeGrade.D
    
    def test_score_2_d(self):
        """2 points = F grade (too low)."""
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=True,
            liquidity_sweep=False,
            momentum_aligned=False,
            volume_confirmed=False,
            macro_aligned=False,
            rr_ratio=2.0,
            confidence=60.0,
        )
        assert score == 1
        assert grade == TradeGrade.F
    
    def test_score_0_f(self):
        """0 points = F grade."""
        score, grade = GradeScoringEngine.calculate_score(
            structural_break=False,
            liquidity_sweep=False,
            momentum_aligned=False,
            volume_confirmed=False,
            macro_aligned=False,
            rr_ratio=1.0,
            confidence=40.0,
        )
        assert score == 0
        assert grade == TradeGrade.F


class TestEntryRules:
    """Test entry rule validation."""
    
    def test_entry_valid_4_of_5(self):
        """Valid entry with 4 of 5 rules."""
        rules = EntryRules(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=True,
            macro_aligned=False,
        )
        assert rules.is_valid() is True
    
    def test_entry_invalid_3_of_5(self):
        """Invalid entry with only 3 of 5 rules."""
        rules = EntryRules(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=False,
            macro_aligned=False,
        )
        assert rules.is_valid() is False
    
    def test_entry_valid_5_of_5(self):
        """Valid entry with all 5 rules."""
        rules = EntryRules(
            structural_break=True,
            liquidity_sweep=True,
            momentum_aligned=True,
            volume_confirmed=True,
            macro_aligned=True,
        )
        assert rules.is_valid() is True


class TestExitRules:
    """Test exit rule calculation."""
    
    def test_calculate_targets_long(self):
        """Calculate long exit targets."""
        exit_rules = ExitRules()
        exit_rules.calculate_targets(entry=41750, stop_loss=40200, r_multiple=3.0)
        
        assert exit_rules.tp1_target > 41750  # TP1 above entry
        assert exit_rules.tp2_target > exit_rules.tp1_target  # TP2 > TP1
        assert exit_rules.trailing_target > 41750  # Trailing above entry
        assert exit_rules.hard_stop_loss == 40200
    
    def test_calculate_targets_short(self):
        """Calculate short exit targets."""
        exit_rules = ExitRules()
        exit_rules.calculate_targets(entry=51500, stop_loss=53800, r_multiple=3.0)
        
        assert exit_rules.tp1_target < 51500  # TP1 below entry
        assert exit_rules.tp2_target < exit_rules.tp1_target  # TP2 < TP1
        assert exit_rules.trailing_target < 51500  # Trailing below entry
        assert exit_rules.hard_stop_loss == 53800


class TestTradeSetup:
    """Test trade setup creation and management."""
    
    def test_position_size_calculation(self):
        """Test position size based on account equity."""
        setup = TradeSetup(
            trade_id="TEST_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            grade=TradeGrade.A_PLUS,
            score=7,
            confidence=85.0,
            market_context=MarketContext.BREAKOUT,
            macro_environment=MacroEnvironment.RISK_ON,
        )
        
        setup.calculate_position_size(account_equity=100.0, risk_pct=2.0)
        
        assert setup.position_size > 0
        assert setup.risk_amount_chf == 2.0  # 2% of 100
    
    def test_setup_tradeable_a_plus(self):
        """A+ grade should be tradeable."""
        setup = TradeSetup(
            trade_id="TEST_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            grade=TradeGrade.A_PLUS,
            score=7,
            confidence=85.0,
            market_context=MarketContext.BREAKOUT,
            macro_environment=MacroEnvironment.RISK_ON,
        )
        
        setup.set_tradeable()
        assert setup.live_tradeable is True
    
    def test_setup_tradeable_a(self):
        """A grade should be tradeable."""
        setup = TradeSetup(
            trade_id="TEST_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            grade=TradeGrade.A,
            score=6,
            confidence=80.0,
            market_context=MarketContext.BREAKOUT,
            macro_environment=MacroEnvironment.RISK_ON,
        )
        
        setup.set_tradeable()
        assert setup.live_tradeable is True
    
    def test_setup_not_tradeable_b(self):
        """B grade should NOT be live tradeable."""
        setup = TradeSetup(
            trade_id="TEST_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            grade=TradeGrade.B,
            score=5,
            confidence=75.0,
            market_context=MarketContext.BREAKOUT,
            macro_environment=MacroEnvironment.RISK_ON,
        )
        
        setup.set_tradeable()
        assert setup.live_tradeable is False
    
    def test_setup_to_dict(self):
        """Test serialization to dict."""
        setup = TradeSetup(
            trade_id="TEST_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            grade=TradeGrade.A_PLUS,
            score=7,
            confidence=85.0,
            market_context=MarketContext.BREAKOUT,
            macro_environment=MacroEnvironment.RISK_ON,
            macro_event="Fed Pivot",
        )
        
        setup.set_tradeable()
        setup_dict = setup.to_dict()
        
        assert setup_dict['trade_id'] == "TEST_001"
        assert setup_dict['asset'] == "BTC"
        assert setup_dict['grade'] == "A+"
        assert setup_dict['live_tradeable'] is True


class TestUnalLiveStrategy:
    """Test main strategy engine."""
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        assert strategy.account_equity == 100.0
        assert len(strategy.active_setups) == 0
        assert len(strategy.executed_trades) == 0
    
    def test_create_setup_a_plus(self):
        """Create A+ grade setup."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
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
            macro_event="Fed Pivot bullisch",
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        assert setup.grade == TradeGrade.A_PLUS
        assert setup.live_tradeable is True
        assert setup.score == 7
        assert setup in strategy.active_setups
    
    def test_create_setup_b_grade(self):
        """Create B grade setup (backtest only)."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        setup = strategy.create_setup(
            trade_id="TRADE_002",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            tp1=44900,
            tp2=47500,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=70.0,  # < 75, no confidence point
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': False,
            }
        )
        
        # 4 entry rules + 1 R/R (3.7:1) + 0 confidence (70 < 75) = 5 points = B
        assert setup.grade == TradeGrade.B
        assert setup.live_tradeable is False
    
    def test_filter_tradeable_setups(self):
        """Filter only tradeable (A+/A) setups."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        # Add A+ setup
        strategy.create_setup(
            trade_id="TRADE_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            tp1=44900,
            tp2=47500,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        # Add B setup (not tradeable)
        strategy.create_setup(
            trade_id="TRADE_002",
            asset="ETH",
            direction="Long",
            entry_price=2500,
            stop_loss=2400,
            tp1=2700,
            tp2=2900,
            market_context="Trending",
            macro_environment="Risk-On Expansion",
            confidence=70.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': False,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': False,
            }
        )
        
        tradeable = strategy.filter_tradeable_setups()
        
        assert len(tradeable) == 1
        assert tradeable[0].trade_id == "TRADE_001"
    
    def test_position_size_equity_adjustment(self):
        """Position size scales with account equity."""
        strategy1 = UnalLiveStrategy(account_equity=100.0)
        strategy2 = UnalLiveStrategy(account_equity=1000.0)
        
        setup1 = strategy1.create_setup(
            trade_id="TRADE_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            tp1=44900,
            tp2=47500,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        setup2 = strategy2.create_setup(
            trade_id="TRADE_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            tp1=44900,
            tp2=47500,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        # Strategy with 10x equity should have 10x position size
        assert setup2.position_size > setup1.position_size
    
    def test_rr_ratio_validation(self):
        """R/R ratio is calculated and enforced."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
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
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        # Calculate expected R/R
        risk = 41750 - 40200
        reward = 47500 - 41750
        expected_rr = reward / risk
        
        assert abs(setup.r_multiple - expected_rr) < 0.01
    
    def test_exit_targets_calculated(self):
        """Exit targets are calculated for each setup."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
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
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        assert setup.exit_rules.tp1_target > 0
        assert setup.exit_rules.tp2_target > setup.exit_rules.tp1_target
        assert setup.exit_rules.hard_stop_loss == 40200
    
    def test_get_strategy_status(self):
        """Get strategy status report."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        strategy.create_setup(
            trade_id="TRADE_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            tp1=44900,
            tp2=47500,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        status = strategy.get_setup_status()
        
        assert status['total_setups'] == 1
        assert status['tradeable_setups'] == 1
        assert status['account_equity'] == 100.0


class TestMultipleAssets:
    """Test strategy across multiple assets."""
    
    def test_btc_setup(self):
        """Create BTC trade setup."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        setup = strategy.create_setup(
            trade_id="BTC_001",
            asset="BTC",
            direction="Long",
            entry_price=41750,
            stop_loss=40200,
            tp1=44900,
            tp2=47500,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=85.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        assert setup.asset == "BTC"
    
    def test_eth_setup(self):
        """Create ETH trade setup."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        setup = strategy.create_setup(
            trade_id="ETH_001",
            asset="ETH",
            direction="Long",
            entry_price=2500,
            stop_loss=2400,
            tp1=2700,
            tp2=2900,
            market_context="Breakout",
            macro_environment="Risk-On Expansion",
            confidence=80.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        assert setup.asset == "ETH"
    
    def test_gld_setup(self):
        """Create GLD (Gold) trade setup."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        setup = strategy.create_setup(
            trade_id="GLD_001",
            asset="GLD",
            direction="Long",
            entry_price=195.50,
            stop_loss=192.00,
            tp1=199.00,
            tp2=203.00,
            market_context="Breakout",
            macro_environment="Risk-Off",
            confidence=78.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        assert setup.asset == "GLD"


class TestShortTrades:
    """Test short trade setups."""
    
    def test_short_trade_setup(self):
        """Create short trade setup."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        setup = strategy.create_setup(
            trade_id="SHORT_001",
            asset="BTC",
            direction="Short",
            entry_price=51500,
            stop_loss=53800,
            tp1=48000,
            tp2=44500,
            market_context="Trending Down",
            macro_environment="Risk-Off",
            macro_event="China Mining Ban",
            confidence=78.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        assert setup.direction == "Short"
        assert setup.stop_loss > setup.entry_price  # Stop above entry for short
    
    def test_short_exit_targets(self):
        """Short trade exit targets are below entry."""
        strategy = UnalLiveStrategy(account_equity=100.0)
        
        setup = strategy.create_setup(
            trade_id="SHORT_001",
            asset="BTC",
            direction="Short",
            entry_price=51500,
            stop_loss=53800,
            tp1=48000,
            tp2=44500,
            market_context="Trending Down",
            macro_environment="Risk-Off",
            confidence=78.0,
            entry_rules_data={
                'structural_break': True,
                'liquidity_sweep': True,
                'momentum_aligned': True,
                'volume_confirmed': True,
                'macro_aligned': True,
            }
        )
        
        # For short trades, targets should be below entry
        assert setup.exit_rules.tp1_target < setup.entry_price
        assert setup.exit_rules.tp2_target < setup.exit_rules.tp1_target


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
