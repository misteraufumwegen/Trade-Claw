# Code Review: Trade-Claw

**Reviewer:** Claude (automated review)
**Datum:** 2026-04-15
**Umfang:** ~9.400 LOC (app/) + ~4.900 LOC (tests/), 47 Module
**Repo-Stand:** commit im Working Directory (nicht gegen einen spezifischen PR)

---

## Summary

Trade-Claw ist eine ambitionierte FastAPI-basierte Multi-Broker-Trading-Plattform (Alpaca, OANDA, Hyperliquid, Mock) mit Risk Engine, Vault, Audit-Log, Backtesting und ML-Grader. Die Grundstruktur ist solide, aber es gibt erhebliche Probleme, die **vor jedem Live-Deployment** behoben werden müssen.

**Verdict: 🟠 Request Changes** — nicht produktionsreif. Sandbox/Paper-Trading OK nach Fixes der High-Findings.

| Severity | Count |
|----------|-------|
| 🔴 Critical | 6 |
| 🟠 High | 9 |
| 🟡 Medium | 12 |
| 🟢 Low | 6 |

Die drei größten Baustellen:
1. **Keine Authentifizierung** auf kritischen Endpoints (Orders, Vault, Audit-Log).
2. **Architektur-Duplizierung**: Zwei parallele Broker-Interfaces + zwei Adapter-Verzeichnisse.
3. **Broker-Adapter unvollständig**: `app/brokers/alpaca_adapter.py` und `oanda_adapter.py` sind nur TODO-Stubs.

> **Hinweis zur Verifikation:** Zwei Findings aus meinen ersten Analysepass waren Fehlinterpretationen:
> – `app/risk/engine.py:215` (`current_drawdown < max_drawdown_threshold`): Ist **korrekt**, wenn Drawdowns negativ kodiert sind (`-0.15` = 15% max Verlust). Bleibt aber als 🟡 Medium drin, weil die Sign-Convention nirgends dokumentiert ist und leicht missverständlich ist.
> – `app/main.py:386` Division-by-zero: Der Guard `if request.entry_price != request.stop_loss` schützt bereits korrekt. Kein Bug.

---

## 🔴 Critical Findings

### C1 — Keine Authentifizierung auf Order-Endpoints
**Datei:** `app/main.py:302, 466, 522`
**Problem:** `/api/v1/orders/submit`, `/api/v1/orders/{id}/cancel`, `/api/v1/brokers/setup` sind **nicht authentifiziert**. Jeder mit Netzwerkzugriff und einer `session_id` kann Orders platzieren, canceln, und Broker-Credentials registrieren. Die `.env.example` enthält zwar `JWT_SECRET`/`JWT_ALGORITHM` — aber die Implementierung fehlt komplett.
**Fix:** FastAPI `Depends(HTTPBearer())` + JWT-Validierung vor jedem state-ändernden Endpoint. Session-IDs müssen aus dem JWT-Claim kommen, nicht aus Query-Parametern.

### C2 — Hardcoded Default-Secrets in `docker-compose.yml`
**Datei:** `docker-compose.yml:9, 48`
**Problem:**
```yaml
POSTGRES_PASSWORD: ${DB_PASSWORD:-trading_password}
SECRET_KEY: ${SECRET_KEY:-change-me-in-production}
```
Fallback-Defaults bedeuten: wenn jemand ohne `.env` startet, läuft Produktion mit `change-me-in-production`. Das ist ein klassischer Weak-Default-Fehler.
**Fix:** Defaults entfernen. Startup-Check im Entrypoint, der abbricht, wenn `SECRET_KEY`, `DB_PASSWORD`, `ENCRYPTION_KEY`, `JWT_SECRET` nicht gesetzt oder auf Platzhalter-Werten sind.

### C3 — Vault speichert Credentials nur im RAM
**Datei:** `app/vault.py:86`
**Problem:** `self.storage: Dict[str, str] = {}` — nach Restart sind alle verschlüsselten Broker-Credentials weg. In einem Multi-Broker-Setup, wo Sessions persistent sein sollen, bricht damit jede Session nach Neustart.
**Fix:** Storage-Backend ist ein Interface (DB-Tabelle mit `encrypted_blob BYTEA`, Redis, oder HashiCorp Vault). Der aktuelle In-Memory-Store ist nur für Tests brauchbar.

