# Custom Broker hinzufügen

Trade-Claw lässt dich beliebige Provider/Broker selbst integrieren. Es gibt
**drei** Wege, in steigender Komplexität:

1. **UI: CCXT-Exchange** — Sidebar → "Broker hinzufügen" → CCXT-Tab.
   Wähle einen aus 111+ unterstützten Exchanges (Binance, Kraken, Coinbase,
   Bybit, OKX, KuCoin, **Alpaca**, MEXC, Bitget, Bitstamp, Phemex, …).
   Kein Code, kein Restart. ✅ **Empfohlener Standardweg.**
2. **UI: Generic REST** — Sidebar → "Broker hinzufügen" → Generic-REST-Tab.
   JSON-Config mit Endpoints und Response-Pfaden. Deckt simple REST-APIs ab
   (Bearer/Header/Query-Auth, JSON-Bodies). Kein Code, kein Restart. ✅
3. **Plugin-Code** — für komplexe Fälle (EIP-712-Signing, OAuth, Websocket-only,
   MT4/MT5-Bridges): eigenes Python-Plugin in `app/brokers/plugins/`. Backend
   muss dafür neu gestartet werden.

Alle drei Wege erscheinen am Ende im Setup-Dialog (Settings → Neu
konfigurieren → "Neue Session") unter Kategorie `custom`.

---

## Weg 1 — UI: CCXT-Exchange (empfohlen)

Sidebar → **Broker hinzufügen** → Tab **CCXT-Exchange** → Filtern z.B. nach
`alpaca`, `binance`, `kraken`, → klicken → optional Label/Tags ergänzen →
**Hinzufügen**. Sofort verfügbar im Setup-Dialog, persistent gespeichert in
der DB.

API-äquivalent (für Skripte / TradingView-Setup):

```bash
curl -X POST http://localhost:8000/api/v1/brokers/defs/ccxt \
  -H "X-API-Key: $TRADE_CLAW_API_KEY" -H "Content-Type: application/json" \
  -d '{"exchange":"alpaca","label":"Alpaca","tags":["forex","stocks"]}'
```

CCXT ist bereits installiert. Standardmäßig sind ein paar populäre
Exchanges im Plugin-Code vorausgewählt:

| broker_type | Provider |
|-------------|----------|
| `ccxt:binance` | Binance |
| `ccxt:kraken` | Kraken |
| `ccxt:coinbase` | Coinbase Advanced |
| `ccxt:bybit` | Bybit |
| `ccxt:okx` | OKX |
| `ccxt:kucoin` | KuCoin |
| `ccxt:bitfinex` | Bitfinex |
| `ccxt:huobi` | HTX (Huobi) |
| `ccxt:gate` | Gate.io |
| `ccxt:mexc` | MEXC |
| `ccxt:bingx` | BingX |
| `ccxt:bitget` | Bitget |

### Setup einer Session mit dem registrierten Broker

1. Sidebar → **Settings → Neu konfigurieren** → Tab **„Neue Session"**
2. Im Broker-Dropdown unter Kategorie **CCXT** oder **CUSTOM** den Provider wählen
3. **Modus: Paper** (für Sandbox/Testnet, soweit der Provider einen hat) oder Live
4. API-Key + Secret eintragen — bei Coinbase, OKX, KuCoin auch das
   Passphrase-Feld ausfüllen
5. „Session erstellen" klicken

Trade-Claw versucht zuerst zu authentifizieren (`fetch_balance`). Wenn das
durchgeht, ist die Session aktiv und der Bot kann dort traden.

### Sandbox-Limitierungen

- **Binance:** Hat einen Testnet, CCXT setzt ihn automatisch wenn
  `environment=paper`.
- **Kraken / Coinbase:** Kein Sandbox in CCXT — Paper-Modus wird auf Live
  umgeleitet, also vorsichtig. Tipp: bei Live-Trading mit Kraken/Coinbase
  zuerst Mock-Broker für Bot-Logik-Tests nutzen, dann mit kleiner
  Position-Size live gehen.

### Eigene Exchange ergänzen

Geh einfach in **Broker hinzufügen → CCXT-Exchange**, filtere im Suchfeld
nach `bitvavo` / `phemex` / `alpaca` / `mt2trading` / etc. und klick
"Hinzufügen". Die Datei `app/brokers/plugins/ccxt_plugin.py` musst du nur
dann editieren wenn du den **Default-Bestand** für Erst-Installationen
ändern willst.

---

## Weg 2 — UI: Generic REST Broker

Sidebar → **Broker hinzufügen** → Tab **Generic REST**. Hier gibst du eine
JSON-Konfiguration ein, die Trade-Claw zur Laufzeit gegen die REST-API
deines Brokers ausführt. Geeignet für jeden Broker mit:

