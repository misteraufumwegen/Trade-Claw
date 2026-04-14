"""
Comprehensive unit tests for broker adapters.
Tests AlpacaAdapter, OandaAdapter, and BrokerManager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.adapters.alpaca import AlpacaAdapter
from app.adapters.oanda import OandaAdapter
from app.adapters.broker_manager import BrokerManager
from app.interfaces.broker import (
    Account,
    Position,
    Trade,
    Candle,
    OrderStatus,
    OrderType,
    OrderSide,
    TimeInForce,
)


# ==================== ALPACA ADAPTER TESTS ====================


class TestAlpacaAdapterConnection:
    """Test AlpacaAdapter connection lifecycle."""

    @pytest.mark.asyncio
    async def test_alpaca_init(self):
        """Test AlpacaAdapter initialization."""
        adapter = AlpacaAdapter(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
        )
        assert adapter.broker_name == "alpaca"
        assert adapter.api_key == "test_key"
        assert adapter.sandbox is True
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_alpaca_connect_success(self):
        """Test successful connection to Alpaca."""
        adapter = AlpacaAdapter("key", "secret", sandbox=True)

        with patch("app.adapters.alpaca.ccxt_async.alpaca") as mock_exchange:
            mock_instance = AsyncMock()
            mock_instance.load_markets = AsyncMock()
            mock_exchange.return_value = mock_instance

            result = await adapter.connect()
            assert result is True
            assert adapter.is_connected is True
            assert adapter.exchange is not None

    @pytest.mark.asyncio
    async def test_alpaca_disconnect(self):
        """Test disconnection from Alpaca."""
        adapter = AlpacaAdapter("key", "secret", sandbox=True)

        with patch("app.adapters.alpaca.ccxt_async.alpaca") as mock_exchange:
            mock_instance = AsyncMock()
            mock_instance.load_markets = AsyncMock()
            mock_instance.close = AsyncMock()
            mock_exchange.return_value = mock_instance

            await adapter.connect()
            await adapter.disconnect()
            assert adapter.is_connected is False


class TestAlpacaAdapterAccount:
    """Test AlpacaAdapter account operations."""

    @pytest.mark.asyncio
    async def test_get_account_success(self):
        """Test fetching account information."""
        adapter = AlpacaAdapter("key", "secret", sandbox=True)
        adapter._is_connected = True

        mock_balance = {
            "free": 10000.0,
            "total": 50000.0,
            "info": {"account_id": "acc123"},
        }

        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_balance = AsyncMock(return_value=mock_balance)

        account = await adapter.get_account()

        assert isinstance(account, Account)
        assert account.account_id == "acc123"
        assert account.cash == 10000.0
        assert account.portfolio_value == 50000.0

    @pytest.mark.asyncio
    async def test_get_account_not_connected(self):
        """Test get_account raises error when not connected."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            await adapter.get_account()


