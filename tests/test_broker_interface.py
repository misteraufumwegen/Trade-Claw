"""
Tests for BrokerInterface and broker abstract base class
"""

import pytest
from app.interfaces.broker import (
    BrokerInterface,
    OrderStatus,
    OrderType,
    OrderSide,
    TimeInForce,
)


def test_order_status_enum():
    """Test OrderStatus enum values"""
    assert OrderStatus.PENDING.value == "pending"
    assert OrderStatus.FILLED.value == "filled"
    assert OrderStatus.CANCELLED.value == "cancelled"


def test_order_type_enum():
    """Test OrderType enum values"""
    assert OrderType.MARKET.value == "market"
    assert OrderType.LIMIT.value == "limit"
    assert OrderType.STOP.value == "stop"


def test_order_side_enum():
    """Test OrderSide enum values"""
    assert OrderSide.BUY.value == "buy"
    assert OrderSide.SELL.value == "sell"


def test_time_in_force_enum():
    """Test TimeInForce enum values"""
    assert TimeInForce.DAY.value == "day"
    assert TimeInForce.GTC.value == "gtc"
    assert TimeInForce.IOC.value == "ioc"
    assert TimeInForce.FOK.value == "fok"


def test_broker_interface_is_abstract():
    """Test that BrokerInterface cannot be instantiated directly"""
    with pytest.raises(TypeError):
        broker = BrokerInterface(
            broker_name="test",
            api_key="test_key",
            api_secret="test_secret"
        )


class MockBrokerAdapter(BrokerInterface):
    """Mock broker adapter for testing"""

    async def connect(self) -> bool:
        self._is_connected = True
        return True

    async def disconnect(self) -> None:
        self._is_connected = False

    async def get_account(self):
        return {}

    async def get_positions(self):
        return []

    async def get_position(self, symbol: str):
        return None

    async def place_order(self, symbol, quantity, side, order_type=OrderType.MARKET, 
                         limit_price=None, stop_price=None, time_in_force=TimeInForce.DAY):
        return {}

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_order(self, order_id: str):
        return {}

    async def get_orders(self, status=None, limit=100):
        return []

    async def get_historical_candles(self, symbol, timeframe, limit=100, 
                                     start_time=None, end_time=None):
        return []

    async def get_quote(self, symbol: str):
        return {}

    async def get_account_history(self):
        return {}


def test_mock_broker_adapter_initialization():
    """Test that mock broker adapter can be instantiated"""
    broker = MockBrokerAdapter(
        broker_name="mock",
        api_key="test_key",
        api_secret="test_secret"
    )
    assert broker.broker_name == "mock"
    assert broker.is_connected == False


@pytest.mark.asyncio
async def test_mock_broker_connect_disconnect():
    """Test mock broker connect/disconnect"""
    broker = MockBrokerAdapter(
        broker_name="mock",
        api_key="test_key",
        api_secret="test_secret"
    )
    
    assert not broker.is_connected
    
    await broker.connect()
    assert broker.is_connected
    
    await broker.disconnect()
    assert not broker.is_connected