- Bearer / Header / Query-Param Authentifizierung
- JSON-Request- und Response-Bodies
- Standard-CRUD-Endpoints (account, quote, orders, positions, balance)

### Schritt 1: Vorlage öffnen

Im UI ist die Vorlage vorausgefüllt — sie sieht so aus (Auszug):

```json
{
  "base_url_paper": "https://demo-api.example.com",
  "base_url_live":  "https://api.example.com",
  "auth": {"type": "bearer", "value_template": "Bearer {api_key}"},
  "endpoints": {
    "authenticate": {"method": "GET", "path": "/account"},
    "quote":         {"method": "GET", "path": "/quote/{symbol}"},
    "submit_order":  {
      "method": "POST", "path": "/orders",
      "body_template": {
        "symbol": "{symbol}", "side": "{side_lower}",
        "qty": "{quantity}", "type": "{order_type_lower}",
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
    "get_order": {"status": "status", "filled_quantity": "filled", "average_fill_price": "fill_price"},
    "positions": {
      "list": "positions",
      "symbol": "symbol", "quantity": "qty",
      "average_price": "avg_price", "current_price": "current",
      "unrealized_pnl": "unrealized_pnl", "side": "side"
    },
    "balance": {"balance": "balance", "equity": "equity", "margin_available": "margin_available"}
  },
  "status_map": {"filled": "FILLED", "open": "ACCEPTED", "cancelled": "CANCELLED"}
}
```

### Schritt 2: Anpassen

- `base_url_paper` / `base_url_live` → die URL deines Brokers.
- `auth.type` → `bearer` für `Authorization: Bearer <key>`, `header` für
  benutzerdefinierten Header (`header_name` setzen), `query` für API-Key
  als URL-Parameter (`query_param` setzen).
- `endpoints.<name>.path` → setze die Pfade deines Brokers ein. `{symbol}`,
  `{order_id}`, `{api_key}` usw. werden zur Laufzeit ersetzt.
- `paths.<endpoint>.<feld>` → JSON-Pfade in der Response. Z.B. wenn dein
  Broker `{"data": {"bid": 1.085}}` zurückgibt, schreib `data.bid`.
- `status_map` → mappe deine Broker-Statuswerte (`open`, `closed`, …) auf
  Trade-Claw-Status: `PENDING`, `ACCEPTED`, `FILLED`, `PARTIALLY_FILLED`,
  `CANCELLED`, `REJECTED`, `EXPIRED`.

### Schritt 3: Testen

Im Block „Verbindung testen" kannst du echte Test-Credentials eintragen
(`{"api_key":"...","secret_key":"..."}`). Trade-Claw ruft `authenticate`
und (falls definiert) `balance` gegen deine Broker-URL auf, **ohne den
Broker zu speichern**. Du siehst sofort, ob die Authentifizierung greift.

### Schritt 4: Speichern

Klick „Speichern & registrieren". Der Broker landet in der DB und ist
**sofort** im Setup-Dropdown unter Kategorie `custom` verfügbar — kein
Restart nötig.

### Limitierungen des Generic-REST-Adapters

- Kein WebSocket-Streaming. `stream_prices` wirft `NotImplementedError`.
  Trade-Claw fällt auf Polling von `get_quote` zurück.
- Keine HMAC- oder EIP-712-Signaturen. Wenn dein Broker das verlangt,
  brauchst du Weg 3 (Plugin).
- Templating ist String-Substitution, keine Logik. Dynamische Werte (z.B.
  Zeitstempel im Body) gehen nicht ohne Plugin.
- Status-Mapping ist 1:1. Wenn dein Broker komplexe Status-Hierarchien hat,
  baue sie im Plugin auf.

---

## Weg 3 — Eigenes Plugin schreiben

Das ist der „mache es richtig"-Weg, wenn dein Provider nicht in CCXT ist
und auch nicht über Generic-REST abbildbar ist.
Jedes Plugin ist eine einzelne Python-Datei in `app/brokers/plugins/` und
muss zwei Dinge tun:

1. Eine Klasse definieren, die von `BrokerAdapter` erbt
   (`app/brokers/broker_interface.py`).
2. Eine `register(registry)`-Funktion exportieren, die dem Registry mitteilt,
   wie dein Broker heißt und welche Credentials er braucht.

### Schritt 2.1 — Skeleton kopieren

Speichere als `app/brokers/plugins/my_broker.py`:

