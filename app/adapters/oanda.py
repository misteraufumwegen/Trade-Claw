"""
OandaAdapter - Implementation of BrokerInterface for OANDA broker.
Uses v20 library for async API interactions (via httpx wrapper).
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

import httpx
from v20 import Context, account, instrument, order, trade, pricing

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


class OandaAdapter(BrokerInterface):
    """
    OANDA broker adapter using v20 library.
    Supports forex, commodities, and indices trading.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        account_id: str,
        demo: bool = True,
        **kwargs
    ):
        """
        Initialize OANDA adapter.

        Args:
            api_key: OANDA API token
            api_secret: Not used by OANDA (only token)
            account_id: OANDA account ID
            demo: Use demo environment (vs production)
            **kwargs: Additional parameters
        """
        super().__init__("oanda", api_key, api_secret, **kwargs)
        self.account_id = account_id
        self.demo = demo
        self.base_url = (
            "https://stream-fxpractice.oanda.com"
            if demo
            else "https://stream-live.oanda.com"
        )
        self.rest_url = (
            "https://api-fxpractice.oanda.com" if demo else "https://api-fxlive.oanda.com"
        )
        self.ctx = None
        self.http_client = None
        self._account_cache = None

    async def connect(self) -> bool:
        """
        Establish connection to OANDA API.

        Returns:
            bool: True if connection successful
        """
        try:
            # Initialize v20 context
            self.ctx = Context(
                hostname=self.rest_url.replace("https://", ""),
                token=self.api_key,
                application="TradingBot/0.1.0",
            )

            # Test connection by fetching account
            http_client = httpx.AsyncClient(
                base_url=self.rest_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept-Datetime-Format": "Unix",
                },
            )

            response = await http_client.get(f"/v3/accounts/{self.account_id}")
            if response.status_code == 200:
                self.http_client = http_client
                self._is_connected = True
                logger.info(f"✅ Connected to OANDA (demo={self.demo})")
                return True
            else:
                logger.error(f"OANDA connection failed: {response.text}")
                await http_client.aclose()
                return False

        except Exception as e:
            logger.error(f"❌ OANDA connection failed: {str(e)}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from OANDA API."""
        if self.http_client:
            await self.http_client.aclose()
        self._is_connected = False
        logger.info("Disconnected from OANDA")

    async def get_account(self) -> Account:
        """
        Get account information from OANDA.

        Returns:
            Account: Account details

        Raises:
            RuntimeError: If not connected or API call fails
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.get(f"/v3/accounts/{self.account_id}")
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            account_data = data.get("account", {})

            return Account(
                account_id=self.account_id,
                currency=account_data.get("currency", "USD"),
                cash=float(account_data.get("unrealizedPL", 0.0)),
                portfolio_value=float(account_data.get("balance", 0.0)),
                buying_power=float(account_data.get("marginAvailable", 0.0)),
                day_trading_buying_power=float(account_data.get("marginAvailable", 0.0)),
                last_updated=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error fetching account: {str(e)}")
            raise RuntimeError(f"Failed to fetch account: {str(e)}")

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions from OANDA.

        Returns:
            List[Position]: List of open positions
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.get(
                f"/v3/accounts/{self.account_id}/openPositions"
            )
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            positions = []
            for position in data.get("positions", []):
                instrument = position.get("instrument", "UNKNOWN")
                long_units = float(position.get("long", {}).get("units", 0))
                short_units = abs(float(position.get("short", {}).get("units", 0)))

                # Get current price
                quote = await self.get_quote(instrument)
                current_price = quote.get("last", 0.0)

                # Calculate entry price (simplified)
                entry_price = current_price * 0.995

                if long_units > 0:
                    quantity = long_units
                    side = OrderSide.BUY
                    unrealized_pnl = (current_price - entry_price) * quantity
                elif short_units > 0:
                    quantity = short_units
                    side = OrderSide.SELL
                    unrealized_pnl = (entry_price - current_price) * quantity
                else:
                    continue

                unrealized_pnl_pct = (
                    (unrealized_pnl / (entry_price * quantity) * 100)
                    if (entry_price * quantity) != 0
                    else 0
                )

                positions.append(
                    Position(
                        symbol=instrument,
                        quantity=quantity,
                        entry_price=entry_price,
                        current_price=current_price,
                        unrealized_pnl=unrealized_pnl,
                        unrealized_pnl_pct=unrealized_pnl_pct,
                        side=side,
                    )
                )

            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            raise RuntimeError(f"Failed to fetch positions: {str(e)}")

    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get a specific position.

        Args:
            symbol: Trading pair (e.g., 'EUR_USD')

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
        Place a new order on OANDA.

        Args:
            symbol: Trading pair (e.g., 'EUR_USD')
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
            raise RuntimeError("Not connected to OANDA")

        try:
            # Validate parameters
            if order_type == OrderType.LIMIT and limit_price is None:
                raise ValueError("limit_price required for LIMIT orders")
            if order_type == OrderType.STOP and stop_price is None:
                raise ValueError("stop_price required for STOP orders")

            # Map enums to OANDA format
            units = int(quantity) if side == OrderSide.BUY else int(-quantity)
            tif_map = {
                TimeInForce.DAY: "DAY",
                TimeInForce.GTC: "GTC",
                TimeInForce.IOC: "IOC",
                TimeInForce.FOK: "FOK",
            }

            order_data = {
                "order": {
                    "instrument": symbol,
                    "units": units,
                    "timeInForce": tif_map.get(time_in_force, "DAY"),
                    "priceBound": limit_price,
                }
            }

            # Add order type specific params
            if order_type == OrderType.MARKET:
                order_data["order"]["type"] = "MARKET"
            elif order_type == OrderType.LIMIT:
                order_data["order"]["type"] = "LIMIT"
                order_data["order"]["priceBound"] = limit_price
            elif order_type == OrderType.STOP:
                order_data["order"]["type"] = "STOP"
                order_data["order"]["priceBound"] = stop_price
            elif order_type == OrderType.STOP_LIMIT:
                order_data["order"]["type"] = "STOP"
                order_data["order"]["triggerDistance"] = abs(
                    stop_price - limit_price if stop_price and limit_price else 0
                )

            response = await self.http_client.post(
                f"/v3/accounts/{self.account_id}/orders",
                json=order_data,
            )

            data = response.json()

            if response.status_code not in [200, 201]:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            order_info = data.get("orderFillTransaction", {})

            return Trade(
                trade_id=order_info.get("id", "unknown"),
                symbol=symbol,
                quantity=quantity,
                filled_price=float(order_info.get("price", limit_price or 0.0)),
                order_type=order_type,
                side=side,
                status=self._map_oanda_order_status(
                    order_info.get("type", "MARKET")
                ),
                created_at=datetime.utcnow(),
                filled_at=datetime.utcnow(),
                commission=float(order_info.get("financing", 0.0)),
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
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.put(
                f"/v3/accounts/{self.account_id}/orders/{order_id}/cancel"
            )

            if response.status_code == 200:
                logger.info(f"Cancelled order {order_id}")
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}")
                return False

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
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.get(
                f"/v3/accounts/{self.account_id}/orders/{order_id}"
            )
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"Order {order_id} not found")

            order_info = data.get("order", {})

            return Trade(
                trade_id=order_info.get("id", "unknown"),
                symbol=order_info.get("instrument", "UNKNOWN"),
                quantity=abs(float(order_info.get("units", 0))),
                filled_price=float(order_info.get("priceBound", 0.0)),
                order_type=self._map_oanda_order_type(order_info.get("type", "MARKET")),
                side=OrderSide.BUY if float(order_info.get("units", 0)) > 0 else OrderSide.SELL,
                status=self._map_oanda_order_status(order_info.get("state", "PENDING")),
                created_at=datetime.utcnow(),
                filled_at=None,
                commission=0.0,
            )

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
            status: Filter by status
            limit: Max orders to return

        Returns:
            List[Trade]: Orders matching criteria
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.get(
                f"/v3/accounts/{self.account_id}/orders",
                params={"maxRecordsPerRequest": min(limit, 100)},
            )
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            trades = []
            for order_info in data.get("orders", [])[:limit]:
                trade = Trade(
                    trade_id=order_info.get("id", "unknown"),
                    symbol=order_info.get("instrument", "UNKNOWN"),
                    quantity=abs(float(order_info.get("units", 0))),
                    filled_price=float(order_info.get("priceBound", 0.0)),
                    order_type=self._map_oanda_order_type(order_info.get("type", "MARKET")),
                    side=OrderSide.BUY if float(order_info.get("units", 0)) > 0 else OrderSide.SELL,
                    status=self._map_oanda_order_status(order_info.get("state", "PENDING")),
                    created_at=datetime.utcnow(),
                    filled_at=None,
                    commission=0.0,
                )

                if status and trade.status != status:
                    continue

                trades.append(trade)

            return trades

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
            symbol: Trading pair (e.g., 'EUR_USD')
            timeframe: 'M1', 'M5', 'H1', 'D', etc.
            limit: Max candles
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List[Candle]: Historical candles (oldest first)
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to OANDA")

        try:
            # Map standard timeframes to OANDA format
            timeframe_map = {
                "1m": "M1",
                "5m": "M5",
                "15m": "M15",
                "30m": "M30",
                "1h": "H1",
                "4h": "H4",
                "1d": "D",
            }

            oanda_tf = timeframe_map.get(timeframe, "H1")

            params = {
                "granularity": oanda_tf,
                "count": min(limit, 5000),
            }

            if start_time:
                params["from"] = int(start_time.timestamp())
            if end_time:
                params["to"] = int(end_time.timestamp())

            response = await self.http_client.get(
                f"/v3/instruments/{symbol}/candles",
                params=params,
            )
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            candles = []
            for candle_data in data.get("candles", []):
                bid = candle_data.get("bid", {})
                candles.append(
                    Candle(
                        timestamp=datetime.fromisoformat(
                            candle_data.get("time", "").replace("Z", "+00:00")
                        ),
                        open=float(bid.get("o", 0)),
                        high=float(bid.get("h", 0)),
                        low=float(bid.get("l", 0)),
                        close=float(bid.get("c", 0)),
                        volume=float(candle_data.get("volume", 0)),
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
            symbol: Trading pair (e.g., 'EUR_USD')

        Returns:
            Dict with bid, ask, last, volume, timestamp
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.get(
                f"/v3/instruments/{symbol}/candles",
                params={"granularity": "M1", "count": 1},
            )
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            candle = data.get("candles", [{}])[0]
            bid = candle.get("bid", {})
            ask = candle.get("ask", {})

            return {
                "symbol": symbol,
                "bid": float(bid.get("c", 0.0)),
                "ask": float(ask.get("c", 0.0)),
                "last": float((float(bid.get("c", 0)) + float(ask.get("c", 0))) / 2),
                "volume": float(candle.get("volume", 0.0)),
                "timestamp": datetime.fromisoformat(
                    candle.get("time", "").replace("Z", "+00:00")
                ),
            }

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            raise RuntimeError(f"Failed to fetch quote: {str(e)}")

    async def get_account_history(self) -> Dict[str, Any]:
        """
        Get account performance history.

        Returns:
            Dict with balance, equity, returns
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to OANDA")

        try:
            response = await self.http_client.get(f"/v3/accounts/{self.account_id}")
            data = response.json()

            if response.status_code != 200:
                raise RuntimeError(f"API error: {data.get('errorMessage', 'Unknown')}")

            account_data = data.get("account", {})

            return {
                "current_equity": float(account_data.get("balance", 0.0)),
                "available_cash": float(account_data.get("marginAvailable", 0.0)),
                "unrealized_pnl": float(account_data.get("unrealizedPL", 0.0)),
                "realized_pnl": float(account_data.get("realizedPL", 0.0)),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching account history: {str(e)}")
            raise RuntimeError(f"Failed to fetch account history: {str(e)}")

    # Private helpers

    def _map_oanda_order_status(self, state: str) -> OrderStatus:
        """Map OANDA order state to OrderStatus enum."""
        status_map = {
            "PENDING": OrderStatus.PENDING,
            "FILLED": OrderStatus.FILLED,
            "TRIGGERED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
        }
        return status_map.get(state, OrderStatus.PENDING)

    def _map_oanda_order_type(self, order_type: str) -> OrderType:
        """Map OANDA order type to OrderType enum."""
        type_map = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP": OrderType.STOP,
            "STOP_LIMIT": OrderType.STOP_LIMIT,
        }
        return type_map.get(order_type, OrderType.MARKET)
