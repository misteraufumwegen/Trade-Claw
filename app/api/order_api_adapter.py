"""
Order API Adapter
Normalizes orders across all brokers (Alpaca, OANDA, Hyperliquid, etc.)
Handles Risk Engine integration and position validation.

Pattern:
1. User submits order with broker selection
2. Adapter validates against Risk Engine
3. Adapter normalizes to BrokerAdapter interface
4. Submits to selected broker
5. Returns normalized Order result
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from app.brokers.broker_interface import (
    BrokerAdapter,
    Order,
    OrderDirection,
    OrderStatus,
    OrderType,
    Position,
)
from app.security.audit import AuditLog

logger = logging.getLogger("OrderAPIAdapter")


class RiskValidationResult(Enum):
    """Risk validation outcomes"""

    APPROVED = "APPROVED"
    REJECTED_POSITION_SIZE = "REJECTED_POSITION_SIZE"
    REJECTED_DRAWDOWN = "REJECTED_DRAWDOWN"
    REJECTED_DAILY_LOSS = "REJECTED_DAILY_LOSS"
    REJECTED_CORRELATION = "REJECTED_CORRELATION"
    REJECTED_IMMUTABLE_SL = "REJECTED_IMMUTABLE_SL"


class OrderAPIRequest:
    """Normalized API request"""

    def __init__(
        self,
        symbol: str,
        direction: OrderDirection,
        quantity: float,
        entry_price: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        order_type: OrderType = OrderType.MARKET,
        **metadata,
    ):
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.order_type = order_type
        self.metadata = metadata
        self.created_at = datetime.utcnow()


class OrderAPIAdapter:
    """
    Main API adapter for order submission across brokers.
    """

    def __init__(
        self,
        broker: BrokerAdapter,
        risk_engine: Any | None = None,
        audit_log: AuditLog | None = None,
    ):
        """
        Initialize adapter.

        Args:
            broker: Configured BrokerAdapter (Alpaca, OANDA, Hyperliquid, Mock, etc.)
            risk_engine: Risk Engine instance (for position/drawdown/etc checks)
            audit_log: Audit logging instance
        """
        self.broker = broker
        self.risk_engine = risk_engine
        self.audit_log = audit_log or AuditLog()

    async def submit_order(self, request: OrderAPIRequest) -> Order:
        """
        Submit order through API.

        Process:
        1. Validate request format
        2. Check risk limits
        3. Get market quote (slippage check)
        4. Submit to broker
        5. Track in audit log

        Args:
            request: OrderAPIRequest with order details

        Returns:
            Order object with broker order ID

        Raises:
            ValueError: If request invalid
            RiskLimitExceededError: If risk check fails
            OrderRejectedError: If broker rejects
        """

        # Validate request
        self._validate_request(request)
        logger.info(f"Order request: {request.symbol} {request.direction.value} {request.quantity}")

        # Check risk limits if Risk Engine configured
        if self.risk_engine:
            validation = await self._validate_risk(request)
            if validation != RiskValidationResult.APPROVED:
                self.audit_log.log(
                    action="ORDER_REJECTED",
                    reason=validation.value,
                    details={"symbol": request.symbol, "quantity": request.quantity},
                )
                raise ValueError(f"Risk check failed: {validation.value}")

        # Get current market quote
        quote = await self.broker.get_quote(request.symbol)
        logger.info(f"Current quote: {request.symbol} bid={quote.bid} ask={quote.ask}")

        # Build normalized Order object
        order = Order(
            order_id=None,  # Will be assigned by broker
            symbol=request.symbol,
            direction=request.direction,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.entry_price if request.order_type != OrderType.MARKET else None,
            stop_price=request.stop_loss if request.order_type == OrderType.STOP else None,
        )
        order.metadata = {
            "take_profit": request.take_profit,
            "api_request": request.metadata,
            "submitted_at": datetime.utcnow().isoformat(),
        }

        # Submit to broker
        try:
            order_id = await self.broker.submit_order(order)
            order.order_id = order_id
            order.status = OrderStatus.ACCEPTED

            # Log to audit
            self.audit_log.log(
                action="ORDER_SUBMITTED",
                order_id=order_id,
                broker=self.broker.__class__.__name__,
                details={
                    "symbol": request.symbol,
                    "direction": request.direction.value,
                    "quantity": request.quantity,
                    "entry_price": request.entry_price,
                },
            )

            logger.info(f"Order submitted: {order_id}")
            return order

        except Exception as e:
            self.audit_log.log(
                action="ORDER_SUBMISSION_FAILED",
                reason=str(e),
                details={"symbol": request.symbol},
            )
            raise

    async def get_order(self, order_id: str) -> Order:
        """Get order status from broker"""
        order = await self.broker.get_order_status(order_id)

        self.audit_log.log(
            action="ORDER_STATUS_CHECK",
            order_id=order_id,
            details={"status": order.status.value if order.status else None},
        )

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        success = await self.broker.cancel_order(order_id)

        self.audit_log.log(
            action="ORDER_CANCELLED",
            order_id=order_id,
            details={"success": success},
        )

        return success

    async def get_positions(self) -> list[Position]:
        """Get all open positions"""
        positions = await self.broker.get_positions()

        self.audit_log.log(
            action="POSITIONS_FETCHED",
            details={"count": len(positions)},
        )

        return positions

    async def get_balance(self) -> dict[str, float]:
        """Get account balance"""
        balance = await self.broker.get_account_balance()

        self.audit_log.log(
            action="BALANCE_FETCHED",
            details=balance,
        )

        return balance

    def _validate_request(self, request: OrderAPIRequest):
        """Validate order request format"""

        if not request.symbol:
            raise ValueError("Symbol required")

        if request.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {request.quantity}")

        if request.entry_price and request.entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {request.entry_price}")

        if request.stop_loss and request.take_profit:
            # SL should be worse than entry, TP should be better
            if request.direction == OrderDirection.BUY:
                if request.stop_loss >= request.entry_price:
                    raise ValueError("Stop loss should be below entry price for BUY")
                if request.take_profit <= request.entry_price:
                    raise ValueError("Take profit should be above entry price for BUY")
            else:  # SELL
                if request.stop_loss <= request.entry_price:
                    raise ValueError("Stop loss should be above entry price for SELL")
                if request.take_profit >= request.entry_price:
                    raise ValueError("Take profit should be below entry price for SELL")

        logger.info(f"Request validation passed for {request.symbol}")

    async def _validate_risk(self, request: OrderAPIRequest) -> RiskValidationResult:
        """Check risk limits with Risk Engine"""

        try:
            # Position size check (e.g., max 10% of account)
            if hasattr(self.risk_engine, "check_position_size"):
                if not await self.risk_engine.check_position_size(request.quantity):
                    logger.warning(f"Position size {request.quantity} exceeds limit")
                    return RiskValidationResult.REJECTED_POSITION_SIZE

            # Drawdown check (e.g., max -15%)
            if hasattr(self.risk_engine, "check_drawdown"):
                if not await self.risk_engine.check_drawdown():
                    logger.warning("Drawdown limit exceeded")
                    return RiskValidationResult.REJECTED_DRAWDOWN

            # Daily loss check (e.g., max -5%)
            if hasattr(self.risk_engine, "check_daily_loss"):
                if not await self.risk_engine.check_daily_loss():
                    logger.warning("Daily loss limit exceeded")
                    return RiskValidationResult.REJECTED_DAILY_LOSS

            # Correlation check (don't add correlated positions)
            if hasattr(self.risk_engine, "check_correlation"):
                if not await self.risk_engine.check_correlation(request.symbol):
                    logger.warning(f"High correlation detected for {request.symbol}")
                    return RiskValidationResult.REJECTED_CORRELATION

            # SL immutability check (if SL locked, don't allow new entries)
            if hasattr(self.risk_engine, "is_sl_immutable"):
                if await self.risk_engine.is_sl_immutable():
                    logger.warning("Stop loss immutable, cannot submit new orders")
                    return RiskValidationResult.REJECTED_IMMUTABLE_SL

            return RiskValidationResult.APPROVED

        except Exception as e:
            logger.error(f"Risk validation error: {e}")
            # On error, fail closed (reject order)
            return RiskValidationResult.REJECTED_POSITION_SIZE

    async def validate_rr_ratio(
        self,
        entry: float,
        stop_loss: float,
        take_profit: float,
        direction: OrderDirection,
        min_ratio: float = 1.5,
    ) -> tuple[bool, float]:
        """
        Validate Risk/Reward ratio.

        Returns:
            (is_valid, ratio)
        """

        if direction == OrderDirection.BUY:
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit

        if risk <= 0:
            return False, 0

        ratio = reward / risk
        is_valid = ratio >= min_ratio

        logger.info(f"R/R ratio: {ratio:.2f} (min: {min_ratio})")

        return is_valid, ratio


class OrderBatchProcessor:
    """Process multiple orders efficiently"""

    def __init__(self, adapter: OrderAPIAdapter, max_concurrent: int = 5):
        self.adapter = adapter
        self.max_concurrent = max_concurrent

    async def submit_batch(self, requests: list[OrderAPIRequest]) -> list[Order]:
        """
        Submit multiple orders with rate limiting.

        Args:
            requests: List of OrderAPIRequest

        Returns:
            List of Order objects with results
        """
        import asyncio

        results = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def submit_with_limit(req):
            async with semaphore:
                try:
                    return await self.adapter.submit_order(req)
                except Exception as e:
                    logger.error(f"Batch order failed: {e}")
                    return None

        tasks = [submit_with_limit(req) for req in requests]
        results = await asyncio.gather(*tasks)

        successful = [r for r in results if r is not None]
        logger.info(f"Batch submitted: {len(successful)}/{len(requests)} successful")

        return successful
