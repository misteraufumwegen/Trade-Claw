"""Pytest configuration and fixtures for Trade-Claw tests."""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.models import Base, BrokerSession, RiskLimit, Order, Position, AuditLog
from app.risk import RiskEngine


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine (session-scoped)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture
def db_session(db_engine):
    """Create fresh database session for each test."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    # Cleanup after test
    session.rollback()
    session.close()


# ============================================================================
# Broker Session Fixtures
# ============================================================================


@pytest.fixture
def broker_session(db_session: Session) -> BrokerSession:
    """Create test broker session."""
    session = BrokerSession(
        user_id="test_user_123",
        broker_type="mock",
        credentials_vault_key="vault:test_session_key",
        session_id="test_session_abc123",
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture
def hyperliquid_session(db_session: Session) -> BrokerSession:
    """Create Hyperliquid test session."""
    session = BrokerSession(
        user_id="test_user_123",
        broker_type="hyperliquid",
        credentials_vault_key="vault:hyperliquid_key",
        session_id="test_session_hyperliquid",
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture
def alpaca_session(db_session: Session) -> BrokerSession:
    """Create Alpaca test session."""
    session = BrokerSession(
        user_id="test_user_123",
        broker_type="alpaca",
        credentials_vault_key="vault:alpaca_key",
        session_id="test_session_alpaca",
    )
    db_session.add(session)
    db_session.commit()
    return session


# ============================================================================
# Risk Limit Fixtures
# ============================================================================


@pytest.fixture
def risk_limit(db_session: Session, broker_session: BrokerSession) -> RiskLimit:
    """Create test risk limit."""
    risk_limit = RiskLimit(
        session_id=broker_session.session_id,
        max_position_size_pct=0.10,  # 10%
        max_drawdown_pct=-0.15,  # -15%
        max_daily_loss_pct=-0.20,  # -20%
        min_risk_reward_ratio=1.5,
        sl_immutable=True,
        halt_on_breach=True,
        is_halted=False,
    )
    db_session.add(risk_limit)
    db_session.commit()
    return risk_limit


@pytest.fixture
def aggressive_risk_limit(db_session: Session, broker_session: BrokerSession) -> RiskLimit:
    """Create aggressive risk limit for testing."""
    risk_limit = RiskLimit(
        session_id=broker_session.session_id,
        max_position_size_pct=0.20,  # 20%
        max_drawdown_pct=-0.10,  # -10%
        max_daily_loss_pct=-0.15,  # -15%
        min_risk_reward_ratio=1.0,  # Minimum 1:1
    )
    db_session.add(risk_limit)
    db_session.commit()
    return risk_limit


# ============================================================================
# Order Fixtures
# ============================================================================


@pytest.fixture
def pending_order(db_session: Session, broker_session: BrokerSession) -> Order:
    """Create test pending order."""
    order = Order(
        session_id=broker_session.session_id,
        order_id="order_pending_001",
        symbol="BTC/USD",
        side="BUY",
        size=Decimal("0.5"),
        entry_price=Decimal("40000"),
        stop_loss=Decimal("38000"),
        take_profit=Decimal("44000"),
        status="PENDING",
        risk_ratio=2.0,
    )
    db_session.add(order)
    db_session.commit()
    return order


@pytest.fixture
def filled_order(db_session: Session, broker_session: BrokerSession) -> Order:
    """Create test filled order."""
    order = Order(
        session_id=broker_session.session_id,
        order_id="order_filled_001",
        symbol="ETH/USD",
        side="BUY",
        size=Decimal("10.0"),
        entry_price=Decimal("2000"),
        stop_loss=Decimal("1900"),
        take_profit=Decimal("2200"),
        status="FILLED",
        filled_size=Decimal("10.0"),
        avg_fill_price=Decimal("2000"),
        commission=Decimal("20"),
        pnl=Decimal("1980"),  # (2200 - 2000) * 10 - 20 = 1980
        filled_at=datetime.utcnow(),
        risk_ratio=2.0,
    )
    db_session.add(order)
    db_session.commit()
    return order


@pytest.fixture
def rejected_order(db_session: Session, broker_session: BrokerSession) -> Order:
    """Create test rejected order."""
    order = Order(
        session_id=broker_session.session_id,
        order_id="order_rejected_001",
        symbol="SOL/USD",
        side="SELL",
        size=Decimal("100.0"),
        entry_price=Decimal("100"),
        stop_loss=Decimal("110"),
        take_profit=Decimal("90"),
        status="REJECTED",
        risk_ratio=1.0,
    )
    db_session.add(order)
    db_session.commit()
    return order


# ============================================================================
# Position Fixtures
# ============================================================================


@pytest.fixture
def long_position(db_session: Session, broker_session: BrokerSession) -> Position:
    """Create test long position."""
    position = Position(
        session_id=broker_session.session_id,
        symbol="BTC/USD",
        side="LONG",
        entry_price=Decimal("40000"),
        current_price=Decimal("41500"),
        size=Decimal("1.0"),
        unrealized_pnl=Decimal("1500"),
        status="OPEN",
    )
    db_session.add(position)
    db_session.commit()
    return position


@pytest.fixture
def short_position(db_session: Session, broker_session: BrokerSession) -> Position:
    """Create test short position."""
    position = Position(
        session_id=broker_session.session_id,
        symbol="ETH/USD",
        side="SHORT",
        entry_price=Decimal("2000"),
        current_price=Decimal("1950"),
        size=Decimal("10.0"),
        unrealized_pnl=Decimal("500"),
        status="OPEN",
    )
    db_session.add(position)
    db_session.commit()
    return position


@pytest.fixture
def closed_position(db_session: Session, broker_session: BrokerSession) -> Position:
    """Create test closed position."""
    position = Position(
        session_id=broker_session.session_id,
        symbol="SOL/USD",
        side="LONG",
        entry_price=Decimal("100"),
        current_price=Decimal("102"),
        size=Decimal("100"),
        unrealized_pnl=Decimal("200"),
        status="CLOSED",
        closed_at=datetime.utcnow(),
    )
    db_session.add(position)
    db_session.commit()
    return position


# ============================================================================
# Audit Log Fixtures
# ============================================================================


@pytest.fixture
def audit_logs(db_session: Session, broker_session: BrokerSession) -> list:
    """Create test audit log entries."""
    logs = [
        AuditLog(
            session_id=broker_session.session_id,
            action="SESSION_CREATED",
            details="User session initialized",
            severity="INFO",
        ),
        AuditLog(
            session_id=broker_session.session_id,
            action="ORDER_SUBMITTED",
            symbol="BTC/USD",
            details="Market order submitted: BUY 1.0 BTC @ market",
            severity="INFO",
        ),
        AuditLog(
            session_id=broker_session.session_id,
            action="RISK_CHECK_PASSED",
            symbol="BTC/USD",
            details="Order passed risk validation (R/R: 2.0:1)",
            severity="INFO",
        ),
        AuditLog(
            session_id=broker_session.session_id,
            action="ORDER_FILLED",
            symbol="BTC/USD",
            details="Order filled at 40000",
            severity="INFO",
        ),
        AuditLog(
            session_id=broker_session.session_id,
            action="POSITION_OPENED",
            symbol="BTC/USD",
            details="Long position opened: 1.0 BTC @ 40000",
            severity="INFO",
        ),
    ]
    
    for log in logs:
        db_session.add(log)
    db_session.commit()
    
    return logs


# ============================================================================
# Risk Engine Fixtures
# ============================================================================


@pytest.fixture
def risk_engine(db_session: Session) -> RiskEngine:
    """Create test risk engine."""
    return RiskEngine(db_session)


# ============================================================================
# Test Data Generation Helpers
# ============================================================================


@pytest.fixture
def sample_account():
    """Sample account data."""
    return {
        "balance": Decimal("100000"),
        "equity": Decimal("100000"),
        "margin_used": Decimal("0"),
        "margin_available": Decimal("100000"),
        "currency": "USD",
    }


@pytest.fixture
def sample_quote():
    """Sample price quote."""
    return {
        "symbol": "BTC/USD",
        "bid": Decimal("39950"),
        "ask": Decimal("40000"),
        "last": Decimal("39975"),
        "liquidity": "HIGH",
        "estimated_fees": Decimal("5"),
    }


@pytest.fixture
def sample_order_params():
    """Sample order submission parameters."""
    return {
        "symbol": "BTC/USD",
        "side": "BUY",
        "size": Decimal("0.5"),
        "entry_price": Decimal("40000"),
        "stop_loss": Decimal("38000"),
        "take_profit": Decimal("44000"),
    }


# ============================================================================
# Marker Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "risk: Risk engine tests")
    config.addinivalue_line("markers", "broker: Broker adapter tests")