```python
"""Plugin for MyBroker (https://my-broker.example.com)."""

from datetime import datetime
from typing import Any

import aiohttp  # already in requirements

from app.brokers.broker_interface import (
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
from app.brokers.registry import BrokerEntry, BrokerRegistry, CredentialField


class MyBrokerAdapter(BrokerAdapter):
    BASE_URL_LIVE  = "https://api.my-broker.example.com"
    BASE_URL_PAPER = "https://demo-api.my-broker.example.com"

    def __init__(self, api_key: str, secret_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, secret_key=secret_key, **kwargs)
        self.base_url = self.BASE_URL_PAPER if kwargs.get("paper", True) else self.BASE_URL_LIVE
        self._session: aiohttp.ClientSession | None = None

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._session

    async def authenticate(self) -> bool:
        try:
            session = await self._http()
            async with session.get(f"{self.base_url}/account") as r:
                r.raise_for_status()
            self.is_authenticated = True
            return True
        except Exception as exc:
            raise AuthenticationError(str(exc)) from exc

    async def get_quote(self, symbol: str) -> Quote:
        session = await self._http()
        async with session.get(f"{self.base_url}/quote/{symbol}") as r:
            data = await r.json()
        return Quote(
            symbol=symbol,
            bid=float(data["bid"]),
            ask=float(data["ask"]),
            bid_size=float(data.get("bid_size", 0)),
            ask_size=float(data.get("ask_size", 0)),
            last_price=float(data.get("last", data["bid"])),
            timestamp=datetime.utcnow(),
        )

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: await self.get_quote(s) for s in symbols}

    async def submit_order(self, order: Order) -> str:
        session = await self._http()
        payload = {
            "symbol": order.symbol,
            "side": "buy" if order.direction == OrderDirection.BUY else "sell",
            "qty": order.quantity,
            "type": "market" if order.order_type == OrderType.MARKET else "limit",
            "price": order.price,
            "stop_loss": (order.metadata or {}).get("stop_loss"),
            "take_profit": (order.metadata or {}).get("take_profit"),
        }
        async with session.post(f"{self.base_url}/orders", json=payload) as r:
            if r.status >= 400:
                raise OrderRejectedError(await r.text())
            data = await r.json()
        return str(data["order_id"])

    async def get_order_status(self, order_id: str) -> Order:
        session = await self._http()
        async with session.get(f"{self.base_url}/orders/{order_id}") as r:
            data = await r.json()
        return Order(
            order_id=order_id,
            symbol=data["symbol"],
            direction=OrderDirection(data["side"].upper()),
            order_type=OrderType.MARKET,
            quantity=float(data["qty"]),
            filled_quantity=float(data.get("filled", 0)),
            average_fill_price=float(data["fill_price"]) if data.get("fill_price") else None,
            status=_status_map(data["status"]),
        )

    async def cancel_order(self, order_id: str) -> bool:
        session = await self._http()
        async with session.delete(f"{self.base_url}/orders/{order_id}") as r:
            return r.status < 400

    async def get_positions(self) -> list[Position]:
        session = await self._http()
        async with session.get(f"{self.base_url}/positions") as r:
            data = await r.json()
        return [
            Position(
                symbol=p["symbol"],
                quantity=float(p["qty"]),
                average_price=float(p["avg_price"]),
                current_price=float(p["current"]),
                unrealized_pnl=float(p["unrealized_pnl"]),
                unrealized_pnl_percent=float(p.get("unrealized_pct", 0)),
                side=OrderDirection.BUY if p["side"] == "long" else OrderDirection.SELL,
                last_updated=datetime.utcnow(),
            )
            for p in data.get("positions", [])
        ]

    async def get_position(self, symbol: str) -> Position | None:
        for p in await self.get_positions():
            if p.symbol == symbol:
                return p
        return None

    async def get_account_balance(self) -> dict[str, float]:
        session = await self._http()
        async with session.get(f"{self.base_url}/account") as r:
            data = await r.json()
        return {
            "balance": float(data["balance"]),
            "equity": float(data["equity"]),
            "margin_available": float(data.get("margin_available", data["balance"])),
            "margin_used": float(data.get("margin_used", 0)),
        }

    async def stream_prices(self, symbols, callback) -> None:
        raise NotImplementedError("Add WS streaming if needed.")

    async def disconnect(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


def _status_map(s: str) -> OrderStatus:
    return {
        "pending": OrderStatus.PENDING,
        "accepted": OrderStatus.ACCEPTED,
        "filled": OrderStatus.FILLED,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "cancelled": OrderStatus.CANCELLED,
        "rejected": OrderStatus.REJECTED,
        "expired": OrderStatus.EXPIRED,
    }.get(s.lower(), OrderStatus.PENDING)


def register(registry: BrokerRegistry) -> None:
    """Required entry point — Trade-Claw calls this on startup."""

    def factory(credentials: dict, **config: Any) -> BrokerAdapter:
        return MyBrokerAdapter(
            api_key=credentials.get("api_key", ""),
            secret_key=credentials.get("secret_key", ""),
            paper=config.get("paper", True),
            **{k: v for k, v in config.items() if k != "paper"},
        )

    registry.register(
        BrokerEntry(
            broker_type="my_broker",                 # what the user picks in the dropdown
            label="MyBroker (Forex / CFD)",
            description="My-Broker.example.com REST API.",
            factory=factory,
            credentials=(
                CredentialField(name="api_key", secret=False, placeholder="your API key"),
                CredentialField(name="secret_key", secret=True, placeholder="your secret"),
            ),
            paper_supported=True,
            live_supported=True,
            category="custom",
            tags=("forex", "cfd"),
        )
    )
```