class TestAlpacaAdapterPositions:
    """Test AlpacaAdapter position operations."""

    @pytest.mark.asyncio
    async def test_get_positions_empty(self):
        """Test getting positions when none exist."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True
        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_balance = AsyncMock(
            return_value={"free": 1000, "total": 1000, "info": {}}
        )

        positions = await adapter.get_positions()
        assert isinstance(positions, list)
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_get_position_found(self):
        """Test getting a specific position."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        mock_positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                entry_price=150.0,
                current_price=155.0,
                unrealized_pnl=500.0,
                unrealized_pnl_pct=3.33,
                side=OrderSide.BUY,
            ),
        ]

        adapter.get_positions = AsyncMock(return_value=mock_positions)

        position = await adapter.get_position("AAPL")
        assert position is not None
        assert position.symbol == "AAPL"
        assert position.quantity == 100

    @pytest.mark.asyncio
    async def test_get_position_not_found(self):
        """Test getting non-existent position."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True
        adapter.get_positions = AsyncMock(return_value=[])

        position = await adapter.get_position("TSLA")
        assert position is None


class TestAlpacaAdapterOrders:
    """Test AlpacaAdapter order operations."""

    @pytest.mark.asyncio
    async def test_place_order_market(self):
        """Test placing a market order."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        mock_order = {
            "id": "order123",
            "amount": 100,
            "average": 150.0,
            "status": "closed",
            "timestamp": int(datetime.now().timestamp() * 1000),
            "cost": 15000,
        }

        adapter.exchange = AsyncMock()
        adapter.exchange.create_order = AsyncMock(return_value=mock_order)

        trade = await adapter.place_order(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )

        assert isinstance(trade, Trade)
        assert trade.trade_id == "order123"
        assert trade.symbol == "AAPL"
        assert trade.quantity == 100

    @pytest.mark.asyncio
    async def test_place_order_limit_validation(self):
        """Test limit order price validation."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        with pytest.raises(ValueError, match="limit_price required"):
            await adapter.place_order(
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                limit_price=None,
            )

    @pytest.mark.asyncio
    async def test_cancel_order_success(self):
        """Test successful order cancellation."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True
        adapter.exchange = AsyncMock()
        adapter.exchange.cancel_order = AsyncMock()

        result = await adapter.cancel_order("order123")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_order_success(self):
        """Test fetching order details."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        mock_order = {
            "id": "order123",
            "symbol": "AAPL",
            "amount": 100,
            "average": 150.0,
            "status": "closed",
            "type": "market",
            "side": "buy",
            "timestamp": int(datetime.now().timestamp() * 1000),
        }

        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_orders = AsyncMock(return_value=[mock_order])

        trade = await adapter.get_order("order123")
        assert isinstance(trade, Trade)
        assert trade.trade_id == "order123"

    @pytest.mark.asyncio
    async def test_get_orders_with_filter(self):
        """Test getting orders with status filter."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        mock_orders = [
            {
                "id": "order1",
                "symbol": "AAPL",
                "amount": 100,
                "average": 150.0,
                "status": "closed",
                "type": "market",
                "side": "buy",
                "timestamp": int(datetime.now().timestamp() * 1000),
            },
            {
                "id": "order2",
                "symbol": "TSLA",
                "amount": 50,
                "average": 0,
                "status": "open",
                "type": "limit",
                "side": "buy",
                "timestamp": int(datetime.now().timestamp() * 1000),
            },
        ]

        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_orders = AsyncMock(return_value=mock_orders)

        trades = await adapter.get_orders(limit=10)
        assert len(trades) == 2


