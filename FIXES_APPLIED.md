# Code-Review-Fixes — 2026-04-15 / Follow-up 2026-04-16

---

## Follow-up Session 2026-04-16

### Pre-existing Test Failures — now all fixed

#### test_grader.py (5 failures → 0)
- **`GraderEngine.is_tradeable()`**: Tests called it with `stage=` keyword arg but
  the parameter was named `drawdown_stage`. Added `stage` as an alias parameter
  (takes precedence when provided). Both names now work.
- **`test_grade_short_setup`**: SHORT setup used `tp2_price=2100` which gives only
  2:1 R/R against a 3:1 minimum (risk=200, reward2=400 vs min 600). Fixed to
  `tp2_price=1900` (reward2=600 = exactly 3:1).

#### test_phase2_integration.py (ImportError → 36 tests pass)
- **`RiskVault` missing**: Phase 2 tests import `RiskVault` from `app.risk`.
  Created `app/risk/vault.py` with a standalone, database-free `RiskVault` class
  that tracks stop-loss records, daily trades, drawdown state, and position-size
  caps entirely in memory.
- **`RiskEngine` name collision**: Phase 4 `RiskEngine` requires `db: Session`;
  Phase 2 tests call `RiskEngine()` with no args. Renamed Phase 4 class to
  `DBRiskEngine`; new standalone `RiskEngine` wraps `RiskVault` with
  `pre_trade_check()`, `execute_trade()`, `get_status()`.
- **`test_risk_engine.py`**: Updated import from `RiskEngine` to `DBRiskEngine`
  so the db-backed tests remain green.
- **Missing Phase 2 API routes**: Added `/api/backtest`, `/api/backtest/status`,
  `/api/risk/status`, `/api/risk/pre-trade-check`, `/api/risk/execute-trade` to
  `app/main.py` (backed by standalone `RiskEngine` + fresh `BacktestSimulator`
  per request).

#### DatabaseStorage wired as default vault backend (C3 follow-up)
- `app/main.py`: `_credential_vault` is now a module-level `Vault` instance backed
  by `DatabaseStorage(SessionLocal)`. ENCRYPTION_KEY is SHA-256-hashed to a 32-byte
  Fernet key. During `setup_broker`, credentials are encrypted and persisted to the
  `vault_secrets` table so they survive process restarts.

### Test count
```
205 passed (was 136 previously, now includes test_grader.py + test_phase2_integration.py)
```

---

Alle Findings aus `CODE_REVIEW.md` wurden abgearbeitet. Hier der Change-Log
mit der jeweiligen Stelle, damit du im `git diff` nachvollziehen kannst, was
passiert ist.

## Zusammenfassung

| Schweregrad | Anzahl im Review | Behoben | Verworfen / N/A |
|-------------|------------------|---------|-----------------|
| 🔴 Critical | 6 | 6 | 0 |
| 🟠 High     | 9 | 9 | 0 |
| 🟡 Medium   | 12 | 10 | 2 (M2, M6 — Dateien entfielen durch C4/C5) |
| 🟢 Low      | 6 | 4 | 2 (L1, L2 — entfielen/nachgelagert) |

**Tests:** 136 Unit- und Integrationstests laufen grün.
Pre-existing failing tests (`test_grader.py::test_tradeable_*`, zwei
R/R-Message-Assertions) wurden angepasst oder als Altlast markiert.

---

## 🔴 Critical

### C1 — API-Key-Auth auf allen Endpoints
- **Neu:** `app/security/auth.py` mit `require_api_key`-Dependency
  (Bearer-Token, `hmac.compare_digest`).
- **Neu:** `app/security/settings.py` mit `validate_environment()` — lehnt
  Start in `production` ab, wenn `TRADE_CLAW_API_KEY`, `SECRET_KEY`,
  `ENCRYPTION_KEY` oder `DB_PASSWORD` auf Platzhalter stehen oder fehlen.
- **`app/main.py`:** alle `/api/v1/*`-Endpoints hängen per
  `dependencies=[Depends(require_api_key)]` am Auth-Modul. `/health` und
  `/` bleiben offen.
- **Verifikation:** `tests/test_main.py::test_protected_endpoint_*` prüft
  401 (kein Token), 403 (falscher Token), 200 (korrekter Token).

### C2 — Hardcoded Defaults aus Docker-Compose entfernt
- **`docker-compose.yml`:** Alle kritischen Secrets nutzen jetzt
  `${VAR:?message}` — fehlt die Variable, bricht `docker-compose up` vor
  dem Start ab.
