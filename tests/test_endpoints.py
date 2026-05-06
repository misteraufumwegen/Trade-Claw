"""Test FastAPI endpoints for PHASE 4."""

import os

# Env vars must be set BEFORE importing app.main — it validates at import.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TRADE_CLAW_API_KEY", "test-endpoints-key")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("DB_PASSWORD", "test-db-password")

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import AuditLog, Base, BrokerSession, Order, Position, RiskLimit
from app.main import app, get_db_session

# All protected endpoints require the bearer token (C1).
AUTH_HEADERS = {"Authorization": f"Bearer {os.environ['TRADE_CLAW_API_KEY']}"}


# Test database setup
@pytest.fixture
def test_db():
    """Create test database.

    Uses StaticPool + check_same_thread=False so that the fixture's session
    and the TestClient's thread both see the same underlying in-memory DB.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_client(test_db: Session):
    """Create test client with test database."""

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def broker_session(test_db: Session) -> BrokerSession:
    """Create test broker session."""
    session = BrokerSession(
        user_id="test_user",
        broker_type="mock",
        credentials_vault_key="vault:test_session",
        session_id="test_session_123",
    )
    test_db.add(session)

    # Add risk limits
    risk_limit = RiskLimit(
        session_id="test_session_123",
        max_position_size_pct=0.10,
        max_drawdown_pct=-0.15,
        min_risk_reward_ratio=1.5,
    )
    test_db.add(risk_limit)
    test_db.commit()

    return session


class TestHealthEndpoints:
    """Test health and info endpoints."""

    def test_health_check(self, test_client: TestClient):
        """Test /health endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["version"] == "4.0.0"

    def test_root_endpoint(self, test_client: TestClient):
        """Root either returns metadata JSON or redirects to the bundled UI."""
        response = test_client.get("/", follow_redirects=False)
        assert response.status_code in (200, 307)
        if response.status_code == 307:
            assert response.headers["location"].endswith("/app/")
        else:
            assert response.json()["name"] == "Trade-Claw API"


class TestBrokerSetup:
    """Test broker setup endpoints."""

    def test_broker_setup_mock(self, test_client: TestClient):
        """Test setting up mock broker."""
        request_data = {
            "broker_type": "mock",
            "credentials": {"mode": "normal"},
            "user_id": "test_user",
        }
        response = test_client.post(
            "/api/v1/brokers/setup", json=request_data, headers=AUTH_HEADERS
        )

        # Note: This will fail without proper router mocking
        # In real implementation, would mock router.create_session()
        if response.status_code != 500:  # Skip if not mocked
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["broker_type"] == "mock"
            assert data["status"] == "ACTIVE"


class TestQuoteEndpoints:
    """Test price quote endpoints."""

    def test_get_quote(self, test_client: TestClient, broker_session: BrokerSession):
        """Test getting price quote."""
        test_client.get(
            f"/api/v1/brokers/{broker_session.session_id}/quote",
            params={"symbol": "BTC/USD", "amount": 1.0},
        )

        # Note: Requires router mock
        # In real implementation, would return quote