### Schritt 2.2 — Backend neu starten

`Ctrl+C` im Launcher-Terminal, dann nochmal `start-app.bat` /
`start-app.command`. Im Log siehst du:

```
INFO  Registered broker plugin: my_broker (custom)
```

### Schritt 2.3 — Testen

`curl http://localhost:8000/api/v1/brokers/types` muss `my_broker` jetzt
auflisten. Danach im UI Settings → Neu konfigurieren → Tab „Neue Session"
und „MyBroker" auswählen — die zwei Credential-Felder erscheinen
automatisch.

---

## Tipps & Stolperfallen

**Symbol-Mapping:** Trade-Claw gibt deinem Adapter die Symbole 1:1 weiter,
wie sie in der API ankommen (vom UI oder vom TradingView-Webhook). Wenn dein
Broker sie anders nennt (z.B. `EUR_USD` vs `EURUSD` vs `EUR/USD`),
übersetze im Adapter. Beispiel im CCXT-Plugin: keine Übersetzung, weil CCXT
schon mit `BTC/USDT`-Format arbeitet, aber für TradingView-Webhooks
solltest du das Mapping in der Pine-Vorlage machen
(`docs/trade_claw_alert.pine` macht es schon für die Majors).

**Auto-Resolve-Poller:** Der FastAPI-Poller liest
`broker.orders[order_id].metadata["closed_price"]` um Outcomes aufzulösen.
Wenn dein Broker eine andere Mechanik hat (Webhooks, WebSocket-Events,
Position-Polling), passe den Poller in `app/main.py:_outcome_poller` an —
oder schreibe eine eigene Background-Task im Plugin, die `metadata`
auffüllt sobald deine API meldet „position closed".

**Optional-deps-Pattern:** Wenn dein Plugin eine Python-Library braucht,
die nicht alle User installiert haben, mache den Import in `register()`
mit `try: import ... except ImportError: return`. Das verhindert, dass die
gesamte App kaputtgeht, wenn die Lib fehlt — das CCXT-Plugin tut genau das.

**Authentifizierung scheitert mit `Authentication failed for <type>`:** Im
Adapter wirf `AuthenticationError` *vor* dem `return False` — der Router
loggt das und propagiert den Grund nach oben.

**Mehrere Sessions parallel:** Du kannst pro Aufruf `setupBroker` eine neue
Session erstellen — der Router speichert sie unter ihrer `session_id`.
Verschiedene Broker laufen problemlos parallel, du siehst sie im UI im
Settings-Bereich.

---

## Referenz: BrokerAdapter-Schnittstelle

Vollständige Methoden, die jedes Plugin implementieren muss
(`app/brokers/broker_interface.py`):

| Methode | Zweck |
|---------|-------|
| `authenticate()` → `bool` | Credentials gegen den Provider prüfen |
| `get_quote(symbol)` → `Quote` | Live Bid/Ask/Last für ein Symbol |
| `get_quotes_batch(symbols)` → `dict[symbol, Quote]` | Bulk-Variante |
| `submit_order(order)` → `str` | Order absetzen, Broker-`order_id` zurück |
| `get_order_status(order_id)` → `Order` | Status + Fill-Info |
| `cancel_order(order_id)` → `bool` | Cancel; `True` wenn ok |
| `get_positions()` → `list[Position]` | Offene Positionen |
| `get_position(symbol)` → `Position | None` | Einzelne Position |
| `get_account_balance()` → `dict` | `balance`, `equity`, `margin_*` |
| `stream_prices(symbols, callback)` | WebSocket-Stream (NotImplementedError ok wenn nicht gewünscht) |
| `disconnect()` | Aufräumen (HTTP-Sessions, WS, …) |

Die `Quote`, `Order`, `Position`-Dataclasses sind in
`app/brokers/broker_interface.py` definiert — keep it that way, sonst
zerbrechen Risk-Engine und ML-Service.