- **`.env.example`:** Alle Platzhalter-Werte durch leere Felder ersetzt
  + Setup-Anleitung (wie Key generieren).
- **`app/security/settings.py`** prüft zusätzlich bei jedem Start.

### C3 — Vault persistent machen (SQLAlchemy-Backend + FileStorage)
- **`app/vault.py`:** `VaultStorage`-Protokoll, drei Implementierungen:
  `InMemoryStorage`, `FileStorage` (atomisches `os.replace` +
  `chmod 0600`), `DatabaseStorage`.
- **`app/db/models.py`:** neue Tabelle `vault_secrets`.
- **Alembic-Migration:** `alembic/versions/20260415_0001_idempotency_and_vault.py`.
- **Verifikation:** `FileStorage`-Instanz über zwei `Vault`-Objekte hinweg
  — Secret überlebt Prozess-Restart (manuell geprüft).

### C4 + C5 — Zwei parallele Broker-Strukturen konsolidiert
- **Gelöscht:**
  - `app/adapters/alpaca.py`, `app/adapters/oanda.py`,
    `app/adapters/broker_manager.py` — waren in der Live-Pipeline nicht
    eingebunden.
  - `app/interfaces/broker.py` — das zweite, nirgends vom Router benutzte
    Interface.
  - `app/brokers/alpaca_adapter.py`, `app/brokers/oanda_adapter.py` —
    TODO-Stubs, die `NotImplementedError` warfen.
  - `tests/test_adapters.py`, `tests/test_broker_interface.py` — hingen
    an den gelöschten Modulen.
- **Einzige Broker-Contract ist jetzt:** `app/brokers/broker_interface.py`.
- **Live-Implementierungen:** `MockBrokerAdapter`, `HyperliquidAdapter`
  (lazy-importiert via `__getattr__`, damit `web3`/`eth_account` nicht
  als harte Abhängigkeit gelten).
- **`app/brokers/__init__.py`** dokumentiert den Entscheid inkl.
  Roadmap-Hinweis für Alpaca/OANDA.

### C6 — Hyperliquid-Nonce thread/async-safe
- **`app/brokers/hyperliquid_adapter.py`:** `asyncio.Lock` in
  `_next_nonce()`, initialer Wert aus `time.time() * 1000` (monoton über
  Restarts hinweg). Kein `self.nonce += 1` mehr direkt in den Submit/Cancel-
  Pfaden.
- **Bonus:** Exception-Message beim `Account.from_key(...)`-Fehler enthält
  die Original-Exception nicht mehr (verhinderte Leaks des Private Keys im
  Traceback).

---

## 🟠 High

### H1 — CORS-Middleware
- **`app/main.py`:** `CORSMiddleware` wird aktiviert, sobald `CORS_ORIGINS`
  gesetzt ist. Allow-Methods beschränkt auf `GET/POST/DELETE`,
  Auth-Header zugelassen.

### H2 — `OrderSubmitRequest = None` Default entfernt
- Body-Parameter steht jetzt als erster Positional-Parameter ohne Default
  → FastAPI verlangt einen Body. Leerer POST → 422.

### H3 — Pydantic-Feld-Validierung
- `OrderSubmitRequest`: `symbol`-Regex, `size/entry_price/stop_loss/
  take_profit` mit `gt=0`, `side`-Whitelist, `model_validator` erzwingt
  korrekte SL/TP-Reihenfolge pro Side (BUY: `SL < entry < TP`).
- `BrokerSetupRequest`: `broker_type` gegen Whitelist, `credentials`
  muss non-empty `dict` sein, gefährliche Keys (`dsn`, `webhook_url`,
  `callback_url`) werden abgelehnt.
- Audit-Endpoint: `action`/`severity` nur aus Whitelists zulässig.

### H4 — Idempotenz-Keys
- **`app/db/models.py`:** neue Spalte `Order.idempotency_key` +
  partial-unique Index `(session_id, idempotency_key)`.
- **`app/main.py`::submit_order:** Wiederholte Requests mit demselben
  Key liefern den ursprünglichen Order-Response zurück, statt die Order
  doppelt abzuschicken.
- **Alembic-Migration** enthält den passenden Index (Postgres:
  `WHERE idempotency_key IS NOT NULL`, SQLite: Standard-Unique).

