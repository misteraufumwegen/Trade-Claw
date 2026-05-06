"""
Loader that turns ``CustomBrokerDef`` rows into live ``BrokerEntry``s in the
plugin registry. Runs on startup and after every CRUD mutation, so adding a
broker via the UI takes effect immediately without a restart.

Two kinds of definitions are supported:

- ``ccxt`` — thin wrapper around the existing CCXT plugin for any
  ``ccxt.exchanges`` id (the curated list in the CCXT plugin file is just
  the *default* — the UI can register any other exchange CCXT supports).
- ``rest`` — the ``GenericRestAdapter`` with a user-supplied JSON config.

We tag every dynamically-registered entry with category=``custom`` so the
UI can show them under their own section.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.brokers.broker_interface import BrokerAdapter
from app.brokers.generic_rest_adapter import GenericRestAdapter, GenericRestConfig
from app.brokers.registry import REGISTRY, BrokerEntry, CredentialField

logger = logging.getLogger(__name__)


# Track which broker_types we registered dynamically so we can detach them
# cleanly on reload.
_DYNAMIC_KEYS: set[str] = set()


def _credentials_from_config(cfg: dict) -> tuple[CredentialField, ...]:
    """Pull a CredentialField list out of a saved config (or build defaults)."""
    raw_creds = cfg.get("credentials") or []
    if not raw_creds:
        return (
            CredentialField(name="api_key", secret=False, placeholder="API key"),
            CredentialField(
                name="secret_key",
                required=False,
                secret=True,
                placeholder="API secret (if applicable)",
            ),
        )
    out: list[CredentialField] = []
    for c in raw_creds:
        out.append(
            CredentialField(
                name=str(c.get("name") or "api_key"),
                required=bool(c.get("required", True)),
                secret=bool(c.get("secret", True)),
                placeholder=str(c.get("placeholder") or ""),
                help=str(c.get("help") or ""),
            )
        )
    return tuple(out)


def _build_ccxt_factory(exchange_id: str):
    def factory(credentials: dict, **config: Any) -> BrokerAdapter:
        # Defer import so a CCXT-less environment still loads the rest of
        # the loader (the API will simply error when the user tries to use
        # this broker without ccxt installed).
        from app.brokers.plugins.ccxt_plugin import CcxtAdapter  # noqa: PLC0415

        return CcxtAdapter(
            exchange_id=exchange_id,
            credentials=credentials,
            **config,
        )

    return factory


def _build_rest_factory(rest_config: dict):
    def factory(credentials: dict, **config: Any) -> BrokerAdapter:
        return GenericRestAdapter(
            config=rest_config,
            credentials=credentials,
            paper=bool(config.get("paper", True)),
        )

    return factory


def register_def(entry_dict: dict) -> BrokerEntry:
    """Build a registry entry from a CustomBrokerDef row dict and register it."""
    kind = (entry_dict.get("kind") or "rest").lower()
    broker_type = entry_dict["broker_type"]
    label = entry_dict.get("label") or broker_type
    description = entry_dict.get("description") or ""
    tags = tuple(t.strip() for t in (entry_dict.get("tags_csv") or "").split(",") if t.strip())
    cfg: dict = entry_dict.get("config") or {}

    if kind == "ccxt":
        exchange_id = cfg.get("exchange") or cfg.get("exchange_id")
        if not exchange_id:
            raise ValueError("CCXT def requires config.exchange")
        factory = _build_ccxt_factory(exchange_id)
        creds = (
            CredentialField(name="api_key", secret=False, placeholder="API key"),
            CredentialField(name="secret_key", secret=True, placeholder="API secret"),
            CredentialField(
                name="password",
                required=False,
                secret=True,
                placeholder="passphrase (Coinbase / OKX / KuCoin)",
                help="Some exchanges require a passphrase in addition to the API secret.",
            ),
        )
    elif kind == "rest":
        # Validate before registering — an invalid config now beats a 500
        # later when an order is submitted.
        GenericRestConfig(cfg.get("rest_config") or cfg)
        rest_config = cfg.get("rest_config") or cfg
        factory = _build_rest_factory(rest_config)
        creds = _credentials_from_config(cfg)
    else:
        raise ValueError(f"Unknown custom-broker kind: {kind}")

    entry = BrokerEntry(
        broker_type=broker_type,
        label=label,
        description=description,
        factory=factory,
        credentials=creds,
        paper_supported=bool(entry_dict.get("paper_supported", True)),
        live_supported=bool(entry_dict.get("live_supported", True)),
        category="custom",
        tags=tags,
    )
    REGISTRY.register(entry)
    _DYNAMIC_KEYS.add(broker_type.lower().strip())
    return entry


def reload_from_db(db_session) -> int:
    """Detach previously-registered dynamic entries and reload from DB."""
    from app.db.models import CustomBrokerDef  # noqa: PLC0415

    # Drop dynamic entries — we only own the ones in _DYNAMIC_KEYS.
    for key in list(_DYNAMIC_KEYS):
        REGISTRY._entries.pop(key, None)  # noqa: SLF001 — owner detaches own keys
    _DYNAMIC_KEYS.clear()

    rows = db_session.query(CustomBrokerDef).filter(CustomBrokerDef.enabled).all()
    count = 0
    for row in rows:
        try:
            cfg = json.loads(row.config_json or "{}")
        except json.JSONDecodeError:
            logger.warning("Custom broker def %s has invalid JSON; skipping", row.broker_type)
            continue
        try:
            register_def(
                {
                    "broker_type": row.broker_type,
                    "kind": row.kind,
                    "label": row.label,
                    "description": row.description,
                    "tags_csv": row.tags_csv,
                    "paper_supported": row.paper_supported,
                    "live_supported": row.live_supported,
                    "config": cfg,
                }
            )
            count += 1
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register custom broker %s", row.broker_type)
    logger.info("Custom broker reload: %d entries active", count)
    return count
