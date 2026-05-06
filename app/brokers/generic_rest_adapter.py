"""
Generic REST broker adapter.

Lets a non-developer wire up a REST broker through a JSON config — endpoint
templates, header specs, and JSON-paths to extract bid/ask/order_id/etc.
The user defines the config in the UI; this adapter executes it.

The config shape is documented in ``GenericRestConfig.example()`` below.
We enforce only what the BrokerAdapter contract needs; missing optional
endpoints (positions, batch quotes) downgrade gracefully.

Design principles:

- Templates use ``{var}`` substitution (``{api_key}``, ``{symbol}``,
  ``{order_id}``, ``{quantity}``, …). No code execution; values are
  string-substituted only.
- Auth currently supports Bearer header, custom-header, and query-param.
  More can be added without breaking existing configs.
- JSON paths are dotted strings (``data.bid``, ``positions.0.symbol``).
  Numbers in the path act as list indices.
- Errors from the broker that look like 4xx are raised as
  ``OrderRejectedError``; 5xx as ``BrokerError``; transport errors as
  ``BrokerError`` with the exception text wrapped.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp

from .broker_interface import (
    AuthenticationError,
    BrokerAdapter,
    BrokerError,
    Order,
    OrderDirection,
    OrderRejectedError,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)

logger = logging.getLogger(__name__)


def _get_path(obj: Any, path: str | None, default: Any = None) -> Any:
    """Look up a dotted-path value (``data.bid``, ``orders.0.id``) safely."""
    if not path:
        return default
    cur: Any = obj
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        elif isinstance(cur, dict):
            cur = cur.get(part)
            if cur is None:
                return default
        else:
            return default
    return cur


def _format_template(template: str | None, **vars: Any) -> str | None:
    """``{var}`` substitution that gracefully tolerates missing keys."""
    if template is None:
        return None
    out = template
    for k, v in vars.items():
        out = out.replace("{" + k + "}", str(v))
    return out


class GenericRestConfig:
    """Validates and exposes a config dict.

    The dict shape::

        {
          "base_url_paper": "https://demo.example.com",
          "base_url_live":  "https://api.example.com",
          "auth": {
            "type": "bearer" | "header" | "query",
            "header_name": "X-API-Key",        # for type=header
            "query_param": "apikey",           # for type=query
            "value_template": "Bearer {api_key}"  # default for bearer
          },
          "endpoints": {
            "authenticate": {"method": "GET", "path": "/account"},
            "quote":         {"method": "GET", "path": "/quote/{symbol}"},
            "submit_order":  {
              "method": "POST", "path": "/orders",
              "body_template": {
                "symbol": "{symbol}", "side": "{side_lower}",
                "qty": "{quantity}", "price": "{price}",
                "type": "{order_type_lower}",
                "stop_loss": "{stop_loss}", "take_profit": "{take_profit}"
              }
            },
            "get_order":     {"method": "GET", "path": "/orders/{order_id}"},
            "cancel_order":  {"method": "DELETE", "path": "/orders/{order_id}"},
            "positions":     {"method": "GET", "path": "/positions"},
            "balance":       {"method": "GET", "path": "/account"}
          },
          "paths": {
            "quote": {"bid": "bid", "ask": "ask", "last": "last"},
            "submit_order": {"order_id": "order_id"},
            "get_order": {
              "status": "status", "filled_quantity": "filled",
              "average_fill_price": "fill_price"
            },
            "positions": {
              "list": "positions",
              "symbol": "symbol", "quantity": "qty",
              "average_price": "avg_price", "current_price": "current",
              "unrealized_pnl": "unrealized_pnl", "side": "side"
            },
            "balance": {
              "balance": "balance", "equity": "equity",
              "margin_available": "margin_available"
            }
          },
          "status_map": {
            "filled": "FILLED", "open": "ACCEPTED", "cancelled": "CANCELLED",
            "rejected": "REJECTED"
          }
        }
    """

    def __init__(self, raw: dict):
        if not isinstance(raw, dict):
            raise ValueError("Config must be a JSON object")
        if "base_url_paper" not in raw and "base_url_live" not in raw:
            raise ValueError("Config requires base_url_paper and/or base_url_live")
        if "endpoints" not in raw or not isinstance(raw["endpoints"], dict):
            raise ValueError("Config.endpoints (object) is required")
        if "authenticate" not in raw["endpoints"]:
            raise ValueError("endpoints.authenticate is required")
        self._raw = raw

    @property
    def base_url_paper(self) -> str | None:
        return self._raw.get("base_url_paper")

    @property
    def base_url_live(self) -> str | None:
        return self._raw.get("base_url_live")

    @property
    def auth(self) -> dict:
        return self._raw.get("auth") or {"type": "bearer"}

    @property
    def endpoints(self) -> dict:
        return self._raw["endpoints"]

    @property
    def paths(self) -> dict:
        return self._raw.get("paths") or {}

    @property
    def status_map(self) -> dict:
        return self._raw.get("status_map") or {}

    def base_url(self, paper: bool) -> str:
        url = self.base_url_paper if paper else self.base_url_live
        if not url:
            url = self.base_url_live or self.base_url_paper
        if not url:
            raise ValueError("No base URL configured")
        return url.rstrip("/")

    @staticmethod
    def example() -> dict:
        return {
            "base_url_paper": "https://demo-api.example.com",
            "base_url_live": "https://api.example.com",
            "auth": {"type": "bearer", "value_template": "Bearer {api_key}"},
            "endpoints": {
                "authenticate": {"method": "GET", "path": "/account"},
                "quote": {"method": "GET", "path": "/quote/{symbol}"},
                "submit_order": {
                    "method": "POST",
                    "path": "/orders",
                    "body_template": {
                        "symbol": "{symbol}",
                        "side": "{side_lower}",
                        "qty": "{quantity}",
                        "type": "{order_type_lower}",
                        "stop_loss": "{stop_loss}",
                        "take_profit": "{take_profit}",
                    },
                },
                "get_order": {"method": "GET", "path": "/orders/{order_id}"},
                "cancel_order": {"method": "DELETE", "path": "/orders/{order_id}"},
                "positions": {"method": "GET", "path": "/positions"},
                "balance": {"method": "GET", "path": "/account"},
            },
            "paths": {
                "quote": {"bid": "bid", "ask": "ask", "last": "last"},
                "submit_order": {"order_id": "order_id"},
                "get_order": {
                    "status": "status",
                    "filled_quantity": "filled",
                    "average_fill_price": "fill_price",
                },
                "positions": {
                    "list": "positions",
                    "symbol": "symbol",
                    "quantity": "qty",
                    "average_price": "avg_price",
                    "current_price": "current",
                    "unrealized_pnl": "unrealized_pnl",
                    "side": "side",
                },
                "balance": {
                    "balance": "balance",
                    "equity": "equity",
                    "margin_available": "margin_available",
                },
            },
            "status_map": {
                "filled": "FILLED",
                "open": "ACCEPTED",
                "accepted": "ACCEPTED",
                "cancelled": "CANCELLED",
                "rejected": "REJECTED",
            },
        }


class GenericRestAdapter(BrokerAdapter):
    """REST-only BrokerAdapter driven by a config dict."""

    def __init__(
        self,
        config: dict,
        credentials: dict[str, str],
        *,
        paper: bool = True,
        **kwargs: Any,
    ):
        super().__init__(
            api_key=credentials.get("api_key", ""),
            secret_key=credentials.get("secret_key", ""),
            **kwargs,
        )
        self.config = GenericRestConfig(config)
        self.credentials = credentials
        self.paper = paper
        self._session: aiohttp.ClientSession | None = None

    # ------ HTTP plumbing ----------------------------------------------------

    def _auth_template_vars(self) -> dict[str, str]:
        return {k: str(v) for k, v in self.credentials.items()}

    def _build_headers(self) -> dict[str, str]:
        auth = self.config.auth
        headers: dict[str, str] = {"Content-Type": "application/json"}
        atype = (auth.get("type") or "bearer").lower()
        vars_ = self._auth_template_vars()
        if atype == "bearer":
            tpl = auth.get("value_template") or "Bearer {api_key}"
            headers["Authorization"] = _format_template(tpl, **vars_)
        elif atype == "header":
            name = auth.get("header_name") or "X-API-Key"
            tpl = auth.get("value_template") or "{api_key}"
            headers[name] = _format_template(tpl, **vars_)
        # query auth handled in _build_url
        return headers

    def _build_url(self, path_template: str, **vars: Any) -> str:
        url = self.config.base_url(self.paper) + _format_template(path_template, **vars)
        atype = (self.config.auth.get("type") or "bearer").lower()
        if atype == "query":
            param = self.config.auth.get("query_param") or "apikey"
            tpl = self.config.auth.get("value_template") or "{api_key}"
            sep = "&" if "?" in url else "?"
            url += f"{sep}{param}={_format_template(tpl, **self._auth_template_vars())}"
        return url

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _call(
        self,
        endpoint_key: str,
        url_vars: dict[str, Any] | None = None,
        body_vars: dict[str, Any] | None = None,
    ) -> Any:
        ep = self.config.endpoints.get(endpoint_key)
        if ep is None:
            raise BrokerError(f"Endpoint '{endpoint_key}' not configured")
        method = (ep.get("method") or "GET").upper()
        path_tpl = ep.get("path") or ""
        url = self._build_url(path_tpl, **(url_vars or {}))
        headers = self._build_headers()
        body_tpl = ep.get("body_template")
        body = None
        if body_tpl is not None:
            body = _expand_body(body_tpl, body_vars or {})

        session = await self._http()
        try:
            async with session.request(
                method, url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                text = await r.text()
                if r.status >= 500:
                    raise BrokerError(f"{endpoint_key}: HTTP {r.status} — {text[:200]}")
                if r.status >= 400:
                    raise OrderRejectedError(f"{endpoint_key}: HTTP {r.status} — {text[:200]}")
                if not text:
                    return {}
                try:
                    import json  # noqa: PLC0415

                    return json.loads(text)
                except Exception:
                    return {"_raw": text}
        except aiohttp.ClientError as exc:
            raise BrokerError(f"{endpoint_key}: network error {exc}") from exc

    # ------ BrokerAdapter ----------------------------------------------------

    async def authenticate(self) -> bool:
        try:
            await self._call("authenticate")
            self.is_authenticated = True
            return True
        except OrderRejectedError as exc:
            raise AuthenticationError(str(exc)) from exc

    async def get_quote(self, symbol: str) -> Quote:
        data = await self._call("quote", url_vars={"symbol": symbol})
        paths = self.config.paths.get("quote") or {}
        return Quote(
            symbol=symbol,
            bid=float(_get_path(data, paths.get("bid"), 0)),
            ask=float(_get_path(data, paths.get("ask"), 0)),
            bid_size=float(_get_path(data, paths.get("bid_size"), 0)),
            ask_size=float(_get_path(data, paths.get("ask_size"), 0)),
            last_price=float(_get_path(data, paths.get("last"), 0)),
            timestamp=datetime.utcnow(),
        )

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: await self.get_quote(s) for s in symbols}

    async def submit_order(self, order: Order) -> str:
        meta = order.metadata or {}
        body_vars = {
            "symbol": order.symbol,
            "side": order.direction.value,
            "side_lower": order.direction.value.lower(),
            "quantity": order.quantity,
            "qty": order.quantity,
            "price": order.price or "",
            "order_type": order.order_type.value,
            "order_type_lower": order.order_type.value.lower(),
            "stop_loss": meta.get("stop_loss") or "",
            "take_profit": meta.get("take_profit") or "",
            "entry_price": meta.get("entry_price") or order.price or "",
        }
        data = await self._call("submit_order", body_vars=body_vars)
        path = (self.config.paths.get("submit_order") or {}).get("order_id") or "order_id"
        order_id = str(_get_path(data, path) or "")
        if not order_id:
            raise OrderRejectedError(f"Submit succeeded but no order_id in response: {data}")
        return order_id

    async def get_order_status(self, order_id: str) -> Order:
        data = await self._call("get_order", url_vars={"order_id": order_id})
        paths = self.config.paths.get("get_order") or {}
        raw_status = str(_get_path(data, paths.get("status"), "")).lower()
        mapped = self.config.status_map.get(raw_status, raw_status.upper())
        try:
            status = OrderStatus(mapped)
        except ValueError:
            status = OrderStatus.PENDING
        return Order(
            order_id=order_id,
            symbol=str(_get_path(data, paths.get("symbol"), "")),
            direction=OrderDirection.BUY,
            order_type=OrderType.MARKET,
            quantity=float(_get_path(data, paths.get("quantity"), 0)),
            filled_quantity=float(_get_path(data, paths.get("filled_quantity"), 0)),
            average_fill_price=(
                float(_get_path(data, paths.get("average_fill_price")))
                if _get_path(data, paths.get("average_fill_price"))
                else None
            ),
            status=status,
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._call("cancel_order", url_vars={"order_id": order_id})
            return True
        except (OrderRejectedError, BrokerError):
            return False

    async def get_positions(self) -> list[Position]:
        if "positions" not in self.config.endpoints:
            return []
        data = await self._call("positions")
        paths = self.config.paths.get("positions") or {}
        list_path = paths.get("list", "")
        items = _get_path(data, list_path, []) if list_path else data
        if not isinstance(items, list):
            return []
        out: list[Position] = []
        for p in items:
            try:
                side_str = str(_get_path(p, paths.get("side"), "long")).lower()
                out.append(
                    Position(
                        symbol=str(_get_path(p, paths.get("symbol"), "")),
                        quantity=float(_get_path(p, paths.get("quantity"), 0)),
                        average_price=float(_get_path(p, paths.get("average_price"), 0)),
                        current_price=float(_get_path(p, paths.get("current_price"), 0)),
                        unrealized_pnl=float(_get_path(p, paths.get("unrealized_pnl"), 0)),
                        unrealized_pnl_percent=float(
                            _get_path(p, paths.get("unrealized_pnl_percent"), 0)
                        ),
                        side=OrderDirection.BUY
                        if "long" in side_str or "buy" in side_str
                        else OrderDirection.SELL,
                        last_updated=datetime.utcnow(),
                    )
                )
            except Exception:  # noqa: BLE001
                continue
        return out

    async def get_position(self, symbol: str) -> Position | None:
        for p in await self.get_positions():
            if p.symbol == symbol:
                return p
        return None

    async def get_account_balance(self) -> dict[str, float]:
        if "balance" not in self.config.endpoints:
            return {"balance": 0.0, "equity": 0.0, "margin_available": 0.0, "margin_used": 0.0}
        data = await self._call("balance")
        paths = self.config.paths.get("balance") or {}
        balance = float(_get_path(data, paths.get("balance"), 0))
        equity = float(_get_path(data, paths.get("equity"), balance))
        return {
            "balance": balance,
            "equity": equity,
            "margin_available": float(_get_path(data, paths.get("margin_available"), balance)),
            "margin_used": float(_get_path(data, paths.get("margin_used"), 0)),
        }

    async def stream_prices(self, symbols, callback) -> None:
        raise NotImplementedError("GenericRestAdapter is REST-only — poll get_quote.")

    async def disconnect(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


def _expand_body(template: Any, vars_: dict[str, Any]) -> Any:
    """Recursively substitute ``{var}`` in a dict/list/str body template."""
    if isinstance(template, str):
        s = _format_template(template, **vars_)
        # Best-effort numeric conversion for templates that resolve to a
        # bare number — JSON should not quote prices.
        if s in ("", None):
            return None
        try:
            if "." in s:
                return float(s)
            return int(s)
        except (TypeError, ValueError):
            return s
    if isinstance(template, dict):
        return {
            k: _expand_body(v, vars_)
            for k, v in template.items()
            if _expand_body(v, vars_) is not None
        }
    if isinstance(template, list):
        return [_expand_body(v, vars_) for v in template]
    return template
