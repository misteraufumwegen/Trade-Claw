"""Custom exceptions for Trade-Claw."""


class TradeClawException(Exception):
    """Base exception for all Trade-Claw errors."""
    pass


class OrderValidationError(TradeClawException):
    """Raised when order fails validation checks."""
    pass


class RiskValidationError(TradeClawException):
    """Raised when order fails risk engine validation."""
    pass


class DrawdownHaltError(TradeClawException):
    """Raised when drawdown limit is breached and trading is halted."""
    pass


class BrokerConnectionError(TradeClawException):
    """Raised when broker API connection fails."""
    pass


class BrokerAuthenticationError(BrokerConnectionError):
    """Raised when broker authentication fails."""
    pass


class InsufficientLiquidityError(TradeClawException):
    """Raised when broker cannot fill order due to lack of liquidity."""
    pass


class CredentialError(TradeClawException):
    """Raised when broker credentials are invalid or missing."""
    pass


class SessionNotFoundError(TradeClawException):
    """Raised when broker session cannot be found."""
    pass


class OrderNotFoundError(TradeClawException):
    """Raised when order cannot be found."""
    pass


class PositionNotFoundError(TradeClawException):
    """Raised when position cannot be found."""
    pass


class DatabaseError(TradeClawException):
    """Raised when database operation fails."""
    pass


class InvalidOrderError(TradeClawException):
    """Raised when order parameters are invalid."""
    pass


class OrderCancellationError(TradeClawException):
    """Raised when order cannot be cancelled."""
    pass


class OrderRejectedError(TradeClawException):
    """Raised when broker rejects an order."""
    pass


class IdempotencyViolationError(TradeClawException):
    """Raised when idempotency guarantees are violated."""
    pass