class TestAlpacaAdapterMarketData:
    """Test AlpacaAdapter market data operations."""

    @pytest.mark.asyncio
    async def test_get_historical_candles(self):
        """Test fetching historical candle data."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        now = datetime.now()
        mock_ohlcv = [
            [int(now.timestamp() * 1000), 150.0, 155.0, 149.0, 152.0, 1000000],
            [
                int((now - timedelta(hours=1)).timestamp() * 1000),
                148.0,
                154.0,
                147.0,
                151.0,
                950000,
            ],
        ]

        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_ohlcv = AsyncMock(return_value=mock_ohlcv)

        candles = await adapter.get_historical_candles(
            symbol="AAPL",
            timeframe="1h",
            limit=100,
        )

        assert len(candles) == 2
        assert all(isinstance(c, Candle) for c in candles)
        assert candles[0].close == 152.0

    @pytest.mark.asyncio
    async def test_get_quote(self):
        """Test fetching real-time quote."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        mock_ticker = {
            "bid": 149.50,
            "ask": 150.50,
            "last": 150.0,
            "quoteVolume": 1000000,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "bidVolume": 50000,
            "askVolume": 60000,
        }

        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_ticker = AsyncMock(return_value=mock_ticker)

        quote = await adapter.get_quote("AAPL")

        assert quote["symbol"] == "AAPL"
        assert quote["bid"] == 149.50
        assert quote["ask"] == 150.50
        assert quote["last"] == 150.0

    @pytest.mark.asyncio
    async def test_get_account_history(self):
        """Test fetching account history."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = True

        mock_balance = {
            "total": 50000.0,
            "free": 10000.0,
            "used": 40000.0,
        }

        adapter.exchange = AsyncMock()
        adapter.exchange.fetch_balance = AsyncMock(return_value=mock_balance)

        history = await adapter.get_account_history()

        assert history["current_equity"] == 50000.0
        assert history["available_cash"] == 10000.0


# ==================== OANDA ADAPTER TESTS ====================


class TestOandaAdapterConnection:
    """Test OandaAdapter connection lifecycle."""

    @pytest.mark.asyncio
    async def test_oanda_init(self):
        """Test OandaAdapter initialization."""
        adapter = OandaAdapter(
            api_key="test_token",
            api_secret="ignored",
            account_id="acc123",
            demo=True,
        )
        assert adapter.broker_name == "oanda"
        assert adapter.api_key == "test_token"
        assert adapter.account_id == "acc123"
        assert adapter.demo is True

    @pytest.mark.asyncio
    async def test_oanda_connect_success(self):
        """Test successful OANDA connection."""
        adapter = OandaAdapter("token", "secret", "acc123", demo=True)

        with patch("app.adapters.oanda.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json = lambda: {"account": {}}
            mock_client.return_value = mock_instance

            result = await adapter.connect()
            assert result is True
            assert adapter.is_connected is True

    @pytest.mark.asyncio
    async def test_oanda_disconnect(self):
        """Test OANDA disconnection."""
        adapter = OandaAdapter("token", "secret", "acc123")

        with patch("app.adapters.oanda.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json = lambda: {"account": {}}
            mock_instance.aclose = AsyncMock()
            mock_client.return_value = mock_instance

            await adapter.connect()
            await adapter.disconnect()
            assert adapter.is_connected is False


class TestOandaAdapterAccount:
    """Test OandaAdapter account operations."""

    @pytest.mark.asyncio
    async def test_oanda_get_account(self):
        """Test fetching OANDA account."""
        adapter = OandaAdapter("token", "secret", "acc123")
        adapter._is_connected = True

        mock_response = {
            "account": {
                "currency": "USD",
                "unrealizedPL": 1000.0,
                "balance": 50000.0,
                "marginAvailable": 25000.0,
            }
        }

        adapter.http_client = AsyncMock()
        adapter.http_client.get = AsyncMock()
        adapter.http_client.get.return_value.status_code = 200
        adapter.http_client.get.return_value.json = lambda: mock_response

        account = await adapter.get_account()

        assert isinstance(account, Account)
        assert account.account_id == "acc123"
        assert account.currency == "USD"
        assert account.portfolio_value == 50000.0


class TestOandaAdapterOrders:
    """Test OandaAdapter order operations."""

    @pytest.mark.asyncio
    async def test_oanda_place_order_market(self):
        """Test placing OANDA market order."""
        adapter = OandaAdapter("token", "secret", "acc123")
        adapter._is_connected = True

        mock_response = {
            "orderFillTransaction": {
                "id": "order456",
                "price": 1.1050,
                "type": "MARKET",
                "financing": 0.0,
            }
        }

        adapter.http_client = AsyncMock()
        adapter.http_client.post = AsyncMock()
        adapter.http_client.post.return_value.status_code = 200
        adapter.http_client.post.return_value.json = lambda: mock_response

        trade = await adapter.place_order(
            symbol="EUR_USD",
            quantity=100000,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )

        assert isinstance(trade, Trade)
        assert trade.trade_id == "order456"

    @pytest.mark.asyncio
    async def test_oanda_cancel_order(self):
        """Test cancelling OANDA order."""
        adapter = OandaAdapter("token", "secret", "acc123")
        adapter._is_connected = True

        adapter.http_client = AsyncMock()
        adapter.http_client.put = AsyncMock()
        adapter.http_client.put.return_value.status_code = 200

        result = await adapter.cancel_order("order456")
        assert result is True

    @pytest.mark.asyncio
    async def test_oanda_get_quote(self):
        """Test fetching OANDA quote."""
        adapter = OandaAdapter("token", "secret", "acc123")
        adapter._is_connected = True

        mock_response = {
            "candles": [
                {
                    "bid": {"c": "1.1050"},
                    "ask": {"c": "1.1055"},
                    "volume": 100000,
                    "time": "2026-04-14T10:00:00Z",
                }
            ]
        }

        adapter.http_client = AsyncMock()
        adapter.http_client.get = AsyncMock()
        adapter.http_client.get.return_value.status_code = 200
        adapter.http_client.get.return_value.json = lambda: mock_response

        quote = await adapter.get_quote("EUR_USD")

        assert quote["symbol"] == "EUR_USD"
        assert float(quote["bid"]) == 1.1050
        assert float(quote["ask"]) == 1.1055


# ==================== BROKER MANAGER TESTS ====================


class TestBrokerManagerBasic:
    """Test BrokerManager basic functionality."""

    def test_broker_manager_init(self):
        """Test BrokerManager initialization."""
        manager = BrokerManager()
        assert manager.adapters == {}
        assert manager._primary_broker is None

    def test_register_adapter(self):
        """Test registering an adapter."""
        manager = BrokerManager()
        adapter = AlpacaAdapter("key", "secret")

        manager.register_adapter("alpaca", adapter)

        assert "alpaca" in manager.adapters
        assert manager._primary_broker == "alpaca"

    def test_set_primary_broker(self):
        """Test setting primary broker."""
        manager = BrokerManager()
        adapter1 = AlpacaAdapter("key", "secret")
        adapter2 = OandaAdapter("token", "secret", "acc123")

        manager.register_adapter("alpaca", adapter1)
        manager.register_adapter("oanda", adapter2)

        manager.set_primary_broker("oanda")
        assert manager._primary_broker == "oanda"

    def test_list_adapters(self):
        """Test listing registered adapters."""
        manager = BrokerManager()
        manager.register_adapter("alpaca", AlpacaAdapter("key", "secret"))
        manager.register_adapter("oanda", OandaAdapter("token", "secret", "acc123"))

        adapters = manager.list_adapters()
        assert "alpaca" in adapters
        assert "oanda" in adapters

    def test_get_status(self):
        """Test getting manager status."""
        manager = BrokerManager()
        adapter = AlpacaAdapter("key", "secret")
        manager.register_adapter("alpaca", adapter)

        status = manager.get_status()

        assert status["primary_broker"] == "alpaca"
        assert "alpaca" in status["brokers"]
        assert status["adapter_count"] == 1


class TestBrokerManagerConnections:
    """Test BrokerManager connection operations."""

    @pytest.mark.asyncio
    async def test_connect_all(self):
        """Test connecting all adapters."""
        manager = BrokerManager()

        adapter1 = AlpacaAdapter("key", "secret")
        adapter1.connect = AsyncMock(return_value=True)

        adapter2 = OandaAdapter("token", "secret", "acc123")
        adapter2.connect = AsyncMock(return_value=True)

        manager.register_adapter("alpaca", adapter1)
        manager.register_adapter("oanda", adapter2)

        results = await manager.connect_all()

        assert results["alpaca"] is True
        assert results["oanda"] is True
        assert manager._is_initialized is True

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Test disconnecting all adapters."""
        manager = BrokerManager()

        adapter1 = AlpacaAdapter("key", "secret")
        adapter1.disconnect = AsyncMock()
        adapter1._is_connected = True

        adapter2 = OandaAdapter("token", "secret", "acc123")
        adapter2.disconnect = AsyncMock()
        adapter2._is_connected = True

        manager.register_adapter("alpaca", adapter1)
        manager.register_adapter("oanda", adapter2)

        await manager.disconnect_all()

        adapter1.disconnect.assert_called_once()
        adapter2.disconnect.assert_called_once()


