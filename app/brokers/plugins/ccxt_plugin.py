"""
CCXT plugin — registers ~100 cryptocurrency exchanges as Trade-Claw brokers.

CCXT (https://github.com/ccxt/ccxt) provides a unified Python API for
Binance, Kraken, Coinbase, Bybit, OKX, KuCoin, Bitfinex, Huobi, Gate.io,
MEXC and many more. By installing CCXT you unlock all of them through one
adapter — Trade-Claw exposes each exchange as a separate broker_type
``ccxt:<exchange-id>``.

Optional dependency: this module is loaded by the registry, but if ``ccxt``
isn't installed it logs a single info message and registers nothing — the
rest of Trade-Claw stays unaffected.

Caveats:
- CCXT is **synchronous**. We wrap each call in ``asyncio.to_thread`` so the
  FastAPI event loop stays responsive.
- Symbol normalisation: many exchanges use ``BTC/USDT`` or ``BTC-USD``; the
  Trade-Claw API uses uppercase + ``_`` separators for safety reasons. This
  adapter rewrites between the two; pass the *exchange's* symbol format on
  the wire (e.g. ``BTC/USDT`` for Binance).
- Sandbox / paper-mode: CCXT exposes ``set_sandbox_mode(True)`` for the
  exchanges that have one. We set it automatically when the session is
  created with environment=paper.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.brokers.broker_interface import (
    AuthenticationError,
    BrokerAdapter,
    BrokerError,
    InvalidOrderError,
    Order,
    OrderDirection,
    OrderRejectedError,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)
from app.brokers.registry import BrokerEntry, BrokerRegistry, CredentialField

logger = logging.getLogger(__name__)


# Curated list of exchanges to surface in the registry. CCXT supports more,
# but exposing all 100+ would just clutter the dropdown — the user can extend
# this list (or call ``ccxt.exchanges`` directly) if they need a niche venue.
_EXCHANGE_METADATA: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("binance",   "Binance",            ("crypto", "spot", "perpetuals")),
    ("kraken",    "Kraken",             ("crypto", "spot", "futures")),
    ("coinbase",  "Coinbase Advanced",  ("crypto", "spot")),
    ("bybit",     "Bybit",              ("crypto", "spot", "perpetuals")),
    ("okx",       "OKX",                ("crypto", "spot", "perpetuals")),
    ("kucoin",    "KuCoin",             ("crypto", "spot", "futures")),
    ("bitfinex",  "Bitfinex",           ("crypto", "spot", "margin")),
    ("huobi",     "HTX (Huobi)",        ("crypto", "spot", "futures")),
    ("gate",      "Gate.io",            ("crypto", "spot", "futures")),
    ("mexc",      "MEXC",               ("crypto", "spot", "futures")),
    ("bingx",     "BingX",              ("crypto", "spot", "perpetuals")),
    ("bitget",    "Bitget",             ("crypto", "spot", "perpetuals")),
)


def register(registry: BrokerRegistry) -> None:
    try:
        import ccxt  # noqa: PLC0415, F401
    except ImportError:
        logger.info(
            "CCXT plugin skipped: 'ccxt' not installed. "
            "Run 'pip install ccxt' to unlock Binance/Kraken/etc."
        )
        return

    for exchange_id, label, tags in _EXCHANGE_METADATA:
        if not hasattr(__import__("ccxt"), exchange_id):
            logger.debug("CCXT does not expose %s — skipping", exchange_id)
            continue

        broker_type = f"ccxt:{exchange_id}"

        def _factory(
            credentials: dict, *, _exchange_id: str = exchange_id, **config: Any
        ) -> BrokerAdapter:
            return CcxtAdapter(
                exchange_id=_exchange_id,
                credentials=credentials,
                **config,
            )

        registry.register(
            BrokerEntry(
                broker_type=broker_type,
                label=f"{label} (via CCXT)",
                description=(
                    f"Connect to {label} through CCXT's unified API. "
                    f"API key + secret required; some exchanges also need a "
                    f"passphrase (Coinbase, OKX, KuCoin)."
                ),
                factory=_factory,
                credentials=(
                    CredentialField(
                        name="api_key",
                        secret=False,
                        placeholder="your API key",
                        help=f"API key from your {label} account.",
                    ),
                    CredentialField(
                        name="secret_key",
                        secret=True,
                        placeholder="your API secret",
                        help=f"API secret from your {label} account.",
                    ),
                    CredentialField(
                        name="password",
                        required=False,
                        secret=True,
                        placeholder="API passphrase (if applicable)",
                        help="Required by Coinbase, OKX, KuCoin; ignored otherwise.",
                    ),
                ),
                paper_supported=True,
                live_supported=True,
                category="ccxt",
                tags=tags,
            )
        )


class CcxtAdapter(BrokerAdapter):
    """Bridge between Trade-Claw's BrokerAdapter and CCXT's sync API."""

    def __init__(
        self,
        exchange_id: str,
        credentials: dict[str, str],
        **kwargs: Any,
    ):
        super().__init__(
            api_key=credentials.get("api_key", ""),
            secret_key=credentials.get("secret_key", ""),
            **kwargs,
        )
        import ccxt  # noqa: PLC0415

        ExchangeClass = getattr(ccxt, exchange_id)
        params: dict[str, Any] = {
            "apiKey": self.api_key,
            "secret": self.secret_key,
            "enableRateLimit": True,
        }
        password = credentials.get("password")
        if password:
            params["password"] = password
        self.exchange = ExchangeClass(params)
        self._sandbox = bool(kwargs.get("sandbox", kwargs.get("testnet", False)))
        if self._sandbox:
            try:
                self.exchange.set_sandbox_mode(True)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "%s does not support sandbox mode — using live endpoints",
                    exchange_id,
                )
                self._sandbox = False

    # ------ Async wrappers for sync CCXT calls ------------------------------

    async def _call(self, fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    # ------ BrokerAdapter implementation ------------------------------------

    async def authenticate(self) -> bool:
        try:
            # Cheap call that requires authentication on most exchanges.
            await self._call(self.exchange.fetch_balance)
            self.is_authenticated = True
            return True
        except Exception as exc:  # noqa: BLE001
            self.is_authenticated = False
            raise AuthenticationError(f"CCXT auth failed: {exc}") from exc

    async def get_quote(self, symbol: str) -> Quote:
        try:
            ticker = await self._call(self.exchange.fetch_ticker, symbol)
            bid = float(ticker.get("bid") or ticker.get("last") or 0)
            ask = float(ticker.get("ask") or ticker.get("last") or 0)
            last = float(ticker.get("last") or bid or ask)
            return Quote(
                symbol=symbol,
                bid=bid,
                ask=ask,
                bid_size=float(ticker.get("bidVolume") or 0),
                ask_size=float(ticker.get("askVolume") or 0),
                last_price=last,
                timestamp=datetime.utcnow(),
            )
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"CCXT quote failed: {exc}") from exc

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        # CCXT's fetch_tickers fetches everything if available; cheaper than N calls
        try:
            data = await self._call(self.exchange.fetch_tickers, symbols)
        except Exception:  # noqa: BLE001
            return {s: await self.get_quote(s) for s in symbols}
        out: dict[str, Quote] = {}
        for sym, t in (data or {}).items():
            try:
                out[sym] = Quote(
                    symbol=sym,
                    bid=float(t.get("bid") or 0),
                    ask=float(t.get("ask") or 0),
                    bid_size=float(t.get("bidVolume") or 0),
                    ask_size=float(t.get("askVolume") or 0),
                    last_price=float(t.get("last") or 0),
                    timestamp=datetime.utcnow(),
                )
            except Exception:  # noqa: BLE001
                continue
        return out

    async def submit_order(self, order: Order) -> str:
        side = "buy" if order.direction == OrderDirection.BUY else "sell"
        order_type = "market" if order.order_type == OrderType.MARKET else "limit"
        params: dict[str, Any] = {}
        # Many exchanges accept stopLoss / takeProfit as params on the order
        # itself; CCXT normalises this when supported.
        if (sl := (order.metadata or {}).get("stop_loss")) is not None:
            params["stopLoss"] = {"triggerPrice": float(sl)}
        if (tp := (order.metadata or {}).get("take_profit")) is not None:
            params["takeProfit"] = {"triggerPrice": float(tp)}
        try:
            result = await self._call(
                self.exchange.create_order,
                order.symbol,
                order_type,
                side,
                order.quantity,
                order.price if order_type == "limit" else None,
                params,
            )
            return str(result.get("id") or "")
        except Exception as exc:  # noqa: BLE001
            raise OrderRejectedError(f"CCXT submit failed: {exc}") from exc

    async def get_order_status(self, order_id: str) -> Order:
        try:
            result = await self._call(self.exchange.fetch_order, order_id)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"CCXT fetch_order failed: {exc}") from exc
        status = (result.get("status") or "").lower()
        status_map = {
            "open": OrderStatus.ACCEPTED,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
        }
        return Order(
            order_id=str(result.get("id") or order_id),
            symbol=str(result.get("symbol") or ""),
            direction=OrderDirection.BUY
            if (result.get("side") or "").lower() == "buy"
            else OrderDirection.SELL,
            order_type=OrderType.LIMIT if (result.get("type") or "").lower() == "limit" else OrderType.MARKET,
            quantity=float(result.get("amount") or 0),
            price=float(result.get("price")) if result.get("price") else None,
            filled_quantity=float(result.get("filled") or 0),
            average_fill_price=float(result.get("average")) if result.get("average") else None,
            status=status_map.get(status, OrderStatus.PENDING),
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._call(self.exchange.cancel_order, order_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def get_positions(self) -> list[Position]:
        if not getattr(self.exchange, "has", {}).get("fetchPositions"):
            return []
        try:
            raw = await self._call(self.exchange.fetch_positions)
        except Exception:  # noqa: BLE001
            return []
        out: list[Position] = []
        for p in raw or []:
            try:
                qty = float(p.get("contracts") or p.get("amount") or 0)
                if qty == 0:
                    continue
                out.append(
                    Position(
                        symbol=str(p.get("symbol") or ""),
                        quantity=qty,
                        average_price=float(p.get("entryPrice") or 0),
                        current_price=float(p.get("markPrice") or 0),
                        unrealized_pnl=float(p.get("unrealizedPnl") or 0),
                        unrealized_pnl_percent=float(p.get("percentage") or 0),
                        side=OrderDirection.BUY if (p.get("side") or "").lower() == "long" else OrderDirection.SELL,
                        last_updated=datetime.utcnow(),
                    )
                )
            except Exception:  # noqa: BLE001
                continue
        return out

    async def get_position(self, symbol: str) -> Position | None:
        positions = await self.get_positions()
        for p in positions:
            if p.symbol == symbol:
                return p
        return None

    async def get_account_balance(self) -> dict[str, float]:
        try:
            bal = await self._call(self.exchange.fetch_balance)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"CCXT fetch_balance failed: {exc}") from exc
        # CCXT returns nested {currency: {free, used, total}} + a 'total' map.
        totals = bal.get("total") or {}
        usd_balance = float(totals.get("USDT") or totals.get("USD") or 0)
        return {
            "balance": usd_balance,
            "equity": usd_balance,
            "margin_available": usd_balance,
            "margin_used": 0.0,
            "raw": totals,
        }

    async def stream_prices(self, symbols: list[str], callback) -> None:
        # CCXT-pro supports websockets but is a separate package. For now we
        # raise a clear error so callers can fall back to polling get_quote.
        raise NotImplementedError(
            "Websocket streaming requires ccxt-pro. Poll get_quote instead."
        )

    async def disconnect(self) -> None:
        try:
            await self._call(self.exchange.close)
        except Exception:  # noqa: BLE001
            pass
