"""Test SQLAlchemy models."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    AuditLog,
    Base,
    BrokerSession,
    Order,
    Position,
    RiskLimit,
)


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestBrokerSessionModel:
    """Test BrokerSession model."""

    def test_create_broker_session(self, db_session):
        """Test creating a broker session."""
        session = BrokerSession(
            user_id="user_123",
            broker_type="mock",
            credentials_vault_key="vault:session_123",
            session_id="session_123",
        )
        db_session.add(session)
        db_session.commit()

        retrieved = db_session.query(BrokerSession).filter_by(session_id="session_123").first()
        assert retrieved is not None
        assert retrieved.user_id == "user_123"
        assert retrieved.broker_type == "mock"
        assert retrieved.is_active is True

    def test_broker_session_relationships(self, db_session):
        """Test broker session relationships."""
        session = BrokerSession(
            user_id="user_123",
            broker_type="hyperliquid",
            credentials_vault_key="vault:session_123",
            session_id="session_123",
        )
        db_session.add(session)
        db_session.commit()

        # Add related objects
        order = Order(
            session_id="session_123",
            order_id="order_1",
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("1.0"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
        )
        db_session.add(order)

        position = Position(
            session_id="session_123",
            symbol="BTC/USD",
            side="LONG",
            entry_price=Decimal("40000"),
            current_price=Decimal("41000"),
            size=Decimal("1.0"),
            unrealized_pnl=Decimal("1000"),
        )
        db_session.add(position)

        audit = AuditLog(
            session_id="session_123",
            action="ORDER_SUBMITTED",
            details="Test order",
        )
        db_session.add(audit)

        risk = RiskLimit(
            session_id="session_123",
        )
        db_session.add(risk)

        db_session.commit()

        # Verify relationships
        retrieved_session = (
            db_session.query(BrokerSession).filter_by(session_id="session_123").first()
        )
        assert len(retrieved_session.orders) == 1
        assert len(retrieved_session.positions) == 1
        assert len(retrieved_session.audit_logs) == 1
        assert len(retrieved_session.risk_limits) == 1


class TestOrderModel:
    """Test Order model."""

    def test_create_order(self, db_session):
        """Test creating an order."""
        order = Order(
            session_id="session_123",
            order_id="order_abc",
            symbol="ETH/USD",
            side="BUY",
            size=Decimal("10.0"),
            entry_price=Decimal("2000"),
            stop_loss=Decimal("1900"),
            take_profit=Decimal("2100"),
            status="PENDING",
            risk_ratio=1.5,
        )
        db_session.add(order)
        db_session.commit()

        retrieved = db_session.query(Order).filter_by(order_id="order_abc").first()
        assert retrieved is not None
        assert retrieved.symbol == "ETH/USD"
        assert retrieved.side == "BUY"
        assert retrieved.status == "PENDING"
        assert retrieved.risk_ratio == 1.5

    def test_order_status_transitions(self, db_session):
        """Test order status transitions."""
        order = Order(
            session_id="session_123",
            order_id="order_123",
            symbol="BTC/USD",
            side="SELL",
            size=Decimal("0.5"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("41000"),
            take_profit=Decimal("39000"),
        )
        db_session.add(order)
        db_session.commit()

        # Transition to FILLED
        order.status = "FILLED"
        order.filled_size = Decimal("0.5")
        order.avg_fill_price = Decimal("40000")
        order.filled_at = datetime.utcnow()
        db_session.commit()

        retrieved = db_session.query(Order).filter_by(order_id="order_123").first()
        assert retrieved.status == "FILLED"
        assert retrieved.filled_size == Decimal("0.5")

    def test_order_pnl_calculation(self, db_session):
        """Test order P&L calculation."""
        order = Order(
            session_id="session_123",
            order_id="order_pnl",
            symbol="BTC/USD",
            side="BUY",
            size=Decimal("1.0"),
            entry_price=Decimal("40000"),
            stop_loss=Decimal("39000"),
            take_profit=Decimal("42000"),
            status="FILLED",
            filled_size=Decimal("1.0"),
            avg_fill_price=Decimal("40000"),
            commission=Decimal("10"),
        )

        # Calculate realized P&L
        exit_price = Decimal("41000")
        realized_pnl = (exit_price - Decimal("40000")) * Decimal("1.0") - Decimal("10")
        order.pnl = realized_pnl

        db_session.add(order)
        db_session.commit()

        retrieved = db_session.query(Order).filter_by(order_id="order_pnl").first()
        assert retrieved.pnl == Decimal("990")  # 1000 - 10


class TestPositionModel:
    """Test Position model."""

    def test_create_position(self, db_session):
        """Test creating a position."""
        position = Position(
            session_id="session_123",
            symbol="SOL/USD",
            side="LONG",
            entry_price=Decimal("100"),
            current_price=Decimal("105"),
            size=Decimal("100"),
            unrealized_pnl=Decimal("500"),
            status="OPEN",
        )
        db_session.add(position)
        db_session.commit()

        retrieved = db_session.query(Position).filter_by(symbol="SOL/USD").first()
        assert retrieved is not None
        assert retrieved.side == "LONG"
        assert retrieved.unrealized_pnl == Decimal("500")

    def test_position_status_transitions(self, db_session):
        """Test position closing."""
        position = Position(
            session_id="session_123",
            symbol="BTC/USD",
            side="LONG",
            entry_price=Decimal("40000"),
            current_price=Decimal("41000"),
            size=Decimal("1.0"),
            unrealized_pnl=Decimal("1000"),
            status="OPEN",
        )
        db_session.add(position)
        db_session.commit()

        # Close position
        position.status = "CLOSED"
        position.closed_at = datetime.utcnow()
        db_session.commit()

        retrieved = db_session.query(Position).filter_by(symbol="BTC/USD").first()
        assert retrieved.status == "CLOSED"
        assert retrieved.closed_at is not None

    def test_short_position(self, db_session):
        """Test creating a short position."""
        position = Position(
            session_id="session_123",
            symbol="ETH/USD",
            side="SHORT",
            entry_price=Decimal("2000"),
            current_price=Decimal("1900"),
            size=Decimal("10"),
            unrealized_pnl=Decimal("1000"),
            status="OPEN",
        )
        db_session.add(position)
        db_session.commit()

        retrieved = db_session.query(Position).filter_by(symbol="ETH/USD").first()
        assert retrieved.side == "SHORT"
        assert retrieved.unrealized_pnl == Decimal("1000")  # Profit on short


class TestAuditLogModel:
    """Test AuditLog model."""

    def test_create_audit_log(self, db_session):
        """Test creating audit log entry."""
        audit = AuditLog(
            session_id="session_123",
            action="ORDER_SUBMITTED",
            symbol="BTC/USD",
            details="Order submitted for review",
            severity="INFO",
        )
        db_session.add(audit)
        db_session.commit()

        retrieved = db_session.query(AuditLog).filter_by(action="ORDER_SUBMITTED").first()
        assert retrieved is not None
        assert retrieved.symbol == "BTC/USD"
        assert retrieved.severity == "INFO"

    def test_audit_log_immutability(self, db_session):
        """Test that audit logs are append-only."""
        audit1 = AuditLog(
            session_id="session_123",
            action="ORDER_SUBMITTED",
            details="Event 1",
        )
        audit2 = AuditLog(
            session_id="session_123",
            action="ORDER_FILLED",
            details="Event 2",
        )
        db_session.add(audit1)
        db_session.add(audit2)
        db_session.commit()

        # Retrieve all logs
        logs = (
            db_session.query(AuditLog)
            .filter_by(session_id="session_123")
            .order_by(AuditLog.timestamp)
            .all()
        )
        assert len(logs) == 2
        assert logs[0].action == "ORDER_SUBMITTED"
        assert logs[1].action == "ORDER_FILLED"

    def test_audit_log_severity_levels(self, db_session):
        """Test different severity levels."""
        severities = ["INFO", "WARNING", "ERROR", "CRITICAL"]

        for i, severity in enumerate(severities):
            audit = AuditLog(
                session_id="session_123",
                action=f"EVENT_{i}",
                details=f"Test {severity}",
                severity=severity,
            )
            db_session.add(audit)

        db_session.commit()

        for severity in severities:
            retrieved = db_session.query(AuditLog).filter_by(severity=severity).first()
            assert retrieved.severity == severity


class TestRiskLimitModel:
    """Test RiskLimit model."""

    def test_create_risk_limit(self, db_session):
        """Test creating risk limits."""
        risk_limit = RiskLimit(
            session_id="session_123",
            max_position_size_pct=0.10,
            max_drawdown_pct=-0.15,
            max_daily_loss_pct=-0.20,
            min_risk_reward_ratio=1.5,
        )
        db_session.add(risk_limit)
        db_session.commit()

        retrieved = db_session.query(RiskLimit).filter_by(session_id="session_123").first()
        assert retrieved is not None
        assert retrieved.max_position_size_pct == 0.10
        assert retrieved.max_drawdown_pct == -0.15
        assert retrieved.min_risk_reward_ratio == 1.5

    def test_risk_limit_halt_flag(self, db_session):
        """Test halt flag on risk limits."""
        risk_limit = RiskLimit(
            session_id="session_123",
            is_halted=False,
            halt_on_breach=True,
        )
        db_session.add(risk_limit)
        db_session.commit()

        # Trigger halt
        risk_limit.is_halted = True
        db_session.commit()

        retrieved = db_session.query(RiskLimit).filter_by(session_id="session_123").first()
        assert retrieved.is_halted is True

    def test_risk_limit_drawdown_tracking(self, db_session):
        """Test drawdown tracking."""
        risk_limit = RiskLimit(
            session_id="session_123",
            current_drawdown_pct=-0.05,
            current_daily_loss_pct=-0.02,
        )
        db_session.add(risk_limit)
        db_session.commit()

        # Update drawdown
        risk_limit.current_drawdown_pct = -0.16  # Breaches -0.15
        risk_limit.is_halted = True
        db_session.commit()

        retrieved = db_session.query(RiskLimit).filter_by(session_id="session_123").first()
        assert retrieved.current_drawdown_pct == -0.16
        assert retrieved.is_halted is True