class TestBrokerManagerAccounts:
    """Test BrokerManager account operations."""

    @pytest.mark.asyncio
    async def test_get_account_primary(self):
        """Test getting account from primary broker."""
        manager = BrokerManager()
        adapter = AlpacaAdapter("key", "secret")

        mock_account = Account(
            account_id="acc123",
            currency="USD",
            cash=10000,
            portfolio_value=50000,
            buying_power=10000,
            day_trading_buying_power=10000,
            last_updated=datetime.now(),
        )

        adapter.get_account = AsyncMock(return_value=mock_account)
        adapter._is_connected = True

        manager.register_adapter("alpaca", adapter)

        account = await manager.get_account()
        assert account.account_id == "acc123"

    @pytest.mark.asyncio
    async def test_get_accounts_all(self):
        """Test getting accounts from all brokers."""
        manager = BrokerManager()

        account1 = Account(
            account_id="acc1",
            currency="USD",
            cash=10000,
            portfolio_value=50000,
            buying_power=10000,
            day_trading_buying_power=10000,
            last_updated=datetime.now(),
        )

        account2 = Account(
            account_id="acc2",
            currency="USD",
            cash=5000,
            portfolio_value=25000,
            buying_power=5000,
            day_trading_buying_power=5000,
            last_updated=datetime.now(),
        )

        adapter1 = AlpacaAdapter("key", "secret")
        adapter1.get_account = AsyncMock(return_value=account1)
        adapter1._is_connected = True

        adapter2 = OandaAdapter("token", "secret", "acc2")
        adapter2.get_account = AsyncMock(return_value=account2)
        adapter2._is_connected = True

        manager.register_adapter("alpaca", adapter1)
        manager.register_adapter("oanda", adapter2)

        accounts = await manager.get_accounts_all()

        assert len(accounts) == 2
        assert "alpaca" in accounts
        assert "oanda" in accounts


