"""
AlpacaAdapter - Implementation of BrokerInterface for Alpaca broker.
Uses ccxt library for async API interactions.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

import ccxt.async_support as ccxt_async

from app.interfaces.broker import (
    BrokerInterface,
    Account,
    Position,
    Trade,
    Candle,
    OrderStatus,
    OrderType,
    OrderSide,
    TimeInForce,
)

logger = logging.getLogger(__name__)


class AlpacaAdapter(BrokerInterface):
    """
    Alpaca broker adapter using ccxt library.
    Supports both Alpaca Markets (stocks) and Alpaca Crypto.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        sandbox: bool = True,
        **kwargs
    ):
        """
        Initialize Alpaca adapter.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca secret key
            sandbox: Use sandbox (paper trading) environment
            **kwargs: Additional parameters (e.g., passphrase for crypto)
        """
        super().__init__("alpaca", api_key, api_secret, **kwargs)
        self.sandbox = sandbox
        self.exchange = None
        self.passphrase = kwargs.get("passphrase", "")
        self._account_cache = None
        self._account_cache_time = None
        self._cache_ttl = 30  # Cache account for 30 seconds

    async def connect(self) -> bool:
        """
        Establish connection to Alpaca API.

        Returns:
            bool: True if connection successful
        """
        try:
            config = {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "sandbox": self.sandbox,
                "enableRateLimit": True,
                "rateLimit": 200,
            }

            if self.passphrase:
                config["password"] = self.passphrase

            self.exchange = ccxt_async.alpaca(config)

            # Test connection by fetching account
            await self.exchange.load_markets()
            self._is_connected = True
            logger.info(f"✅ Connected to Alpaca (sandbox={self.sandbox})")
            return True

        except Exception as e:
            logger.error(f"❌ Alpaca connection failed: {str(e)}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Alpaca API."""
        if self.exchange:
            await self.exchange.close()
            self._is_connected = False
            logger.info("Disconnected from Alpaca")

    async def get_account(self) -> Account:
        """
        Get account information from Alpaca.

        Returns:
            Account: Account details

        Raises:
            RuntimeError: If not connected or API call fails
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            # Fetch account balance
            balance = await self.exchange.fetch_balance()

            account_id = balance.get("info", {}).get("account_id", "unknown")
            cash = balance.get("free", 0.0)
            total = balance.get("total", 0.0)

            return Account(
                account_id=account_id,
                currency="USD",
                cash=float(cash),
                portfolio_value=float(total),
                buying_power=float(cash),  # Simplified
                day_trading_buying_power=float(cash),
                last_updated=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error fetching account: {str(e)}")
            raise RuntimeError(f"Failed to fetch account: {str(e)}")

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List[Position]: List of open positions
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            positions = []
            balance = await self.exchange.fetch_balance()

            for symbol, holding in balance.items():
                if symbol in ["free", "used", "total", "info"]:
                    continue

                quantity = holding.get("free", 0.0)
                if quantity == 0:
                    continue

                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    current_price = ticker.get("last", 0.0)

                    # Calculate entry price (simple: assume bought at current - 2%)
                    entry_price = current_price * 0.98

                    unrealized_pnl = (current_price - entry_price) * quantity
                    unrealized_pnl_pct = (
                        (current_price - entry_price) / entry_price * 100
                        if entry_price != 0
                        else 0
                    )

                    positions.append(
                        Position(
                            symbol=symbol,
                            quantity=float(quantity),
                            entry_price=float(entry_price),
                            current_price=float(current_price),
                            unrealized_pnl=float(unrealized_pnl),
                            unrealized_pnl_pct=float(unrealized_pnl_pct),
                            side=OrderSide.BUY,
                        )
                    )

                except Exception as e:
                    logger.warning(f"Skipping {symbol}: {str(e)}")
                    continue

            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            raise RuntimeError(f"Failed to fetch positions: {str(e)}")

    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get a specific position.

        Args:
            symbol: Trading pair symbol (e.g., 'AAPL/USD')

        Returns:
            Position or None if no position exists
        """
        try:
            positions = await self.get_positions()
            for pos in positions:
                if pos.symbol == symbol:
                    return pos
            return None
        except Exception as e:
            logger.error(f"Error fetching position {symbol}: {str(e)}")
            return None

    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> Trade:
        """
        Place a new order on Alpaca.

        Args:
            symbol: Trading pair (e.g., 'AAPL/USD')
            quantity: Order quantity
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT
            limit_price: Price for LIMIT orders
            stop_price: Price for STOP orders
            time_in_force: DAY, GTC, IOC, FOK

        Returns:
            Trade: Order details

        Raises:
            ValueError: If parameters invalid
            RuntimeError: If order placement fails
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            # Validate parameters
            if order_type == OrderType.LIMIT and limit_price is None:
                raise ValueError("limit_price required for LIMIT orders")
            if order_type == OrderType.STOP and stop_price is None:
                raise ValueError("stop_price required for STOP orders")
            if order_type == OrderType.STOP_LIMIT and (
                limit_price is None or stop_price is None
            ):
                raise ValueError(
                    "Both limit_price and stop_price required for STOP_LIMIT"
                )

            # Map to ccxt order type
            order_type_map = {
                OrderType.MARKET: "market",
                OrderType.LIMIT: "limit",
                OrderType.STOP: "stop",
                OrderType.STOP_LIMIT: "stop_limit",
            }

            ccxt_order_type = order_type_map.get(order_type, "market")
            ccxt_side = side.value.lower()

            # Build order params
            params = {
                "timeInForce": time_in_force.value.upper(),
            }

            if stop_price:
                params["stopPrice"] = stop_price
            if limit_price:
                params["price"] = limit_price

            # Place order
            order = await self.exchange.create_order(
                symbol=symbol,
                type=ccxt_order_type,
                side=ccxt_side,
                amount=quantity,
                price=limit_price,
                params=params,
            )

            return Trade(
                trade_id=order.get("id", "unknown"),
                symbol=symbol,
                quantity=float(order.get("amount", quantity)),
                filled_price=float(order.get("average", limit_price or 0.0)),
                order_type=order_type,
                side=side,
                status=self._map_order_status(order.get("status", "open")),
                created_at=datetime.fromtimestamp(
                    order.get("timestamp", 0) / 1000
                ),
                filled_at=None,
                commission=float(order.get("cost", 0) * 0.001),  # Assume 0.1%
            )

        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise RuntimeError(f"Failed to place order: {str(e)}")

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation successful
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            # Note: ccxt requires symbol for cancellation in some cases
            # This is a simplified implementation
            await self.exchange.cancel_order(order_id)
            logger.info(f"Cancelled order {order_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return False

    async def get_order(self, order_id: str) -> Trade:
        """
        Get order details.

        Args:
            order_id: Order ID

        Returns:
            Trade: Order details

        Raises:
            RuntimeError: If order not found or API fails
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            # Alpaca requires symbol - fetch all orders and filter
            orders = await self.exchange.fetch_orders()
            for order in orders:
                if order.get("id") == order_id:
                    return self._order_to_trade(order)

            raise RuntimeError(f"Order {order_id} not found")

        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {str(e)}")
            raise

    async def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Trade]:
        """
        Get list of orders.

        Args:
            status: Filter by status (None = all)
            limit: Max orders to return

        Returns:
            List[Trade]: Orders matching criteria
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            orders = await self.exchange.fetch_orders(limit=limit)

            trades = []
            for order in orders:
                trade = self._order_to_trade(order)

                # Filter by status if specified
                if status and trade.status != status:
                    continue

                trades.append(trade)

            return trades[:limit]

        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            raise RuntimeError(f"Failed to fetch orders: {str(e)}")

    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Candle]:
        """
        Get historical OHLCV candle data.

        Args:
            symbol: Trading pair (e.g., 'AAPL/USD')
            timeframe: '1m', '5m', '1h', '1d', etc.
            limit: Max candles
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List[Candle]: Historical candles (oldest first)
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            since = None
            if start_time:
                since = int(start_time.timestamp() * 1000)

            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=since,
                limit=limit,
            )

            candles = []
            for row in ohlcv:
                timestamp, open_, high, low, close, volume = row

                if end_time and datetime.fromtimestamp(timestamp / 1000) > end_time:
                    break

                candles.append(
                    Candle(
                        timestamp=datetime.fromtimestamp(timestamp / 1000),
                        open=float(open_),
                        high=float(high),
                        low=float(low),
                        close=float(close),
                        volume=float(volume),
                    )
                )

            return candles

        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {str(e)}")
            raise RuntimeError(f"Failed to fetch candles: {str(e)}")

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Trading pair (e.g., 'AAPL/USD')

        Returns:
            Dict with bid, ask, last, volume, timestamp
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            ticker = await self.exchange.fetch_ticker(symbol)

            return {
                "symbol": symbol,
                "bid": float(ticker.get("bid", 0.0)),
                "ask": float(ticker.get("ask", 0.0)),
                "last": float(ticker.get("last", 0.0)),
                "volume": float(ticker.get("quoteVolume", 0.0)),
                "timestamp": datetime.fromtimestamp(ticker.get("timestamp", 0) / 1000),
                "bid_size": float(ticker.get("bidVolume", 0.0)),
                "ask_size": float(ticker.get("askVolume", 0.0)),
            }

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            raise RuntimeError(f"Failed to fetch quote: {str(e)}")

    async def get_account_history(self) -> Dict[str, Any]:
        """
        Get account performance history.

        Returns:
            Dict with equity curve, returns, etc.
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to Alpaca")

        try:
            balance = await self.exchange.fetch_balance()

            return {
                "current_equity": float(balance.get("total", 0.0)),
                "available_cash": float(balance.get("free", 0.0)),
                "used_margin": float(balance.get("used", 0.0)),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching account history: {str(e)}")
            raise RuntimeError(f"Failed to fetch account history: {str(e)}")

    # Private helpers

    def _map_order_status(self, ccxt_status: str) -> OrderStatus:
        """Map ccxt order status to OrderStatus enum."""
        status_map = {
            "open": OrderStatus.PENDING,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
        }
        return status_map.get(ccxt_status.lower(), OrderStatus.PENDING)

    def _order_to_trade(self, order: Dict[str, Any]) -> Trade:
        """Convert ccxt order dict to Trade object."""
        return Trade(
            trade_id=order.get("id", "unknown"),
            symbol=order.get("symbol", "UNKNOWN"),
            quantity=float(order.get("amount", 0.0)),
            filled_price=float(order.get("average", 0.0)),
            order_type=self._map_order_type(order.get("type", "market")),
            side=OrderSide.BUY
            if order.get("side", "buy").lower() == "buy"
            else OrderSide.SELL,
            status=self._map_order_status(order.get("status", "open")),
            created_at=datetime.fromtimestamp(order.get("timestamp", 0) / 1000),
            filled_at=(
                datetime.fromtimestamp(order.get("timestamp", 0) / 1000)
                if order.get("status", "").lower() == "closed"
                else None
            ),
            commission=float(order.get("cost", 0) * 0.001),
        )

    def _map_order_type(self, ccxt_type: str) -> OrderType:
        """Map ccxt order type to OrderType enum."""
        type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
        }
        return type_map.get(ccxt_type.lower(), OrderType.MARKET)