### C4 — Zwei konkurrierende Broker-Interfaces nebeneinander
**Dateien:** `app/interfaces/broker.py` ↔ `app/brokers/broker_interface.py`
**Problem:**
- `interfaces/broker.py`: `OrderSide` mit `"buy"/"sell"` (lowercase), `Trade`-Dataclass
- `brokers/broker_interface.py`: `OrderDirection` mit `"BUY"/"SELL"` (uppercase), `Account`-Dataclass
- Unterschiedliche Field-Namen in `Position` (`entry_price` vs `average_price`)

Tests importieren aus beiden (`test_adapters.py` → `interfaces/`, `test_brokers.py` → `brokers/`). Bei jedem Import/Wrapper-Mix besteht die Gefahr von stillschweigenden Bugs.
**Fix:** **Vor allem anderen** konsolidieren. Vorschlag: `app/interfaces/broker.py` als Single Source of Truth, `app/brokers/broker_interface.py` löschen, alle Adapter migrieren.

### C5 — Alpaca- und OANDA-Adapter in `app/brokers/` sind TODO-Stubs
**Dateien:** `app/brokers/alpaca_adapter.py:40,66,95,109,114,119`, `app/brokers/oanda_adapter.py:41,…`
**Problem:**
```python
async def submit_order(self, ...) -> str:
    # TODO: Implement order submission
    raise NotImplementedError
```
Sechs `TODO: Implement …`-Marker in Alpaca, vier in OANDA. Tests mocken diese komplett — ein Live-Call würde sofort `NotImplementedError` werfen.
**Fix:** Entweder diese Dateien löschen (die *funktionierenden* Adapter liegen ohnehin in `app/adapters/alpaca.py` und `app/adapters/oanda.py`), oder fertig implementieren. Aktuell sind sie Dead Code mit TODO-Falle.

### C6 — Race Condition bei Hyperliquid-Nonce
**Datei:** `app/brokers/hyperliquid_adapter.py:104, 216, 379`
**Problem:**
```python
self.nonce = 0
...
self.nonce += 1   # nicht atomar in async
```
Bei zwei gleichzeitigen `submit_order`-Calls können beide denselben `nonce` lesen → EIP-712-Signatur wird dupliziert → doppelte Orders oder Replay-Risiko.
**Fix:**
```python
import asyncio
self._nonce_lock = asyncio.Lock()

async def _next_nonce(self) -> int:
    async with self._nonce_lock:
        # Besser: millisecond-based + counter, damit auch nach Restart monoton
        self.nonce = max(self.nonce + 1, int(time.time() * 1000))
        return self.nonce
```

---

## 🟠 High Findings

### H1 — Kein CORS-Middleware registriert
**Datei:** `app/main.py:29-35`
`CORS_ORIGINS` steht in der `.env.example` (Zeile 62) aber `app.add_middleware(CORSMiddleware, ...)` wird nie aufgerufen. Ein Frontend kann die API nicht sauber nutzen, und es gibt keinen Origin-Schutz.

### H2 — `OrderSubmitRequest = None` Default ist broken
**Datei:** `app/main.py:305`
```python
async def submit_order(
    session_id: str = Query(...),
    request: OrderSubmitRequest = None,   # ← verhindert automatische Body-Validation
    db: Session = Depends(get_db_session),
):
```
FastAPI sieht hier einen optionalen Body — leerer POST-Request kommt mit `request=None` durch und crasht danach an `request.symbol`. Fix: `request: OrderSubmitRequest` (kein Default).