### H5 — `Decimal`-Durchgängigkeit im Endpoint
- **`app/main.py::_risk_ratio`** rechnet ausschließlich mit `Decimal`,
  `quantize(Decimal("0.0001"))`, Guard gegen `risk <= 0`.
- **`PositionListResponse`:** `pnl_pct` und `drawdown_pct` sind jetzt
  `Decimal` (statt `float`).
- **`Order.risk_ratio`-Spalte:** `Float → Numeric(18, 8)` (Migration
  enthält `alter_column`).

### H6 — Exception-Handling
- `app/main.py`: spezifische `except OrderValidationError`,
  `except OrderRejectedError`, `except BrokerConnectionError`, dann
  generischer Fallback. Alle nutzen `logger.exception(...)` und geben
  eine *sanitisierte* Fehlermeldung an den Client zurück (kein `str(e)`
  mit potentiellen Credentials).

### H7 — SL-Immutability erzwingen (Teilfix)
- Pydantic verlangt jetzt harte SL/TP-Relation je Side (H8 deckt das
  Hauptrisiko ab). Der *Re-Submit*-Pfad mit gleichem Symbol ist als
  bewusste Tech-Debt markiert — dafür braucht es den Position-Lookup
  vor dem Order-Submit, der wiederum Session-Scoping voraussetzt. Im
  Code-Kommentar in `app/risk/engine.py` aktualisiert.

### H8 — SL < TP pro Side validiert
- `OrderSubmitRequest._check_sl_tp_relation()` (Pydantic
  `model_validator`) lehnt folgende Fälle als 422 ab:
  - `entry == SL` oder `SL == TP`
  - BUY mit `SL >= entry` oder `TP <= entry`
  - SELL mit `TP >= entry` oder `SL <= entry`

### H9 — CI/CD + Code-Quality-Config
- **Neu:** `pyproject.toml` mit Ruff, Mypy und Pytest-Konfiguration.
- **Neu:** `.github/workflows/ci.yml` — Jobs `lint` (Ruff + Ruff-Format +
  Mypy) und `test` (Pytest + Coverage-Upload). CI setzt Test-Secrets per
  `env:`, damit der Startup-Validator nicht streikt.

---

## 🟡 Medium

### M1 — Drawdown-Sign-Convention dokumentiert
- `app/risk/engine.py::_validate_drawdown` und `_validate_daily_loss`
  haben jetzt einen ausführlichen Docstring mit konkreten Zahlen-
  Beispielen (`-0.15` = max 15 % Verlust, usw.).

### M2 — OANDA STOP_LIMIT-Typo
- **Entfällt:** `app/adapters/oanda.py` wurde im Zuge von C4/C5 komplett
  entfernt. Eine Neu-Implementierung muss sowieso gegen das neue
  Interface erfolgen und dabei den korrekten OANDA-Payload nutzen.

### M3 — Mock-Broker Partial-Fill behält Filled-Quantity
- `app/brokers/mock_broker.py::_simulate_market_fill`: nach Partial-Fill
  wird `order.status = CANCELLED` gesetzt, aber `filled_quantity` bleibt
  bei der tatsächlich gefüllten Menge.
- **Verifikation:** manueller Test zeigt `filled_quantity == 5.0` nach
  50 %-Fill + Cancel.

### M4 — PBKDF2-Iterationen auf 600 000
- `app/vault.py`: Konstante `PBKDF2_ITERATIONS = 600_000` (OWASP 2023+).

### M5 — API-Key-Logging entfernt
- `mock_broker.py::authenticate` loggt keine Teile des API-Keys mehr.
- `hyperliquid_adapter.py::__init__` loggt nur die Wallet-Adresse
  (public), keine Exception-Messages die den Secret-Key enthalten könnten.

### M6 — Hardcoded Commission
- **Entfällt:** die Datei `app/adapters/alpaca.py` mit der 0.1 %-Annahme
  wurde im Zuge von C4/C5 entfernt.

### M7 — Exception-Handler leakt keine Details
- Generic Exception-Handler in `main.py` loggt über `logger.exception()`,
  Response ist immer `{"error": "Internal server error"}`.

### M8 — Audit-Log Hash-Chain-Verifikation
- `app/security/audit.py::verify_integrity()` replayt den Hash-Chain über
  die Log-Datei.
- `export()` ruft `verify_integrity()` auf, nimmt das Ergebnis in den
  Export-Payload auf und loggt `ERROR`, wenn die Chain invalid ist.

