"""
Broker Interface (Abstract)
Multi-broker architecture — any broker can be plugged in.

Pattern:
- Alpaca, OANDA, Hyperliquid implement this interface
- Order API Adapter normalizes orders across brokers
- Risk Engine integrates at normalization layer
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio


class OrderDirection(Enum):
    """Direction of an order — BUY (long) or SELL (short / close long)."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order execution style.

    - MARKET:     Execute immediately at the best available price.
    - LIMIT:      Execute only at ``price`` or better.
    - STOP:       Becomes a MARKET order once ``stop_price`` is touched.
    - STOP_LIMIT: Becomes a LIMIT order at ``price`` once ``stop_price`` is touched.
    """

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    """Lifecycle states for an order.

    ``PENDING`` → ``ACCEPTED`` → (``PARTIALLY_FILLED`` →) ``FILLED`` |
    ``CANCELLED`` | ``REJECTED`` | ``EXPIRED``.
    """

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class Quote:
    """Market quote response"""
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    last_price: float
    timestamp: datetime


@dataclass
class Order:
    """Order representation (normalized across all brokers)"""
    order_id: str
    symbol: str
    direction: OrderDirection  # BUY / SELL
    order_type: OrderType
    quantity: float
    price: Optional[float] = None  # For LIMIT, STOP orders
    stop_price: Optional[float] = None  # For STOP orders
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    broker_order_id: Optional[str] = None  # broker's internal ID
    metadata: Dict[str, Any] = None  # broker-specific data

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Position:
    """Open position representation"""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    side: OrderDirection  # LONG (BUY) or SHORT (SELL)
    last_updated: datetime


@dataclass
class TradeConfirmation:
    """Trade execution confirmation"""
    order_id: str
    broker_order_id: str
    symbol: str
    direction: OrderDirection
    quantity: float
    average_fill_price: float
    total_value: float  # quantity * average_fill_price
    filled_at: datetime
    fees: float = 0.0


class BrokerAdapter(ABC):
    """
    Abstract base class for all broker implementations.
    Each broker (Alpaca, OANDA, Hyperliquid, etc.) extends this.
    """

    def __init__(self, api_key: str, secret_key: Optional[str] = None, **kwargs):
        """
        Initialize broker adapter with credentials.
        
        Args:
            api_key: API Key / Public Key
            secret_key: API Secret / Private Key (if applicable)
            **kwargs: Broker-specific config (base_url, account_id, etc.)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.config = kwargs
        self.is_authenticated = False

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Verify API credentials with broker.
        Returns True if valid, raises exception if invalid.
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """
        Get current market quote for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "EUR_USD" for OANDA, "BTC/USD" for Hyperliquid)
        
        Returns:
            Quote object with bid/ask/last price
        """
        pass

    @abstractmethod
    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Quote]:
        """
        Get multiple quotes in one call (more efficient).
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            Dict mapping symbol -> Quote
        """
        pass

    @abstractmethod
    async def submit_order(self, order: Order) -> str:
        """
        Submit order to broker.
        
        Args:
            order: Order object with entry details
        
        Returns:
            order_id (broker's order ID)
        
        Raises:
            OrderRejectedError: If broker rejects order
            InsufficientLiquidityError: If liquidity unavailable
            InvalidOrderError: If order parameters invalid
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """
        Get current status of an order.
        
        Args:
            order_id: Broker order ID
        
        Returns:
            Updated Order object
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Broker order ID
        
        Returns:
            True if cancelled successfully, False if already closed
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of Position objects
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get single position by symbol.
        
        Returns:
            Position if exists, None if no position
        """
        pass

    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance and equity.
        
        Returns:
            Dict with keys: 'balance', 'equity', 'margin_available', 'margin_used'
        """
        pass

    @abstractmethod
    async def stream_prices(self, symbols: List[str], callback) -> None:
        """
        Subscribe to live price updates via WebSocket.
        
        Args:
            symbols: List of symbols to stream
            callback: Async function(symbol, price_update) to call on each tick
        
        Note: Should run indefinitely until disconnected
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Clean up connections (WebSockets, etc.)
        """
        pass


class BrokerError(Exception):
    """Base exception for broker errors"""
    pass


class OrderRejectedError(BrokerError):
    """Order was rejected by broker"""
    pass


class InsufficientLiquidityError(BrokerError):
    """Not enough liquidity to fill order"""
    pass


class InvalidOrderError(BrokerError):
    """Order parameters invalid"""
    pass


class AuthenticationError(BrokerError):
    """API credentials invalid"""
    pass
