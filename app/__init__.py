"""
Trade-Claw Backend
Multi-broker trading infrastructure with risk management.

Modules:
- brokers: Adapter implementations (Mock, Hyperliquid, Alpaca, OANDA, etc.)
- api: Order API and normalization layer
- routing: Session management and broker selection
- wizard: Onboarding/configuration
- security: Audit logging and compliance
"""

__version__ = "0.3.0"
__author__ = "Elon (CTO)"
__description__ = "Multi-broker trading bot with risk management"

from app.brokers.broker_interface import (
    BrokerAdapter,
    Order,
    Quote,
    Position,
    OrderDirection,
    OrderType,
    OrderStatus,
)
from app.brokers.mock_broker import MockBrokerAdapter
from app.api.order_api_adapter import OrderAPIAdapter
from app.routing.broker_session_router import BrokerSessionRouter, BrokerType
from app.wizard.onboarding_broker_config import OnboardingWizard
from app.security.audit import AuditLog

__all__ = [
    'BrokerAdapter',
    'Order',
    'Quote',
    'Position',
    'OrderDirection',
    'OrderType',
    'OrderStatus',
    'MockBrokerAdapter',
    'OrderAPIAdapter',
    'BrokerSessionRouter',
    'BrokerType',
    'OnboardingWizard',
    'AuditLog',
]
