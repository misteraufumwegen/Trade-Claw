"""
Tests for the FastAPI application in ``app.main``.

These cover:
- Unauthenticated endpoints (/, /health)
- The API-key authentication (C1)
- Pydantic request validation (H3, H8)
- Audit-log enum filter validation
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Set env BEFORE importing app.main — it validates secrets at import time.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TRADE_CLAW_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("DB_PASSWORD", "test-db-password")

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth() -> dict:
    return {"Authorization": f"Bearer {os.environ['TRADE_CLAW_API_KEY']}"}


# ---------------------------------------------------------------------------
# Unauthenticated endpoints
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Trade-Claw API"
    assert body["docs"] == "/docs"


# ---------------------------------------------------------------------------
# API-key authentication (C1)
# ---------------------------------------------------------------------------


def test_protected_endpoint_requires_auth(client: TestClient) -> None:
    r = client.get("/api/v1/positions?session_id=any")
    assert r.status_code == 401


def test_protected_endpoint_rejects_wrong_key(client: TestClient) -> None:
    r = client.get(
        "/api/v1/positions?session_id=any",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 403


def test_protected_endpoint_accepts_correct_key(client: TestClient, auth: dict) -> None:
    r = client.get("/api/v1/positions?session_id=does-not-exist", headers=auth)
    assert r.status_code == 200  # empty list


# ---------------------------------------------------------------------------
# Order-submit validation (H3, H8)
# ---------------------------------------------------------------------------


ORDER_BASE = {
    "symbol": "BTC/USD",
    "side": "BUY",
    "size": 1,
    "entry_price": 50_000,
    "stop_loss": 49_000,
    "take_profit": 52_000,
}


@pytest.mark.parametrize(
    "override",
    [
        {"size": -1},  # negative size
        {"size": 0},  # zero size
        {"entry_price": 0},  # zero price
        {"stop_loss": 50_000},  # equals entry
        {"take_profit": 50_000},  # equals entry
        {"stop_loss": 52_000},  # SL above entry for BUY
        {"take_profit": 49_500},  # TP below entry for BUY
        {"symbol": "bad symbol!"},  # regex fail
        {"symbol": "btcusd"},  # lowercase fail
        {"side": "INVALID"},  # unknown side
    ],
)
def test_submit_order_invalid_inputs_rejected(
    client: TestClient, auth: dict, override: dict
) -> None:
    payload = {**ORDER_BASE, **override}
    r = client.post(
        "/api/v1/orders/submit?session_id=s1",
        headers=auth,
        json=payload,
    )
    assert r.status_code == 422, r.json()


def test_submit_order_session_not_found(client: TestClient, auth: dict) -> None:
    # Valid payload, but session doesn't exist -> 404.
    r = client.post(
        "/api/v1/orders/submit?session_id=nonexistent",
        headers=auth,
        json=ORDER_BASE,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Broker-setup validation (H3)
# ---------------------------------------------------------------------------


def test_setup_broker_rejects_unknown_broker(client: TestClient, auth: dict) -> None:
    r = client.post(
        "/api/v1/brokers/setup",
        headers=auth,
        json={"broker_type": "rogue-broker", "credentials": {"api_key": "x"}},
    )
    assert r.status_code == 422


def test_setup_broker_rejects_empty_credentials(client: TestClient, auth: dict) -> None:
    r = client.post(
        "/api/v1/brokers/setup",
        headers=auth,
        json={"broker_type": "mock", "credentials": {}},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Audit-log filter whitelist
# ---------------------------------------------------------------------------


def test_audit_rejects_unknown_severity(client: TestClient, auth: dict) -> None:
    r = client.get(
        "/api/v1/audit?session_id=s1&severity=HACKED",
        headers=auth,
    )
    assert r.status_code == 400


def test_audit_rejects_unknown_action(client: TestClient, auth: dict) -> None:
    r = client.get(
        "/api/v1/audit?session_id=s1&action=DROP_TABLE",
        headers=auth,
    )
    assert r.status_code == 400
