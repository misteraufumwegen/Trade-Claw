"""
Tests for FastAPI main application
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Trading Bot API" in response.json()["message"]


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "trading-bot-api"


def test_status_endpoint(client):
    """Test status endpoint"""
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "components" in response.json()


def test_get_accounts_placeholder(client):
    """Test accounts endpoint (placeholder)"""
    response = client.get("/api/accounts")
    assert response.status_code == 200


def test_get_positions_placeholder(client):
    """Test positions endpoint (placeholder)"""
    response = client.get("/api/positions")
    assert response.status_code == 200


def test_get_orders_placeholder(client):
    """Test orders endpoint (placeholder)"""
    response = client.get("/api/orders")
    assert response.status_code == 200


def test_create_order_placeholder(client):
    """Test order creation endpoint (placeholder)"""
    response = client.post("/api/orders")
    assert response.status_code == 200
