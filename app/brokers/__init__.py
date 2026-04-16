"""Broker adapters for Trade-Claw.

The canonical broker contract is :class:`.broker_interface.BrokerAdapter`.
Adapters currently shipped:

- ``MockBrokerAdapter``   — in-memory simulator, used by tests.
- ``HyperliquidAdapter``  — live Hyperliquid DEX adapter (EIP-712 signing).

Alpaca and OANDA adapters were removed because the previous implementations
were empty ``NotImplementedError`` stubs (see review finding C5). New
adapters must subclass ``BrokerAdapter`` and register with
``app.routing.BrokerSessionRouter``.
"""

from typing import TYPE_CHECKING

from .broker_interface import BrokerAdapter, Order, Position, Quote
from .mock_broker import MockBrokerAdapter

# Backward-compat alias — some older code/tests import ``MockBroker``.
MockBroker = MockBrokerAdapter


def __getattr__(name: str):
    """Lazy-import heavy adapters so the package loads without their deps.

    ``HyperliquidAdapter`` pulls in ``web3`` / ``eth_account``; users who only
    run the mock broker shouldn't have to install those packages.
    """
    if name == "HyperliquidAdapter":
        from .hyperliquid_adapter import HyperliquidAdapter  # noqa: WPS433
        return HyperliquidAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:  # pragma: no cover
    from .hyperliquid_adapter import HyperliquidAdapter  # noqa: F401


__all__ = [
    "BrokerAdapter",
    "Order",
    "Position",
    "Quote",
    "MockBroker",
    "MockBrokerAdapter",
    "HyperliquidAdapter",
]
