"""
BrokerManager - Central orchestrator for managing multiple broker adapters.
Handles adapter lifecycle, route trading requests, aggregate data.
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum

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


class BrokerRouter(str, Enum):
    """Enum for routing decisions."""
    ALPACA = "alpaca"
    OANDA = "oanda"
    PRIMARY = "primary"  # Use primary broker


class BrokerManager:
    """
    Central manager for multiple broker adapters.
    Coordinates connections, routes orders, aggregates data.
    """

    def __init__(self):
        """Initialize broker manager."""
        self.adapters: Dict[str, BrokerInterface] = {}
        self._primary_broker: Optional[str] = None
        self._is_initialized = False

    def register_adapter(self, broker_name: str, adapter: BrokerInterface) -> None:
        """
        Register a broker adapter.

        Args:
            broker_name: Name of the broker (e.g., 'alpaca', 'oanda')
            adapter: BrokerInterface instance
        """
        self.adapters[broker_name.lower()] = adapter
        if not self._primary_broker:
            self._primary_broker = broker_name.lower()
        logger.info(f"Registered adapter: {broker_name}")

    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect all registered adapters.

        Returns:
            Dict mapping broker names to connection success status
        """
        results = {}
        for broker_name, adapter in self.adapters.items():
            try:
                success = await adapter.connect()
                results[broker_name] = success
                status = "✅" if success else "❌"
                logger.info(f"{status} {broker_name} connected")
            except Exception as e:
                logger.error(f"Failed to connect {broker_name}: {str(e)}")
                results[broker_name] = False

        self._is_initialized = all(results.values())
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all adapters."""
        for broker_name, adapter in self.adapters.items():
            try:
                await adapter.disconnect()
                logger.info(f"Disconnected {broker_name}")
            except Exception as e:
                logger.error(f"Error disconnecting {broker_name}: {str(e)}")

    def _get_adapter(self, broker: Optional[str] = None) -> BrokerInterface:
        """
        Get broker adapter by name or primary.

        Args:
            broker: Broker name, or None for primary

        Returns:
            BrokerInterface instance

        Raises:
            ValueError: If broker not found or not connected
        """
        broker_name = (broker or self._primary_broker or "").lower()

        if not broker_name:
            raise ValueError("No primary broker set")

        if broker_name not in self.adapters:
            raise ValueError(f"Broker {broker_name} not registered")

        adapter = self.adapters[broker_name]
        if not adapter.is_connected:
            raise ValueError(f"Broker {broker_name} not connected")

        return adapter

    # Account Operations

    async def get_account(self, broker: Optional[str] = None) -> Account:
        """
        Get account from specified or primary broker.

        Args:
            broker: Broker name, or None for primary

        Returns:
            Account information
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_account()

    async def get_accounts_all(self) -> Dict[str, Account]:
        """
        Get accounts from all connected brokers.

        Returns:
            Dict mapping broker names to Account objects
        """
        results = {}
        for broker_name, adapter in self.adapters.items():
            try:
                if adapter.is_connected:
                    account = await adapter.get_account()
                    results[broker_name] = account
            except Exception as e:
                logger.warning(f"Failed to fetch account from {broker_name}: {str(e)}")

        return results

    # Position Operations

    async def get_positions(self, broker: Optional[str] = None) -> List[Position]:
        """
        Get positions from specified or primary broker.

        Args:
            broker: Broker name, or None for primary

        Returns:
            List of open positions
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_positions()

    async def get_position(
        self,
        symbol: str,
        broker: Optional[str] = None,
    ) -> Optional[Position]:
        """
        Get specific position.

        Args:
            symbol: Trading pair symbol
            broker: Broker name, or None for primary

        Returns:
            Position or None if not found
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_position(symbol)

    async def get_positions_all(self, symbol: Optional[str] = None) -> Dict[str, List[Position]]:
        """
        Get positions from all brokers.

        Args:
            symbol: Filter by symbol, or None for all

        Returns:
            Dict mapping broker names to position lists
        """
        results = {}
        for broker_name, adapter in self.adapters.items():
            try:
                if adapter.is_connected:
                    positions = await adapter.get_positions()
                    if symbol:
                        positions = [p for p in positions if p.symbol == symbol]
                    results[broker_name] = positions
            except Exception as e:
                logger.warning(
                    f"Failed to fetch positions from {broker_name}: {str(e)}"
                )

        return results

    # Order Operations

    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        broker: Optional[str] = None,
    ) -> Trade:
        """
        Place order on specified or primary broker.

        Args:
            symbol: Trading pair
            quantity: Order quantity
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT
            limit_price: Price for LIMIT orders
            stop_price: Price for STOP orders
            time_in_force: DAY, GTC, IOC, FOK
            broker: Broker name, or None for primary

        Returns:
            Trade object with order details
        """
        adapter = self._get_adapter(broker)
        return await adapter.place_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )

    async def cancel_order(self, order_id: str, broker: Optional[str] = None) -> bool:
        """
        Cancel order on specified or primary broker.

        Args:
            order_id: Order ID to cancel
            broker: Broker name, or None for primary

        Returns:
            True if successful
        """
        adapter = self._get_adapter(broker)
        return await adapter.cancel_order(order_id)

    async def get_order(self, order_id: str, broker: Optional[str] = None) -> Trade:
        """
        Get order details.

        Args:
            order_id: Order ID
            broker: Broker name, or None for primary

        Returns:
            Trade object with order details
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_order(order_id)

    async def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
        broker: Optional[str] = None,
    ) -> List[Trade]:
        """
        Get orders from specified or primary broker.

        Args:
            status: Filter by status
            limit: Max orders to return
            broker: Broker name, or None for primary

        Returns:
            List of Trade objects
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_orders(status=status, limit=limit)

    async def get_orders_all(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> Dict[str, List[Trade]]:
        """
        Get orders from all brokers.

        Args:
            status: Filter by status
            limit: Max per broker

        Returns:
            Dict mapping broker names to order lists
        """
        results = {}
        for broker_name, adapter in self.adapters.items():
            try:
                if adapter.is_connected:
                    orders = await adapter.get_orders(status=status, limit=limit)
                    results[broker_name] = orders
            except Exception as e:
                logger.warning(f"Failed to fetch orders from {broker_name}: {str(e)}")

        return results

    # Market Data Operations

    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        broker: Optional[str] = None,
    ) -> List[Candle]:
        """
        Get historical candles from specified or primary broker.

        Args:
            symbol: Trading pair
            timeframe: '1m', '5m', '1h', '1d', etc.
            limit: Max candles
            broker: Broker name, or None for primary

        Returns:
            List of Candle objects (oldest first)
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_historical_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )

    async def get_quote(self, symbol: str, broker: Optional[str] = None) -> Dict[str, Any]:
        """
        Get real-time quote from specified or primary broker.

        Args:
            symbol: Trading pair
            broker: Broker name, or None for primary

        Returns:
            Dict with bid, ask, last, volume, etc.
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_quote(symbol)

    async def get_quotes_all(self, symbol: str) -> Dict[str, Dict[str, Any]]:
        """
        Get quotes from all brokers (for comparison).

        Args:
            symbol: Trading pair

        Returns:
            Dict mapping broker names to quote dicts
        """
        results = {}
        for broker_name, adapter in self.adapters.items():
            try:
                if adapter.is_connected:
                    quote = await adapter.get_quote(symbol)
                    results[broker_name] = quote
            except Exception as e:
                logger.warning(f"Failed to fetch quote from {broker_name}: {str(e)}")

        return results

    async def get_account_history(self, broker: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account history from specified or primary broker.

        Args:
            broker: Broker name, or None for primary

        Returns:
            Dict with equity curve, returns, etc.
        """
        adapter = self._get_adapter(broker)
        return await adapter.get_account_history()

    async def get_account_histories_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Get account histories from all brokers.

        Returns:
            Dict mapping broker names to history dicts
        """
        results = {}
        for broker_name, adapter in self.adapters.items():
            try:
                if adapter.is_connected:
                    history = await adapter.get_account_history()
                    results[broker_name] = history
            except Exception as e:
                logger.warning(
                    f"Failed to fetch account history from {broker_name}: {str(e)}"
                )

        return results

    # Status & Management

    def get_status(self) -> Dict[str, Any]:
        """
        Get overall manager status.

        Returns:
            Dict with broker statuses, primary broker, etc.
        """
        return {
            "initialized": self._is_initialized,
            "primary_broker": self._primary_broker,
            "brokers": {
                name: {
                    "connected": adapter.is_connected,
                    "sandbox_mode": getattr(adapter, "sandbox", None),
                }
                for name, adapter in self.adapters.items()
            },
            "adapter_count": len(self.adapters),
            "connected_count": sum(
                1 for adapter in self.adapters.values() if adapter.is_connected
            ),
        }

    def set_primary_broker(self, broker_name: str) -> None:
        """
        Set primary broker for operations.

        Args:
            broker_name: Name of broker to set as primary
        """
        if broker_name.lower() not in self.adapters:
            raise ValueError(f"Broker {broker_name} not registered")

        self._primary_broker = broker_name.lower()
        logger.info(f"Primary broker set to {self._primary_broker}")

    def list_adapters(self) -> List[str]:
        """Get list of registered adapters."""
        return list(self.adapters.keys())