class TestBrokerManagerOrders:
    """Test BrokerManager order operations."""

    @pytest.mark.asyncio
    async def test_place_order_primary(self):
        """Test placing order on primary broker."""
        manager = BrokerManager()

        mock_trade = Trade(
            trade_id="trade1",
            symbol="AAPL",
            quantity=100,
            filled_price=150.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            status=OrderStatus.FILLED,
            created_at=datetime.now(),
            filled_at=datetime.now(),
            commission=10.0,
        )

        adapter = AlpacaAdapter("key", "secret")
        adapter.place_order = AsyncMock(return_value=mock_trade)
        adapter._is_connected = True

        manager.register_adapter("alpaca", adapter)

        trade = await manager.place_order(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
        )

        assert trade.trade_id == "trade1"
        assert trade.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_orders_all(self):
        """Test getting orders from all brokers."""
        manager = BrokerManager()

        trades1 = [
            Trade(
                trade_id="t1",
                symbol="AAPL",
                quantity=100,
                filled_price=150.0,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                status=OrderStatus.FILLED,
                created_at=datetime.now(),
                filled_at=datetime.now(),
                commission=10.0,
            )
        ]

        trades2 = [
            Trade(
                trade_id="t2",
                symbol="EUR_USD",
                quantity=100000,
                filled_price=1.1050,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                status=OrderStatus.FILLED,
                created_at=datetime.now(),
                filled_at=datetime.now(),
                commission=5.0,
            )
        ]

        adapter1 = AlpacaAdapter("key", "secret")
        adapter1.get_orders = AsyncMock(return_value=trades1)
        adapter1._is_connected = True

        adapter2 = OandaAdapter("token", "secret", "acc2")
        adapter2.get_orders = AsyncMock(return_value=trades2)
        adapter2._is_connected = True

        manager.register_adapter("alpaca", adapter1)
        manager.register_adapter("oanda", adapter2)

        all_orders = await manager.get_orders_all()

        assert len(all_orders) == 2
        assert len(all_orders["alpaca"]) == 1
        assert len(all_orders["oanda"]) == 1


# ==================== ERROR HANDLING TESTS ====================


class TestErrorHandling:
    """Test error handling across adapters."""

    @pytest.mark.asyncio
    async def test_get_adapter_not_found(self):
        """Test error when adapter not registered."""
        manager = BrokerManager()

        with pytest.raises(ValueError, match="not registered"):
            manager._get_adapter("invalid")

    @pytest.mark.asyncio
    async def test_get_adapter_not_connected(self):
        """Test error when adapter not connected."""
        manager = BrokerManager()
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = False

        manager.register_adapter("alpaca", adapter)

        with pytest.raises(ValueError, match="not connected"):
            manager._get_adapter("alpaca")

    @pytest.mark.asyncio
    async def test_place_order_not_connected(self):
        """Test place_order error when not connected."""
        adapter = AlpacaAdapter("key", "secret")
        adapter._is_connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            await adapter.place_order(
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