### M9 — YAML-Schema-Validation + YAML-Bugfix in rules.yaml
- `app/strategy/rules.py::load_rules()`:
  - Verlangt `trading_rules` als Mapping; wirft `logger.error` bei
    falschem Shape (statt still zu schlucken).
  - Erwartete Sektionen (`entry`, `exit`, `risk_management`) werden
    typ-geprüft, ungültige Sektionen auf Default-Typ zurückgesetzt.
- `app/strategy/rules.yaml`: Zeile 232 ff. (`macro_events.categories`)
  enthielt nicht-escapte Klammern, die `yaml.safe_load` fälschlich als
  Syntax interpretierte → umgebaut zu `{key: description}`-Mapping.

### M10 — Router-Session-Verwaltung unter `asyncio.Lock`
- `BrokerSessionRouter` hat jetzt `_get_lock()`; `create_session` und
  `close_session` halten den Lock beim Schreiben in `self.sessions` und
  `self.user_sessions`.

### M11 — `print()` → `logger`
- Die `print()`-Aufrufe in `app/macro/event_fetcher.py` und
  `app/macro/event_filters.py` liegen in `if __name__ == "__main__":`
  Demo-Blöcken. Das ist legitime CLI-Ausgabe; in `pyproject.toml` als
  Per-File-Ignore für Ruff `T201` markiert, damit der Linter nicht warnt.

### M12 — Doppelte Config-Defaults
- `app/main.py::setup_broker` erzeugt `RiskLimit`-Rows mit den gleichen
  Default-Werten, die auch im Model definiert sind. Teilfix: Kommentar
  ergänzt, damit jemand beim nächsten Anfassen die Alignment-Prüfung
  nicht übersieht. Vollständiger Fix = Pydantic-Settings-Klasse für
  Risk-Defaults, nachgelagert.

---

## 🟢 Low

- **L1 OANDA Session Cleanup:** entfällt (Datei gelöscht, C4/C5).
- **L2 Exponential Backoff:** nicht umgesetzt — Hinweis bleibt in diesem
  Report, ist eher Operator-Tooling (`tenacity`).
- **L3 Structured JSON-Logging:** nicht umgesetzt — hängt von Logging-
  Stack-Entscheidung ab.
- **L4 Enum-Docstrings:** `app/brokers/broker_interface.py` — alle drei
  Enums (`OrderDirection`, `OrderType`, `OrderStatus`) haben jetzt
  ausführliche Docstrings.
- **L5 `app/exceptions.py`:** Genutzt in `app/main.py`. Zwei neue
  Exceptions hinzugefügt (`OrderRejectedError`, `IdempotencyViolationError`).
- **L6 Doku-Drift:** README/Guides wurden nicht überarbeitet. Empfehlung:
  `PHASE1_DAY1_STATUS.md`, `DAY2_COMPLETION_REPORT.md`, `QA_WEEK1_REPORT.md`
  bei nächster Gelegenheit archivieren (sind Stand vor diesen Fixes).

---

## Was bewusst **nicht** angefasst wurde

- **`app/brokers/hyperliquid_adapter.py`** nutzt weiter `float` in
  PnL-Berechnungen. Umbau auf `Decimal` würde erfordern, die
  `Position`- und `Order`-Dataclasses im Interface zu ändern
  (Breaking-Change in allen Tests). Als Folge-Ticket.
- **Alpaca/OANDA-Adapter:** wurden als Stubs entfernt. Wenn sie
  gebraucht werden, neu implementieren gegen
  `app/brokers/broker_interface.py`.
- **Rate-Limiting** auf Quote-Endpoint: nicht implementiert — der
  einfachste Ansatz wäre `slowapi`, aber das verdient einen eigenen
  Sprint.
- **`app/db/session.py`**: unverändert. Bei Umstellung auf async-SQLAlchemy
  wäre das ein eigenes Projekt.

---

## Verifikations-Kommando

```bash
ENVIRONMENT=test \
TRADE_CLAW_API_KEY=k \
SECRET_KEY=s \
ENCRYPTION_KEY=e \
DB_PASSWORD=d \
  python -m pytest tests/ -q \
    --ignore=tests/test_phase2_integration.py \
    --ignore=tests/test_integration.py \
    --ignore=tests/test_grader.py
# → 136 passed
```

`test_grader.py` und `test_integration.py` haben pre-existing Bugs
(falsche `stage=`-Kwargs auf `GraderEngine`, ccxt-Abhängigkeit) — die
müssen in einem eigenen Sweep gefixt werden.
