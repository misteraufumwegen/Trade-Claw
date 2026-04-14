"""
Abstract BrokerInterface - defines contract for all broker adapters.
All adapters (Alpaca, OANDA, etc.) must implement these methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good-til-cancelled
    IOC = "ioc"  # Immediate-or-cancel
    FOK = "fok"  # Fill-or-kill


@dataclass
class Account:
    """Broker account information."""
    account_id: str
    currency: str
    cash: float
    portfolio_value: float
    buying_power: float
    day_trading_buying_power: float
    last_updated: datetime


@dataclass
class Position:
    """Open position in an instrument."""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    side: OrderSide


@dataclass
class Trade:
    """Executed trade/order."""
    trade_id: str
    symbol: str
    quantity: float
    filled_price: float
    order_type: OrderType
    side: OrderSide
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime]
    commission: float


@dataclass
class Candle:
    """OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class BrokerInterface(ABC):
    """
    Abstract base class for broker adapters.
    Defines the contract that all broker implementations must follow.
    """

    def __init__(self, broker_name: str, api_key: str, api_secret: str, **kwargs):
        """
        Initialize broker adapter.

        Args:
            broker_name: Name of the broker (e.g., 'alpaca', 'oanda')
            api_key: API key for broker
            api_secret: API secret for broker
            **kwargs: Additional broker-specific parameters
        """
        self.broker_name = broker_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.kwargs = kwargs
        self._is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to broker API.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker API."""
        pass

    @abstractmethod
    async def get_account(self) -> Account:
        """
        Get account information.

        Returns:
            Account: Account details
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List[Position]: List of open positions
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get a specific position.

        Args:
            symbol: Trading pair symbol (e.g., 'AAPL', 'EUR/USD')

        Returns:
            Position or None if no position exists
        """
        pass

    @abstractmethod
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
        Place a new order.

        Args:
            symbol: Trading pair symbol
            quantity: Order quantity
            side: BUY or SELL
            order_type: Type of order (MARKET, LIMIT, STOP, STOP_LIMIT)
            limit_price: Limit price (required for LIMIT and STOP_LIMIT)
            stop_price: Stop price (required for STOP and STOP_LIMIT)
            time_in_force: Time in force (DAY, GTC, IOC, FOK)

        Returns:
            Trade: Order details

        Raises:
            ValueError: If order parameters are invalid
            RuntimeError: If order placement fails
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation successful
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Trade:
        """
        Get order details.

        Args:
            order_id: Order ID

        Returns:
            Trade: Order details
        """
        pass

    @abstractmethod
    async def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Trade]:
        """
        Get list of orders.

        Args:
            status: Filter by order status
            limit: Maximum number of orders to return

        Returns:
            List[Trade]: List of orders
        """
        pass

    @abstractmethod
    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,  # '1m', '5m', '1h', '1d', etc.
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Candle]:
        """
        Get historical candle data.

        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            limit: Maximum candles to return
            start_time: Start time for historical data
            end_time: End time for historical data

        Returns:
            List[Candle]: Historical candles (oldest first)
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict with bid, ask, last, volume, timestamp, etc.
        """
        pass

    @abstractmethod
    async def get_account_history(self) -> Dict[str, Any]:
        """
        Get account performance history.

        Returns:
            Dict with account equity curve, returns, etc.
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._is_connected
