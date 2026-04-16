"""Test Risk Engine validation."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, RiskLimit
from app.risk import DBRiskEngine as RiskEngine
from app.risk import RiskLevel


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def risk_engine(db_session):
    """Create risk engine with test database."""
    return RiskEngine(db_session)


@pytest.fixture
def test_risk_limit(db_session):
    """Create test risk limit."""
    risk_limit = RiskLimit(
        session_id="test_session",
        max_position_size_pct=0.10,  # 10%
        max_drawdown_pct=-0.15,  # -15%
        max_daily_loss_pct=-0.20,  # -20%
        min_risk_reward_ratio=1.5,  # 1.5:1
        halt_on_breach=True,
    )
    db_session.add(risk_limit)
    db_session.commit()
    return risk_limit


class TestPositionSizeValidation:
    """Test position size validation."""

    def test_position_size_within_limit(self, risk_engine, test_risk_limit):
        """Test position size within acceptable limit."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.25"),  # 0.25 BTC @ 40000 = $10,000 (10% of account)
            entry_price=Decimal("40000"),
            stop_loss=Decimal("38000"),
            take_profit=Decimal("44000"),
        )

        assert result.approved is True
        assert result.level == RiskLevel.OK

    def test_position_size_exceeds_limit(self, risk_engine, test_risk_limit):
        """Test position size exceeding account limit."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("1.0"),  # 1 BTC @ 50000 = $50,000 (50% of account - exceeds 10%)
            entry_price=Decimal("50000"),
            stop_loss=Decimal("48000"),
            take_profit=Decimal("54000"),
        )

        assert result.approved is False
        assert result.reason == "POSITION_SIZE_EXCEEDED"


class TestRiskRewardValidation:
    """Test risk/reward ratio validation."""

    def test_acceptable_risk_reward_ratio(self, risk_engine, test_risk_limit):
        """Test order with acceptable R/R ratio."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),  # Risk: $1,000
            take_profit=Decimal("42500"),  # Reward: $2,500 (2.5:1 ratio)
        )

        assert result.approved is True
        # Aggregate approval message; individual R/R message is in an earlier step.
        assert "approved" in result.message.lower()

    def test_poor_risk_reward_ratio(self, risk_engine, test_risk_limit):
        """Test order with poor R/R ratio."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39900"),  # Risk: $100
            take_profit=Decimal("40100"),  # Reward: $100 (1:1 ratio - too low)
        )

        assert result.approved is False
        assert result.reason == "RISK_REWARD_TOO_LOW"

    def test_short_position_rr_ratio(self, risk_engine, test_risk_limit):
        """Test R/R ratio for SHORT positions."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="SELL",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("41000"),  # Risk: $1,000
            take_profit=Decimal("38500"),  # Reward: $1,500 (1.5:1 ratio)
        )

        assert result.approved is True
        assert "approved" in result.message.lower()

    def test_invalid_stop_loss_buy(self, risk_engine, test_risk_limit):
        """Test that BUY order cannot have SL above entry."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("41000"),  # Invalid: above entry
            take_profit=Decimal("42000"),
        )

        assert result.approved is False
        assert result.reason == "INVALID_STOP_LOSS"

    def test_invalid_take_profit_buy(self, risk_engine, test_risk_limit):
        """Test that BUY order cannot have TP below entry."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("39500"),  # Invalid: below entry
        )

        assert result.approved is False
        assert result.reason == "INVALID_TAKE_PROFIT"


class TestDrawdownValidation:
    """Test drawdown limit validation."""

    def test_drawdown_within_limit(self, risk_engine, test_risk_limit):
        """Test trading allowed when drawdown within limit."""
        test_risk_limit.current_drawdown_pct = -0.10  # Within -15% limit

        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )

        assert result.approved is True

    def test_drawdown_exceeds_limit(self, risk_engine, test_risk_limit):
        """Test trading halted when drawdown breaches limit."""
        test_risk_limit.current_drawdown_pct = -0.16  # Exceeds -15% limit

        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )

        assert result.approved is False
        assert result.reason == "DRAWDOWN_LIMIT_BREACHED"
        assert result.halt_triggered is True

    def test_halt_prevents_new_orders(self, risk_engine, test_risk_limit):
        """Test that trading halt prevents all new orders."""
        test_risk_limit.is_halted = True

        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )

        assert result.approved is False
        assert result.reason == "DRAWDOWN_HALT"
        assert result.halt_triggered is True