### H3 — Pydantic-Felder ohne Validation
**Datei:** `app/main.py:46-50, 78-86`
- `BrokerSetupRequest.credentials: dict` — komplett freies Dict, keine Whitelist pro Broker → leicht ausnutzbar.
- `OrderSubmitRequest` — `symbol: str` ohne Regex; `size/entry_price/stop_loss/take_profit: Decimal` ohne `gt=0`. `size=Decimal("-1")` wird akzeptiert.
**Fix:** Pro Broker ein strikter Schema-Typ (`AlpacaCredentials`, `OandaCredentials` …), und `Field(gt=0)` auf allen numerischen Feldern.

### H4 — Keine Idempotenz bei Order-Submission
**Datei:** `app/api/order_api_adapter.py:150`, `app/main.py:366-373`
Bei Netzwerk-Timeout nach `adapter.submit_order(...)` hat der Client keinen Weg zu wissen, ob die Order durchging. Ein Retry erzeugt eine zweite Order.
**Fix:** Client-generierten Idempotenz-Key (UUID) im Request mitgeben, in DB als UNIQUE-Index, und in der Broker-Adapter-Map cachen.

### H5 — Float statt `Decimal` in PnL-Berechnungen
**Dateien:**
- `app/brokers/hyperliquid_adapter.py:423` — `pnl = (current_price - avg_price) * qty` (floats)
- `app/adapters/alpaca.py:160` — `entry_price = current_price * 0.98` (float)
- `app/adapters/oanda.py:183` — analog

Die Endpoints arbeiten mit `Decimal`, aber die Broker-Adapter rechnen intern mit float zurück. Rundungsfehler akkumulieren sich über viele Trades.
**Fix:** `Decimal`-Durchgängigkeit bis in die Adapter. CCXT/OANDA liefern Strings → `Decimal(str(x))`.

### H6 — Broad `except Exception` verschluckt Fehler (65 Stellen)
**Datei:** u.a. `app/adapters/broker_manager.py:66-73`
```python
except Exception as e:
    logger.error(f"Failed to connect {broker_name}: {str(e)}")
    results[broker_name] = False
```
`KeyboardInterrupt`/`SystemExit` werden in Python 3.x nicht mehr erfasst, aber trotzdem werden `AuthenticationError`, `ValueError`, `TimeoutError` in einen Topf geworfen. Außerdem `str(e)` ohne `exc_info=True` → keine Stack-Traces.
**Fix:** Spezifische Exceptions fangen, `logger.exception(...)` oder `logger.error(..., exc_info=True)`.

### H7 — Fehlende Stop-Loss-Immutability
**Datei:** `app/risk/engine.py:120`
```python
# 5. Validate Stop Loss Immutability (check if order exists)
# This is enforced at API level - cannot move SL after order creation
```
Dieser Kommentar behauptet eine Garantie, die **nirgends im Code** eingelöst wird. Der Nutzer kann über einen neuen Order-Submit mit gleichem Symbol den effektiven SL verschieben.
**Fix:** Before `validate_order`: Existierende offene Position/Order abfragen, bei Konflikt blockieren.

### H8 — Kein Stop-Loss < Take-Profit-Check
**Datei:** `app/api/order_api_adapter.py:238-249`
Wird für BUY geprüft, dass SL < entry < TP — aber nicht ob SL < TP direkt. Bei eigentümlichen Inputs (z.B. SL=100, TP=50, Entry=75) kommen ungültige Orders durch.

### H9 — Kein CI/CD und kein Code-Quality-Enforcement
**Dateien:** kein `.github/workflows/`, kein `pyproject.toml`, kein `.pre-commit-config.yaml`, kein Ruff/Black/mypy
Bei einem Trading-System ist jede ungetestete Änderung ein Risiko. Ohne PR-Tests wird Drift unvermeidlich.
**Fix:** Minimal eine GitHub-Action mit `pytest`, `ruff check`, `mypy app/`.

---

## 🟡 Medium Findings

