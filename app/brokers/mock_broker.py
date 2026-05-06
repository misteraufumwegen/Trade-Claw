"""
Mock Broker Adapter
For testing without real API calls.
Simulates market conditions: fills, slippage, rejections, partial fills.
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime

from .broker_interface import (
    BrokerAdapter,
    BrokerError,
    InsufficientLiquidityError,
    InvalidOrderError,
    Order,
    OrderDirection,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)

logger = logging.getLogger("MockBroker")


class MockBrokerAdapter(BrokerAdapter):
    """
    Simulated broker for testing.

    Features:
    - Configurable fill behavior (instant, delayed, rejection)
    - Slippage simulation
    - Partial fills
    - Order rejection on insufficient liquidity
    - Live price streaming
    """

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, secret_key=None, **kwargs)

        # Mock state
        self.orders: dict[str, Order] = {}
        self.positions: dict[str, Position] = {}
        self.account_balance = kwargs.get("initial_balance", 100000.0)
        self.equity = self.account_balance
        self.margin_available = self.account_balance

        # Mock price data
        self.prices: dict[str, float] = {
            "EUR_USD": 1.0850,
            "GBP_USD": 1.2750,
            "BTC_USD": 42500.0,
            "ETH_USD": 2300.0,
            "SOL_USD": 145.0,
        }

        # Configuration for test scenarios
        self.fill_delay_ms = kwargs.get("fill_delay_ms", 100)  # How fast orders fill
        self.slippage_pips = kwargs.get("slippage_pips", 0.0)  # Slippage simulation
        self.rejection_rate = kwargs.get("rejection_rate", 0.0)  # Probability of rejection
        self.partial_fill_rate = kwargs.get("partial_fill_rate", 0.0)  # Probability of partial fill

        # Streaming state
        self._streaming = False
        self._stream_task = None

        self.is_authenticated = False

    async def authenticate(self) -> bool:
        """Mock authentication always succeeds."""
        # Do NOT log any portion of the API key (security review M5).
        logger.info("Mock broker authenticating")
        await asyncio.sleep(0.1)  # Simulate network delay
        self.is_authenticated = True
        return True

    async def get_quote(self, symbol: str) -> Quote:
        """Get mock quote with optional slippage"""
        if symbol not in self.prices:
            raise InvalidOrderError(f"Symbol {symbol} not supported in mock broker")

        price = self.prices[symbol]
        slippage = self.slippage_pips * 0.0001  # Convert pips to price

        bid = price - slippage
        ask = price + slippage

        return Quote(
            symbol=symbol,
            bid=bid,
            ask=ask,
            bid_size=1000000,  # Mock large size
            ask_size=1000000,
            last_price=price,
            timestamp=datetime.utcnow(),
        )

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        """Get multiple quotes"""
        return {symbol: await self.get_quote(symbol) for symbol in symbols}

    async def submit_order(self, order: Order) -> str:
        """
        Submit order with simulated fill behavior.

        Simulation scenarios:
        1. Random rejection (based on rejection_rate)
        2. Instant fill (market order)
        3. Partial fill then rejection
        4. Instant fill with slippage
        """

        # Random rejection
        if random.random() < self.rejection_rate:
            logger.warning("Mock broker rejecting order (random failure)")
            raise InsufficientLiquidityError("Simulated liquidity failure")

        # Generate order ID
        order_id = f"mock_{uuid.uuid4().hex[:12]}"
        order.order_id = order_id
        order.created_at = datetime.utcnow()

        # Store order
        self.orders[order_id] = order
        logger.info(
            f"Order submitted: {order_id} {order.direction.value} {order.quantity} {order.symbol}"
        )

        # Schedule fill
        if order.order_type == OrderType.MARKET:
            # Market orders fill immediately (with small delay)
            asyncio.create_task(self._simulate_market_fill(order_id))
        elif order.order_type == OrderType.LIMIT:
            # Limit orders stay pending
            asyncio.create_task(self._simulate_limit_fill(order_id))

        return order_id

    async def _simulate_market_fill(self, order_id: str):
        """Simulate market order fill"""
        order = self.orders[order_id]

        # Delay fill
        await asyncio.sleep(self.fill_delay_ms / 1000.0)

        # Check if cancelled
        if order.status == OrderStatus.CANCELLED:
            return

        # Partial fill?
        if random.random() < self.partial_fill_rate:
            filled_qty = order.quantity * 0.5  # Fill 50%
            order.filled_quantity = filled_qty
            order.status = OrderStatus.PARTIALLY_FILLED
            order.average_fill_price = self.prices[order.symbol]
            logger.info(f"Order {order_id} partially filled: {filled_qty}")

            # Remaining size is cancelled — but the 50 % that was filled must
            # stay on the order, so downstream P&L/accounting is correct (M3).
            await asyncio.sleep(0.5)
            order.status = OrderStatus.CANCELLED  # state: partial + cancelled
            logger.info(
                "Order %s: remaining size cancelled after partial fill (filled=%s)",
                order_id,
                filled_qty,
            )
            return

        # Full fill
        quote = await self.get_quote(order.symbol)

        if order.direction == OrderDirection.BUY:
            fill_price = quote.ask  # Buy at ask
        else:
            fill_price = quote.bid  # Sell at bid

        order.filled_quantity = order.quantity
        order.average_fill_price = fill_price
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()

        # Update position
        await self._update_position_from_order(order)

        logger.info(f"Order {order_id} filled at {fill_price}")

        # Schedule settlement so the trade eventually resolves to WIN or LOSS.
        # Without this the FastAPI poller would never see the position close
        # and trade_outcomes rows would stay open forever.
        asyncio.create_task(self._simulate_settlement(order_id))

    async def _simulate_settlement(self, order_id: str):
        """Simulate the trade running to SL or TP.

        Picks the outcome with a probability biased toward the loss side
        (P(TP) ≈ 1 / (1 + R_multiple)) — a fair Bernoulli model for a
        symmetric random walk with the user's R/R. The exit price recorded
        on ``order.metadata['closed_price']`` is what the FastAPI poller
        reads to resolve the TradeOutcome row.

        Settlement delay is short on purpose so manual smoke tests don't
        wait minutes; tune via ``settlement_delay_seconds`` in adapter
        kwargs when you want slower playback.
        """
        order = self.orders.get(order_id)
        if order is None:
            return
        meta = order.metadata or {}
        # Pull stop_loss / take_profit from the OrderAPIRequest metadata that
        # the API adapter forwards into ``order.metadata``.
        tp = meta.get("take_profit")
        sl = meta.get("stop_loss")
        if tp is None or sl is None or order.average_fill_price is None:
            logger.debug("Order %s missing TP/SL metadata; skipping settlement", order_id)
            return

        delay = self.config.get("settlement_delay_seconds", random.uniform(2.0, 6.0))
        await asyncio.sleep(delay)

        if order.status not in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            return  # cancelled or otherwise mutated meanwhile

        entry = float(order.average_fill_price)
        tp_f = float(tp)
        sl_f = float(sl)
        # Expected R/R from this position
        risk = abs(entry - sl_f) or 1e-9
        reward = abs(tp_f - entry)
        rr = reward / risk
        # Probability the random walk reaches TP before SL with this R/R.
        p_tp = 1.0 / (1.0 + rr) if rr > 0 else 0.5

        if random.random() < p_tp:
            closed_price = tp_f
            label = "WIN"
        else:
            closed_price = sl_f
            label = "LOSS"

        order.metadata = {
            **(order.metadata or {}),
            "closed_price": closed_price,
            "settlement_label": label,
            "closed_at": datetime.utcnow().isoformat(),
        }
        # Close the position record too so the broker's get_positions reflects
        # reality at the next poll.
        if order.symbol in self.positions:
            self.positions.pop(order.symbol, None)
        logger.info(
            "Mock settlement: %s %s @ %s (%s)", order_id, label, closed_price, order.symbol
        )

    async def _simulate_limit_fill(self, order_id: str):
        """Simulate limit order (may never fill in mock)"""
        order = self.orders[order_id]

        # For testing: randomly fill after 5-30 seconds
        await asyncio.sleep(random.uniform(5, 30))

        if order.status != OrderStatus.PENDING:
            return  # Already cancelled or filled

        # Check if price would hit limit
        current_price = self.prices[order.symbol]

        if (order.direction == OrderDirection.BUY and current_price <= order.price) or (
            order.direction == OrderDirection.SELL and current_price >= order.price
        ):
            order.filled_quantity = order.quantity
            order.average_fill_price = order.price
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()

            await self._update_position_from_order(order)
            logger.info(f"Limit order {order_id} filled at {order.price}")

    async def _update_position_from_order(self, order: Order):
        """Update position when order fills"""
        symbol = order.symbol
        existing = self.positions.get(symbol)

        quantity_change = (
            order.filled_quantity
            if order.direction == OrderDirection.BUY
            else -order.filled_quantity
        )

        if not existing:
            # New position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity_change,
                average_price=order.average_fill_price,
                current_price=order.average_fill_price,
                unrealized_pnl=0.0,
                unrealized_pnl_percent=0.0,
                side=order.direction,
                last_updated=datetime.utcnow(),
            )
        else:
            # Update existing position
            old_qty = existing.quantity
            old_avg = existing.average_price
            new_qty = old_qty + quantity_change

            if new_qty == 0:
                # Position closed
                del self.positions[symbol]
                logger.info(f"Position {symbol} closed")
            else:
                # Recalculate average price
                existing.quantity = new_qty
                existing.average_price = (
                    old_qty * old_avg + quantity_change * order.average_fill_price
                ) / new_qty
                existing.current_price = order.average_fill_price
                existing.last_updated = datetime.utcnow()

    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        if order_id not in self.orders:
            raise BrokerError(f"Order {order_id} not found")

        order = self.orders[order_id]

        # Update position PnL if position exists
        if order.status == OrderStatus.FILLED and order.symbol in self.positions:
            pos = self.positions[order.symbol]
            pnl_diff = (pos.current_price - pos.average_price) * pos.quantity
            pos.unrealized_pnl = pnl_diff
            pos.unrealized_pnl_percent = (
                (pnl_diff / (pos.average_price * pos.quantity)) * 100
                if pos.average_price != 0
                else 0
            )

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id not in self.orders:
            return False

        order = self.orders[order_id]

        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            return False  # Already closed

        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        logger.info(f"Order {order_id} cancelled")

        return True

    async def get_positions(self) -> list[Position]:
        """Get all positions"""
        return list(self.positions.values())

    async def get_position(self, symbol: str) -> Position | None:
        """Get single position"""
        return self.positions.get(symbol)

    async def get_account_balance(self) -> dict[str, float]:
        """Get account balance"""
        return {
            "balance": self.account_balance,
            "equity": self.equity,
            "margin_available": self.margin_available,
            "margin_used": self.account_balance - self.margin_available,
        }

    async def stream_prices(self, symbols: list[str], callback) -> None:
        """Stream live prices (simulated)"""
        self._streaming = True
        logger.info(f"Starting price stream for {symbols}")

        try:
            while self._streaming:
                for symbol in symbols:
                    # Simulate price movement (random walk)
                    if symbol in self.prices:
                        change = random.gauss(0, 0.001)  # Small random change
                        self.prices[symbol] *= 1 + change

                        quote = await self.get_quote(symbol)
                        await callback(symbol, quote)

                await asyncio.sleep(0.5)  # Send tick every 500ms

        except asyncio.CancelledError:
            self._streaming = False
            logger.info("Price stream stopped")

    async def disconnect(self) -> None:
        """Disconnect from mock broker"""
        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
        logger.info("Mock broker disconnected")


# Test scenarios (for pytest)
class MockBrokerScenarios:
    """Pre-configured mock brokers for different test scenarios"""

    @staticmethod
    def instant_fill() -> MockBrokerAdapter:
        """Orders fill instantly"""
        return MockBrokerAdapter(
            api_key="test",
            initial_balance=100000,
            fill_delay_ms=10,
        )

    @staticmethod
    def slow_fill() -> MockBrokerAdapter:
        """Orders fill slowly (1-2 seconds)"""
        return MockBrokerAdapter(
            api_key="test",
            initial_balance=100000,
            fill_delay_ms=1000,
        )

    @staticmethod
    def with_slippage() -> MockBrokerAdapter:
        """Orders fill with slippage (5 pips)"""
        return MockBrokerAdapter(
            api_key="test",
            initial_balance=100000,
            slippage_pips=5,
        )

    @staticmethod
    def with_rejections() -> MockBrokerAdapter:
        """Orders rejected 20% of the time"""
        return MockBrokerAdapter(
            api_key="test",
            initial_balance=100000,
            rejection_rate=0.2,
        )

    @staticmethod
    def with_partial_fills() -> MockBrokerAdapter:
        """Orders partially filled 30% of the time"""
        return MockBrokerAdapter(
            api_key="test",
            initial_balance=100000,
            partial_fill_rate=0.3,
        )

    @staticmethod
    def chaos() -> MockBrokerAdapter:
        """All problems at once"""
        return MockBrokerAdapter(
            api_key="test",
            initial_balance=100000,
            fill_delay_ms=500,
            slippage_pips=5,
            rejection_rate=0.1,
            partial_fill_rate=0.2,
        )