class TestDailyLossValidation:
    """Test daily loss limit validation."""

    def test_daily_loss_within_limit(self, risk_engine, test_risk_limit):
        """Test trading allowed when daily loss within limit."""
        test_risk_limit.current_daily_loss_pct = -0.15  # Within -20% limit

        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )

        assert result.approved is True

    def test_daily_loss_exceeds_limit(self, risk_engine, test_risk_limit):
        """Test trading blocked when daily loss exceeds limit."""
        test_risk_limit.current_daily_loss_pct = -0.21  # Exceeds -20% limit

        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )

        assert result.approved is False
        assert result.reason == "DAILY_LOSS_LIMIT_BREACHED"


class TestPositionSizeCalculation:
    """Test position size calculation utility."""

    def test_calculate_position_size_1_percent_risk(self, risk_engine):
        """Test calculating position size for 1% risk."""
        account_balance = Decimal("100000")
        risk_pct = 0.01  # 1% risk
        entry_price = Decimal("40000")
        stop_loss = Decimal("39000")  # $1,000 risk per unit

        position_size = risk_engine.calculate_position_size(
            account_balance, risk_pct, entry_price, stop_loss
        )

        # 1% of $100k = $1,000 / $1,000 risk per unit = 1 BTC
        assert position_size == Decimal("1.0")

    def test_calculate_position_size_2_percent_risk(self, risk_engine):
        """Test calculating position size for 2% risk."""
        account_balance = Decimal("50000")
        risk_pct = 0.02  # 2% risk
        entry_price = Decimal("100")
        stop_loss = Decimal("90")  # $10 risk per unit

        position_size = risk_engine.calculate_position_size(
            account_balance, risk_pct, entry_price, stop_loss
        )

        # 2% of $50k = $1,000 / $10 risk per unit = 100 units
        assert position_size == Decimal("100")

    def test_calculate_position_size_zero_risk(self, risk_engine):
        """Test position size calculation with zero risk."""
        account_balance = Decimal("100000")
        risk_pct = 0.01
        entry_price = Decimal("40000")
        stop_loss = Decimal("40000")  # No risk

        position_size = risk_engine.calculate_position_size(
            account_balance, risk_pct, entry_price, stop_loss
        )

        # Zero risk per unit = zero position size
        assert position_size == Decimal("0")


class TestCheckDrawdownHalt:
    """Test drawdown halt logic."""

    def test_halt_triggered_on_breach(self, risk_engine, test_risk_limit):
        """Test that halt is triggered when drawdown breaches limit."""
        test_risk_limit.current_drawdown_pct = -0.16
        test_risk_limit.max_drawdown_pct = -0.15
        test_risk_limit.halt_on_breach = True

        halt_triggered = risk_engine.check_drawdown_halt("test_session")

        assert halt_triggered is True
        # Verify halt flag was set
        assert test_risk_limit.is_halted is True

    def test_halt_not_triggered_within_limit(self, risk_engine, test_risk_limit):
        """Test that halt is not triggered within limits."""
        test_risk_limit.current_drawdown_pct = -0.10
        test_risk_limit.max_drawdown_pct = -0.15
        test_risk_limit.halt_on_breach = True

        halt_triggered = risk_engine.check_drawdown_halt("test_session")

        assert halt_triggered is False
        assert test_risk_limit.is_halted is False


class TestIntegrationScenarios:
    """Integration tests with multiple validation checks."""

    def test_perfect_trade_setup(self, risk_engine, test_risk_limit):
        """Test ideal trade setup passes all validations."""
        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.25"),  # 10% of account
            entry_price=Decimal("40000"),
            stop_loss=Decimal("38000"),  # $2,000 risk
            take_profit=Decimal("44000"),  # $4,000 reward (2:1 ratio)
        )

        assert result.approved is True
        assert result.level == RiskLevel.OK

    def test_trading_halt_scenario(self, risk_engine, test_risk_limit):
        """Test complete trading halt scenario."""
        # Simulate significant loss
        test_risk_limit.current_drawdown_pct = -0.16
        test_risk_limit.is_halted = True

        result = risk_engine.validate_order(
            session_id="test_session",
            account_balance=Decimal("100000"),
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("0.1"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )

        assert result.approved is False
        assert result.halt_triggered is True
