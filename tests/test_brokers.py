"""
Unit tests for broker adapters.
"""

import pytest
import asyncio
from datetime import datetime

from app.brokers.broker_interface import (
    BrokerAdapter,
    Order,
    OrderDirection,
    OrderType,
    OrderStatus,
    Quote,
)
from app.brokers.mock_broker import (
    MockBrokerAdapter,
    MockBrokerScenarios,
)


class TestMockBroker:
    """Test suite for MockBrokerAdapter"""
    
    @pytest.mark.asyncio
    async def test_authentication(self):
        """Test broker authentication"""
        broker = MockBrokerScenarios.instant_fill()
        assert not broker.is_authenticated
        
        result = await broker.authenticate()
        assert result is True
        assert broker.is_authenticated
    
    @pytest.mark.asyncio
    async def test_get_quote(self):
        """Test getting market quotes"""
        broker = MockBrokerScenarios.instant_fill()
        await broker.authenticate()
        
        quote = await broker.get_quote('EUR_USD')
        assert quote.symbol == 'EUR_USD'
        assert quote.bid > 0
        # bid == ask when slippage is 0 (instant-fill scenario); that's valid.
        assert quote.ask >= quote.bid
        assert quote.bid_size > 0
        assert quote.ask_size > 0
    
    @pytest.mark.asyncio
    async def test_market_order_fill(self):
        """Test market order fills"""
        broker = MockBrokerScenarios.instant_fill()
        await broker.authenticate()
        
        order = Order(
            order_id=None,
            symbol='EUR_USD',
            direction=OrderDirection.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        )
        
        order_id = await broker.submit_order(order)
        assert order_id is not None
        
        # Wait for fill
        await asyncio.sleep(0.2)
        
        filled_order = await broker.get_order_status(order_id)
        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.filled_quantity == 1.0
        assert filled_order.average_fill_price > 0
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self):
        """Test order cancellation"""
        broker = MockBrokerScenarios.slow_fill()
        await broker.authenticate()
        
        order = Order(
            order_id=None,
            symbol='BTC_USD',
            direction=OrderDirection.SELL,
            order_type=OrderType.LIMIT,
            quantity=0.5,
            price=41000,
        )
        
        order_id = await broker.submit_order(order)
        
        # Cancel before fill
        success = await broker.cancel_order(order_id)
        assert success is True
        
        # Check status
        cancelled = await broker.get_order_status(order_id)
        assert cancelled.status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_positions_tracking(self):
        """Test position tracking after fills"""
        broker = MockBrokerScenarios.instant_fill()
        await broker.authenticate()
        
        # Submit BUY order
        order1 = Order(
            order_id=None,
            symbol='EUR_USD',
            direction=OrderDirection.BUY,
            order_type=OrderType.MARKET,
            quantity=2.0,
        )
        
        order_id1 = await broker.submit_order(order1)
        await asyncio.sleep(0.2)
        
        # Check position
        positions = await broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == 'EUR_USD'
        assert positions[0].quantity == 2.0
        assert positions[0].side == OrderDirection.BUY
        
        # Submit SELL order (closes position)
        order2 = Order(
            order_id=None,
            symbol='EUR_USD',
            direction=OrderDirection.SELL,
            order_type=OrderType.MARKET,
            quantity=2.0,
        )
        
        order_id2 = await broker.submit_order(order2)
        await asyncio.sleep(0.2)
        
        # Position closed
        positions = await broker.get_positions()
        assert len(positions) == 0
    
    @pytest.mark.asyncio
    async def test_slippage_simulation(self):
        """Test slippage in order fills"""
        broker = MockBrokerScenarios.with_slippage()
        await broker.authenticate()
        
        quote_before = await broker.get_quote('BTC_USD')
        
        order = Order(
            order_id=None,
            symbol='BTC_USD',
            direction=OrderDirection.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        
        order_id = await broker.submit_order(order)
        await asyncio.sleep(0.2)
        
        filled = await broker.get_order_status(order_id)
        
        # Fill price should be higher due to slippage
        assert filled.average_fill_price > quote_before.bid
    
    @pytest.mark.asyncio
    async def test_rejection_scenario(self):
        """Test order rejection"""
        broker = MockBrokerScenarios.with_rejections()
        await broker.authenticate()
        
        # Try multiple orders, some should be rejected
        rejected_count = 0
        for i in range(10):
            order = Order(
                order_id=None,
                symbol='EUR_USD',
                direction=OrderDirection.BUY,
                order_type=OrderType.MARKET,
                quantity=1.0,
            )
            
            try:
                await broker.submit_order(order)
            except Exception:
                rejected_count += 1
        
        # Should have some rejections
        assert rejected_count > 0
        assert rejected_count < 10


class TestBrokerInterface:
    """Test abstract broker interface"""
    
    def test_order_dataclass(self):
        """Test Order object creation"""
        order = Order(
            order_id='test_123',
            symbol='EUR_USD',
            direction=OrderDirection.BUY,
            order_type=OrderType.LIMIT,
            quantity=2.5,
            price=1.0850,
        )
        
        assert order.order_id == 'test_123'
        assert order.symbol == 'EUR_USD'
        assert order.direction == OrderDirection.BUY
        assert order.quantity == 2.5
        assert order.status == OrderStatus.PENDING
    
    def test_quote_dataclass(self):
        """Test Quote object creation"""
        now = datetime.utcnow()
        quote = Quote(
            symbol='BTC_USD',
            bid=42500,
            ask=42510,
            bid_size=1.5,
            ask_size=2.0,
            last_price=42505,
            timestamp=now,
        )
        
        assert quote.symbol == 'BTC_USD'
        assert quote.bid < quote.ask
        assert quote.last_price > quote.bid


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