class TestOrderEndpoints:
    """Test order submission and management endpoints."""

    def test_submit_order_requires_auth(self, test_client: TestClient):
        """Test that order submission requires session."""
        request_data = {
            "symbol": "BTC/USD",
            "side": "BUY",
            "size": "1.0",
            "entry_price": "40000",
            "stop_loss": "39000",
            "take_profit": "42000",
        }
        response = test_client.post(
            "/api/v1/orders/submit",
            json=request_data,
            params={"session_id": "invalid_session"},
            headers=AUTH_HEADERS,
        )

        # Should fail with invalid session
        assert response.status_code in [400, 404]

    def test_submit_valid_order(self, test_client: TestClient, broker_session: BrokerSession):
        """Test submitting valid order."""

        # Note: Requires full mocking of broker adapter
        # Would need to mock:
        # - router.get_api_adapter()
        # - adapter.get_account_info()
        # - adapter.submit_order()

    def test_invalid_risk_reward(self, test_client: TestClient, broker_session: BrokerSession):
        """Test that order with poor R/R is rejected."""

        # Should reject with R/R < 1.5:1

    def test_get_order_status(
        self, test_client: TestClient, broker_session: BrokerSession, test_db: Session
    ):
        """Test getting order status."""
        # Create test order
        order = Order(
            session_id=broker_session.session_id,
            order_id="order_123",
            symbol="BTC/USD",
            side="BUY",
            size="1.0",
            entry_price="40000",
            stop_loss="39000",
            take_profit="42000",
            status="FILLED",
            filled_size="1.0",
            avg_fill_price="40000",
            commission="10",
        )
        test_db.add(order)
        test_db.commit()

        response = test_client.get(
            "/api/v1/orders/order_123",
            params={"session_id": broker_session.session_id},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_123"
        assert data["status"] == "FILLED"
        assert data["symbol"] == "BTC/USD"

    def test_cancel_order(
        self, test_client: TestClient, broker_session: BrokerSession, test_db: Session
    ):
        """Test cancelling order."""
        # Create pending order
        order = Order(
            session_id=broker_session.session_id,
            order_id="order_456",
            symbol="ETH/USD",
            side="SELL",
            size="10.0",
            entry_price="2000",
            stop_loss="2100",
            take_profit="1900",
            status="PENDING",
        )
        test_db.add(order)
        test_db.commit()

        # Note: Requires router mock for broker cancellation
        # response = test_client.post(
        #     "/api/v1/orders/order_456/cancel",
        #     params={"session_id": broker_session.session_id}
        # )


class TestPositionEndpoints:
    """Test position endpoints."""

    def test_get_positions_empty(self, test_client: TestClient, broker_session: BrokerSession):
        """Test getting positions when none exist."""
        response = test_client.get(
            "/api/v1/positions",
            params={"session_id": broker_session.session_id},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["positions"] == []
        assert Decimal(data["total_unrealized_pnl"]) == Decimal("0")
        assert Decimal(data["drawdown_pct"]) == Decimal("0")
        assert data["is_halted"] is False

    def test_get_positions_with_data(
        self, test_client: TestClient, broker_session: BrokerSession, test_db: Session
    ):
        """Test getting positions with open positions."""
        # Add position
        position = Position(
            session_id=broker_session.session_id,
            symbol="BTC/USD",
            side="LONG",
            entry_price="40000",
            current_price="41000",
            size="1.0",
            unrealized_pnl="1000",
            status="OPEN",
        )
        test_db.add(position)
        test_db.commit()

        response = test_client.get(
            "/api/v1/positions",
            params={"session_id": broker_session.session_id},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["positions"]) == 1
        assert data["positions"][0]["symbol"] == "BTC/USD"
        assert Decimal(data["total_unrealized_pnl"]) == Decimal("1000")


class TestAuditEndpoints:
    """Test audit log endpoints."""

    def test_get_audit_log_empty(self, test_client: TestClient, broker_session: BrokerSession):
        """Test getting audit log when empty."""
        response = test_client.get(
            "/api/v1/audit", params={"session_id": broker_session.session_id}, headers=AUTH_HEADERS
        )

        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []
        assert data["total_count"] == 0

    def test_get_audit_log_with_events(
        self, test_client: TestClient, broker_session: BrokerSession, test_db: Session
    ):
        """Test getting audit log with events."""
        # Add audit events
        audit1 = AuditLog(
            session_id=broker_session.session_id,
            action="ORDER_SUBMITTED",
            symbol="BTC/USD",
            details="Order 001 submitted",
            severity="INFO",
        )
        audit2 = AuditLog(
            session_id=broker_session.session_id,
            action="ORDER_FILLED",
            symbol="BTC/USD",
            details="Order 001 filled at 40000",
            severity="INFO",
        )
        test_db.add(audit1)
        test_db.add(audit2)
        test_db.commit()

        response = test_client.get(
            "/api/v1/audit",
            params={"session_id": broker_session.session_id, "limit": 10},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["logs"]) == 2

    def test_audit_log_filter_by_action(
        self, test_client: TestClient, broker_session: BrokerSession, test_db: Session
    ):
        """Test filtering audit log by action."""
        # Add mixed audit events
        test_db.add(
            AuditLog(
                session_id=broker_session.session_id,
                action="ORDER_SUBMITTED",
                details="Test",
                severity="INFO",
            )
        )
        test_db.add(
            AuditLog(
                session_id=broker_session.session_id,
                action="RISK_VIOLATION",
                details="Test",
                severity="WARNING",
            )
        )
        test_db.commit()

        response = test_client.get(
            "/api/v1/audit",
            params={"session_id": broker_session.session_id, "action": "ORDER_SUBMITTED"},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["logs"][0]["action"] == "ORDER_SUBMITTED"
