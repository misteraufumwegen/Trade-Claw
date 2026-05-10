# Trade-Claw — Trading Bot

A multi-broker trading platform built with FastAPI + a self-contained React UI.
Single-user, runs locally on Windows and macOS. Brokers are registered via a
plugin system — Mock + Hyperliquid out of the box, ~111 exchanges via CCXT, and
anything else through the generic REST adapter. Paper-mode by default; live
trading is opt-in per session.

## Quick Start

The bundled launcher creates a Python venv on first run, installs dependencies,
starts the API, and opens the UI in your default browser.

- **Windows**: double-click `start-app.bat`
- **macOS**: double-click `start-app.command`
  (one-time on Mac: `chmod +x start-app.command` from a terminal)
- **Linux / any platform**: `python3 launcher.py`

The UI lives at `http://localhost:8000/app/`. The API lives at the same origin
under `/api/v1/...`. Stop the server with `Ctrl+C` in the launcher window.

> First-time-only setup: the launcher copies `.env.example` to `.env` if it
> does not exist. Edit `.env` and set a real `TRADE_CLAW_API_KEY`.

## Trading modes

- **Paper / Demo (default)** — connects to broker sandboxes (Alpaca paper,
  OANDA demo) or to the testnet (Hyperliquid). No real money moves.
- **Live** — only used when the broker setup wizard is explicitly switched to
  *Live*; you confirm twice before the session is created.

You can switch any time by reconfiguring the broker session from
*Settings → Neu konfigurieren* in the UI.

## Adding brokers

The plugin system lets you add brokers from the UI without writing code:

- **CCXT-Picker** — pick any of ~111 exchanges (Binance, Kraken, Coinbase,
  Bybit, OKX, KuCoin, Bitfinex, Alpaca, …)
- **Generic REST** — config-driven adapter for any HTTP-based broker
  (endpoints, auth, body templates) — no code, just JSON
- **Python plugin** — drop a `.py` file with a `register(registry)` function
  into `app/brokers/plugins/`

See **`docs/CUSTOM_BROKERS.md`** for details.

## Autopilot & TradingView

Trade-Claw kann TradingView-Alerts via Webhook automatisch in Orders
übersetzen. Pipeline: Payload → Grader → ML-Gate → Risk-Engine → Submit, mit
Master-Kill-Switch in der UI.

Ausführliche Schritt-für-Schritt-Anleitung inkl. Cloudflare-Tunnel,
Pine-Skript-Vorlage und JSON-Beispielen für Forex / Crypto / Edelmetalle:

→ **`docs/AUTOPILOT_SETUP.md`**
→ Pine-Vorlage: **`docs/trade_claw_alert.pine`**

## ML & self-learning

Phased rollout (see `docs/AUTOPILOT_SETUP.md` for the recommended workflow):

1. **Outcome logger** — every order's input features + outcome are persisted
2. **Pre-trade ML gate** — `ML_GATE_MODE=advisory` (default), `enforce`, or `off`
3. **Retrain** — `POST /api/v1/ml/retrain` batch-trains on accumulated WIN/LOSS outcomes and hot-swaps the checkpoint
4. **Bootstrap** — `POST /api/v1/ml/bootstrap` builds a synthetic dataset from yfinance OHLCV to avoid the cold-start problem
5. **Walk-Forward backtest** — `POST /api/v1/ml/walkforward` returns an honest OVERFIT / PROMISING / WEAK verdict

The bootstrap and retrain endpoints are also reachable from the *ML & Autopilot*
page in the UI.

## Project structure

```
Trade-Claw/
├── app/                            # FastAPI backend
│   ├── main.py                     # endpoints + lifespan tasks
│   ├── autopilot.py                # TradingView webhook state machine
│   ├── brokers/                    # adapters + plugin registry
│   ├── ml/                         # scorer, trainer, bootstrap, grader
│   ├── risk/                       # risk engine + Fernet vault
│   ├── correlation/, macro/        # additional modules
│   ├── security/                   # auth + env validation
│   └── db/                         # SQLAlchemy models
├── frontend/                       # React via CDN — no build step
│   ├── index.html, app.jsx, api.js, styles.css
├── docs/
│   ├── AUTOPILOT_SETUP.md          # TradingView + Cloudflare tunnel guide
│   ├── CUSTOM_BROKERS.md           # plugin / CCXT / REST broker registration
│   ├── trade_claw_alert.pine       # Pine strategy template
│   └── design/DESIGN_SYSTEM.md     # design tokens behind styles.css
├── ml_bot_phase1/                  # PyTorch model (input=20, hidden 64→32)
├── tests/                          # pytest suite
├── alembic/                        # DB migrations
├── checkpoints/                    # ML model checkpoints
├── launcher.py                     # cross-platform entry point
├── start-app.bat                   # Windows double-click
├── start-app.command               # macOS double-click
├── requirements.txt
├── pyproject.toml                  # ruff / mypy / pytest config
└── .env.example
```

## Configuration

Edit `.env` (created from `.env.example` on first run). Required values:

| Variable | Purpose |
|---|---|
| `TRADE_CLAW_API_KEY` | API auth (Bearer or X-API-Key header) |
| `SECRET_KEY` | App secret (any long random string) |
| `ENCRYPTION_KEY` | Fernet key for the broker-credentials vault |

Useful optionals: `ML_GATE_MODE`, `ML_THRESHOLD`, `TV_WEBHOOK_SECRET`,
`OUTCOME_POLL_SECONDS`, `DATABASE_URL` (defaults to SQLite),
`API_HOST`/`API_PORT`, `CORS_ORIGINS`, `LOG_LEVEL`/`LOG_FILE`.

## Development

```bash
# Run tests
pytest tests/ -v

# Lint + format check
ruff check app tests
ruff format --check app tests

# Type-check
mypy app
```

CI runs the same three steps on push and PR (`.github/workflows/ci.yml`).

## API reference

Once the launcher is running:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI schema:** http://localhost:8000/openapi.json

Key endpoint groups: `/api/v1/brokers/...`, `/api/v1/orders/...`,
`/api/v1/ml/...`, `/api/v1/autopilot`, `/api/v1/webhook/tradingview/{secret}`,
`/api/v1/halt`, `/api/v1/correlation/...`, `/api/v1/macro/...`.

## License

See `LICENSE`.
