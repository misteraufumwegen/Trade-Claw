"""
Broker plugin registry.

Goals:
- Built-in brokers (Mock, Hyperliquid, …) and user-supplied plugins both
  get instantiated through one path: ``REGISTRY.create(broker_type, ...)``.
- Adding a new broker means dropping a Python file into
  ``app/brokers/plugins/`` that exposes a ``register(registry)`` function.
- Plugins are auto-loaded on first import of this module so the FastAPI
  app picks them up at startup with zero configuration.
- Each entry carries a *credential template* that the frontend renders so
  users know which fields to fill — no hard-coded "alpaca needs api_key"
  branches in the UI any more.

Design choice: registry stores **factories** (callables returning a
``BrokerAdapter``) rather than the classes themselves. That lets a plugin
register many ``broker_type``s from one file (e.g. CCXT exposes
``ccxt:binance``, ``ccxt:kraken``, … from a single class).
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .broker_interface import BrokerAdapter

logger = logging.getLogger(__name__)

# Factory signature: (credentials, **config) -> BrokerAdapter
BrokerFactory = Callable[..., BrokerAdapter]


@dataclass(frozen=True)
class CredentialField:
    """Description of one credential the user must supply."""

    name: str
    required: bool = True
    secret: bool = True
    placeholder: str = ""
    help: str = ""


@dataclass(frozen=True)
class BrokerEntry:
    """A registered broker — what the registry hands back to the API."""

    broker_type: str
    label: str
    description: str
    factory: BrokerFactory
    credentials: tuple[CredentialField, ...]
    paper_supported: bool = True
    live_supported: bool = True
    category: str = "custom"  # "builtin" | "ccxt" | "custom"
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "broker_type": self.broker_type,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "tags": list(self.tags),
            "paper_supported": self.paper_supported,
            "live_supported": self.live_supported,
            "credentials": [
                {
                    "name": c.name,
                    "required": c.required,
                    "secret": c.secret,
                    "placeholder": c.placeholder,
                    "help": c.help,
                }
                for c in self.credentials
            ],
        }


class BrokerRegistry:
    """In-process registry. Single instance lives below as ``REGISTRY``."""

    def __init__(self) -> None:
        self._entries: dict[str, BrokerEntry] = {}
        self._loaded = False

    # ----- Registration -----------------------------------------------------

    def register(self, entry: BrokerEntry) -> None:
        key = entry.broker_type.lower().strip()
        if key in self._entries:
            logger.debug("Broker %s already registered — overwriting", key)
        self._entries[key] = entry
        logger.info("Registered broker plugin: %s (%s)", key, entry.category)

    def register_many(self, entries: Iterable[BrokerEntry]) -> None:
        for e in entries:
            self.register(e)

    # ----- Querying ---------------------------------------------------------

    def list(self) -> list[BrokerEntry]:
        self._ensure_loaded()
        return sorted(self._entries.values(), key=lambda e: (e.category, e.broker_type))

    def get(self, broker_type: str) -> BrokerEntry | None:
        self._ensure_loaded()
        return self._entries.get(broker_type.lower().strip())

    def known_types(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._entries.keys())

    # ----- Factory ---------------------------------------------------------

    def create(self, broker_type: str, credentials: dict, **config: Any) -> BrokerAdapter:
        entry = self.get(broker_type)
        if entry is None:
            raise ValueError(f"Unknown broker type '{broker_type}'. Known: {self.known_types()}")
        return entry.factory(credentials, **config)

    # ----- Plugin discovery -------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        # Mark first to avoid recursive imports re-triggering discovery.
        self._loaded = True
        self._discover_plugins()

    def _discover_plugins(self) -> None:
        plugins_dir = Path(__file__).parent / "plugins"
        if not plugins_dir.is_dir():
            logger.debug("No plugins directory at %s", plugins_dir)
            return
        for path in sorted(plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module_name = f"app.brokers.plugins.{path.stem}"
            try:
                module = importlib.import_module(module_name)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to import broker plugin %s", module_name)
                continue
            register_fn = getattr(module, "register", None)
            if not callable(register_fn):
                logger.warning(
                    "Plugin %s has no register(registry) function — skipping",
                    module_name,
                )
                continue
            try:
                register_fn(self)
            except Exception:  # noqa: BLE001
                logger.exception("Plugin %s register() failed", module_name)


# Single registry shared across the process.
REGISTRY = BrokerRegistry()


# ---------------------------------------------------------------------------
# Built-in registrations — kept here so the existing brokers benefit from
# the same metadata pipeline as plugin-supplied ones.
# ---------------------------------------------------------------------------


def _register_builtins(registry: BrokerRegistry) -> None:
    from .mock_broker import MockBrokerAdapter  # noqa: PLC0415

    def _mock_factory(credentials: dict, **config: Any) -> BrokerAdapter:
        return MockBrokerAdapter(
            api_key=credentials.get("api_key", "mock"),
            **config,
        )

    registry.register(
        BrokerEntry(
            broker_type="mock",
            label="Mock (Testing)",
            description=(
                "In-memory simulator with auto-resolving fills. Use this for "
                "smoke tests and ML-pipeline validation. Never trades real money."
            ),
            factory=_mock_factory,
            credentials=(
                CredentialField(
                    name="api_key",
                    required=False,
                    secret=False,
                    placeholder="anything",
                    help="Not used; any value is accepted.",
                ),
            ),
            paper_supported=True,
            live_supported=False,
            category="builtin",
            tags=("testing",),
        )
    )

    # Hyperliquid — registers only when its dependencies (eth-account, web3)
    # are installed. The current adapter file does its own imports; we wrap
    # in try/except so the registry survives a missing optional dep.
    try:
        from .hyperliquid_adapter import HyperliquidAdapter  # noqa: PLC0415

        def _hl_factory(credentials: dict, **config: Any) -> BrokerAdapter:
            return HyperliquidAdapter(
                api_key=credentials.get("api_key", ""),
                secret_key=credentials.get("secret_key", ""),
                **config,
            )

        registry.register(
            BrokerEntry(
                broker_type="hyperliquid",
                label="Hyperliquid (DEX, perpetuals)",
                description=(
                    "Hyperliquid perps via EIP-712 signing. Paper mode hits "
                    "the testnet, live mode hits mainnet — needs an Ethereum "
                    "private key and a wallet address."
                ),
                factory=_hl_factory,
                credentials=(
                    CredentialField(
                        name="api_key",
                        secret=False,
                        placeholder="0x… wallet address",
                        help="Hyperliquid wallet address (public).",
                    ),
                    CredentialField(
                        name="secret_key",
                        secret=True,
                        placeholder="0x… 64-hex private key",
                        help="Ethereum private key for EIP-712 signing.",
                    ),
                ),
                paper_supported=True,
                live_supported=True,
                category="builtin",
                tags=("crypto", "perpetuals", "dex"),
            )
        )
    except ImportError as exc:
        logger.info("Hyperliquid not registered (optional deps missing: %s)", exc)


_register_builtins(REGISTRY)