| # | Datei:Zeile | Finding |
|---|-------------|---------|
| M1 | `app/risk/engine.py:215,239` | Sign-Convention von `current_drawdown_pct`/`max_drawdown_pct` ist nirgends dokumentiert. Der Code ist *korrekt*, wenn beide negativ sind, aber lies­bar ist er nicht. Refactor zu `abs(current_loss) > abs(max_loss_allowed)` mit klaren Namen. |
| M2 | `app/adapters/oanda.py:307-310` | `STOP_LIMIT` wird an OANDA als `type="STOP"` mit `triggerDistance` gesendet. OANDA-API erwartet aber `STOP_LIMIT` mit `triggerPrice` + `price`. Funktioniert so nicht. |
| M3 | `app/brokers/mock_broker.py:153-165` | Nach Partial-Fill wird `filled_quantity = 0` gesetzt statt den teilgefüllten Wert zu behalten → Backtest-Zahlen falsch. |
| M4 | `app/vault.py:120` | PBKDF2-Iterationen=100.000. OWASP 2026 empfiehlt 600k+ für SHA-256; Argon2id wäre besser. |
| M5 | `app/brokers/mock_broker.py:76` | `logger.info(f"Mock broker authenticating with key={self.api_key[:8]}...")` — auch 8-Zeichen-Prefix eines API-Keys ist PII. |
| M6 | `app/adapters/alpaca.py:299` | Hardcoded `commission = cost * 0.001` ("Assume 0.1%"). Muss aus Alpaca-Response oder Config kommen. |
| M7 | `app/main.py:637-653` | Generic Exception-Handler loggt `str(exc)` — kann sensitive Daten durchreichen. `logger.exception()` würde Trace loggen, Response bleibt generic. |
| M8 | `app/security/audit.py:151-168` | Audit-Log hat Hash-Chain zur Tamper-Detection, aber **beim Lesen wird die Chain nie validiert**. `verify_chain()`-Methode und Integrations-Check im Export fehlen. |
| M9 | `app/strategy/rules.py:45-46` | `yaml.safe_load(f)` ist gut — aber das Ergebnis wird nicht gegen ein Pydantic-Schema validiert. Malformed `rules.yaml` → Runtime-Crash. |
| M10 | `app/routing/broker_session_router.py:144-145` | Schreiben in `self.sessions[session_id]` und `self.user_sessions[user_id]` ohne `asyncio.Lock`. Bei parallelen Setup-Calls möglich, dass eine Session sofort überschrieben wird. |
| M11 | `app/macro/event_fetcher.py:377-394`, `app/macro/event_filters.py:317-340` | **20 `print()` statt `logger`** in Produktions-Code. |
| M12 | `app/main.py` + `app/db/models.py` | Doppelte Defaults: Risk-Limits einmal hardcoded im Endpoint-Code (`max_position_size_pct=0.10`), einmal in Model-Defaults. Bei Divergenz entsteht Chaos. |

---

## 🟢 Low Findings

- **L1** `app/adapters/oanda.py:85-102` — Session-Cleanup bei späterem Fehler fehlt (kein `finally`).
- **L2** Alle Broker-Adapter — kein Exponential-Backoff-Retry (siehe `tenacity`).
- **L3** Logs sind plaintext, nicht JSON-strukturiert — erschwert Aggregation (Datadog/Loki).
- **L4** `app/interfaces/broker.py:13-38` — Enums ohne Docstrings.
- **L5** `app/exceptions.py` existiert, wird aber nirgends importiert → Dead Code.
- **L6** Doku-Drift: `PRODUCTION_GUIDE.md` spricht von "Phase 3", Code ist "Phase 4" (`app/main.py:32`). README-Abschnitt "Next Steps" listet schon gemachte Arbeit als TODO.

---

## Test-Coverage Mapping

