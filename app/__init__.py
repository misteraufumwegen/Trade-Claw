"""
Trade-Claw Backend
Multi-broker trading infrastructure with risk management.

Modules:
- brokers: Adapter implementations + plugin registry (Mock, Hyperliquid,
  CCXT-backed exchanges, and config-driven generic REST adapters)
- api: Order API and normalization layer
- routing: Session management and broker selection
- ml: Feature extractor, scorer, trainer, bootstrap, grader
- autopilot: TradingView webhook → grader → ML gate → risk → submit
- correlation, macro: Auxiliary analysis modules
- wizard: Onboarding / broker configuration
- security: Auth, audit logging, env validation
"""

__version__ = "0.3.0"

from app.brokers.broker_interface import (
    BrokerAdapter,
    Order,
    OrderDirection,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)
from app.brokers.mock_broker import MockBrokerAdapter

# The items below pull in heavy optional dependencies (aiohttp, web3, ccxt).
# Expose them lazily so ``import app`` works even when those packages aren't
# installed.


def __getattr__(name: str):
    if name == "OrderAPIAdapter":
        from app.api.order_api_adapter import OrderAPIAdapter

        return OrderAPIAdapter
    if name in {"BrokerSessionRouter", "BrokerType"}:
        from app.routing.broker_session_router import BrokerSessionRouter, BrokerType

        return {"BrokerSessionRouter": BrokerSessionRouter, "BrokerType": BrokerType}[name]
    if name == "OnboardingWizard":
        from app.wizard.onboarding_broker_config import OnboardingWizard

        return OnboardingWizard
    if name == "AuditLog":
        from app.security.audit import AuditLog

        return AuditLog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BrokerAdapter",
    "Order",
    "Quote",
    "Position",
    "OrderDirection",
    "OrderType",
    "OrderStatus",
    "MockBrokerAdapter",
    "OrderAPIAdapter",
    "BrokerSessionRouter",
    "BrokerType",
    "OnboardingWizard",
    "AuditLog",
]