| Modul | Tests vorhanden? | Anmerkung |
|-------|------------------|-----------|
| `app/risk/engine.py` | ✅ 20 Tests | Gut |
| `app/vault.py` | ✅ 31 Tests | Gut |
| `app/ml/grader.py` | ✅ 21 Tests | Gut |
| `app/strategy/unal_strategy.py` | ✅ 36 Tests | Gut |
| `app/db/models.py` | ✅ 14 Tests | Gut |
| `app/adapters/*` | ⚠️ Nur Mocks (`test_adapters.py`) | Keine echten API-Integrations |
| `app/brokers/mock_broker.py` | ✅ `test_brokers.py` | Gut |
| `app/brokers/alpaca_adapter.py` | ❌ Nichts — und Stub | siehe C5 |
| `app/brokers/oanda_adapter.py` | ❌ Nichts — und Stub | siehe C5 |
| `app/brokers/hyperliquid_adapter.py` | ❌ Keine Tests | — |
| `app/api/order_api_adapter.py` | ⚠️ Nur indirekt über `test_integration.py` | |
| `app/macro/event_fetcher.py` | ❌ Keine Tests | |
| `app/macro/event_filters.py` | ❌ Keine Tests | |
| `app/correlation/engine.py` | ❌ Keine Tests | |
| `app/backtest/simulator.py` | ❌ Keine Tests | Lookahead-Bias-Check fehlt |
| `app/routing/broker_session_router.py` | ⚠️ Teilweise | |
| `app/security/audit.py` | ❌ Keine Tests | kritisch für Compliance |
| `app/main.py` Endpoints | ⚠️ 16 Tests in `test_endpoints.py` | unvollständig |

**Gesamteindruck:** ~52 % der Module haben eigene Tests. Edge-Cases (negative Prices, leere Symbols, Netzwerk-Timeouts, Concurrency) sind **sehr** unterrepräsentiert. `asyncio.sleep(0.2)` in vier Test-Files → mögliche Flakiness auf langsamen CI-Runnern.

---

## Was gut aussieht

- **Saubere Modularisierung**: `risk/`, `strategy/`, `backtest/`, `ml/` sind klar getrennt.
- **Audit-Log mit Hash-Chain** (`app/security/audit.py`) — gute Idee, braucht nur den Verification-Pfad.
- **Pydantic-Schemas** durchgängig für API-I/O.
- **`yaml.safe_load`** korrekt verwendet (nicht das unsichere `yaml.load`).
- **Keine Credentials im Git-Log** (kurz geprüft, `.env` ist sauber in `.gitignore`).
- **Decimal für User-facing Preise** in den Endpoint-Schemas (nur intern wird teilweise zu float gewechselt → H5).
- **Docker-Healthchecks** für Postgres und Redis vorhanden.

---

## Empfohlene Reihenfolge der Fixes

### Sprint 1 — Bevor irgendetwas in Richtung Live/Paper-Trading geht:
1. **C1**: Auth auf allen `POST /api/v1/*` und sensiblen `GET`-Endpoints.
2. **C2**: Hardcoded Fallback-Secrets aus `docker-compose.yml` entfernen, Startup-Check.
3. **C4**: Dual-Interface-Konflikt lösen. Eine Wahrheit.
4. **C5**: Stub-Adapter entfernen oder fertigstellen.
5. **H2**: `OrderSubmitRequest = None` korrigieren.
6. **H3**: Pydantic-Validation (`gt=0`, Regex auf Symbol).

### Sprint 2:
7. **C3**: Vault persistent machen.
8. **C6**: Hyperliquid-Nonce-Lock.
9. **H1**: CORS-Middleware.
10. **H4**: Idempotenz-Keys.
11. **H5**: Decimal-Durchgängigkeit.
12. **H9**: CI + Ruff/mypy.

### Sprint 3 — Tech Debt:
13. M1–M12 abarbeiten, Coverage der ungetesteten Module erhöhen, `backtest/simulator.py` auf Lookahead prüfen.

---

## Verdict

**🟠 Request Changes.** Die Architektur ist gut gedacht, aber im aktuellen Zustand:
- öffentlich über HTTP erreichbar = sofortiger Exploit-Weg (C1),
- Restart-Verlust aller Credentials (C3),
- zwei parallele Broker-APIs, von denen eine nur Stubs enthält (C4 + C5).

Nach den Sprint-1-Fixes sehe ich keinen Blocker mehr für Sandbox/Paper-Trading. Echtes Kapital würde ich erst nach Sprint 2 + vollständiger Adapter-Integration + echten End-to-End-Tests gegen Broker-Sandboxes anfassen.
