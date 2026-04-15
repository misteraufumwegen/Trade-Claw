# Trading Bot - Production Deployment Guide

**Version:** 3.0 (Phase 3 — Live Trading Ready)
**Status:** ✅ Production Ready
**Last Updated:** 2026-04-15

---

## Overview

The Trading Bot is a **multi-broker, fully-automated trading system** with:
- ✅ Ünal's complete trading strategy (80% win-rate, 12.42x profit factor)
- ✅ Real-time macro-events integration (worldmonitor.app)
- ✅ Flexible asset correlation engine (Gold, Silver, EUR/USD, BTC, etc.)
- ✅ Risk management (10% position cap, -15% drawdown halt, immutable stop-loss)
- ✅ Live broker connectivity (Alpaca, OANDA)

---

## Quick Start (Production)

### 1. Prerequisites

- **Docker Desktop** (macOS/Windows) or **Docker + Compose** (Linux)
- **Broker Account** (Alpaca or OANDA) with Live or Paper trading credentials
- **3-5 minutes** to set up

### 2. Clone Repository

```bash
git clone https://github.com/misteraufumwegen/Trade-Claw.git
cd Trade-Claw
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Broker: Choose one (ALPACA or OANDA)
TRADING_BROKER=ALPACA

# Alpaca (Paper or Live)
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
# ALPACA_BASE_URL=https://api.alpaca.markets      # Live trading

# OANDA (Paper or Live)
# OANDA_API_KEY=your_oanda_key
# OANDA_ACCOUNT_ID=your_oanda_account
# OANDA_BASE_URL=https://api-fxpractice.oanda.com  # Paper
# OANDA_BASE_URL=https://api-fxtrade.oanda.com     # Live

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trading_bot
REDIS_URL=redis://localhost:6379

# Risk Management (Default: Ünal's settings)
MAX_POSITION_SIZE_PCT=10          # 10% of account per trade
MAX_DRAWDOWN_PCT=15               # -15% emergency halt
```

### 4. Start Services

```bash
docker-compose up -d
```

Verify:
```bash
curl http://localhost:8000/api/health
# Response: {"status":"healthy","service":"trading-bot-api"}
```

### 5. View Dashboard

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Production Operations

### Daily Operations Checklist

**Morning (before market open):**

```bash
# 1. Health Check
curl http://localhost:8000/api/health

# 2. View Active Positions
curl http://localhost:8000/api/positions

# 3. Check Risk Engine Status
curl http://localhost:8000/api/risk/status

# 4. View Macro Events (today)
curl "http://localhost:8000/api/macro/events?days=1"
```

**During Trading:**

```bash
# Monitor live trades
curl http://localhost:8000/api/trades/active

# Check correlation alignment
curl -X POST http://localhost:8000/api/correlation/analyze \
  -H "Content-Type: application/json" \
  -d '{"assets": ["GLD", "SLV", "EUR/USD"], "threshold": 0.7}'

# View backtest metrics (post-trade)
curl http://localhost:8000/api/backtest/metrics
```

**End of Day:**

```bash
# Export daily report
curl http://localhost:8000/api/reports/daily > daily_report.json

# Check drawdown status
curl http://localhost:8000/api/risk/drawdown
```

---

## REST API Endpoints

### Trading

```
GET  /api/trades/active          — Current open positions
GET  /api/trades/{trade_id}      — Specific trade details
POST /api/trades/execute         — Place new trade
PUT  /api/trades/{trade_id}      — Update trade (SL/TP)
DELETE /api/trades/{trade_id}    — Close trade
```

### Strategy & Grading

```
POST /api/strategy/grade         — Grade a setup (A+/A/B)
GET  /api/strategy/rules         — View active rules
POST /api/strategy/backtest      — Run backtest on trade list
```

### Risk Management

```
GET  /api/risk/status            — Overall risk status
GET  /api/risk/limits            — View risk limits (10%, -15%)
GET  /api/risk/drawdown          — Current drawdown %
POST /api/risk/halt-all          — Emergency: Close all trades
```

### Macro Events

```
GET  /api/macro/events           — Live macro events (last 24h)
GET  /api/macro/events?days=7    — Events (last 7 days)
GET  /api/macro/calendar         — Upcoming events (next 7 days)
```

### Correlation Engine

```
POST /api/correlation/analyze    — Analyze multi-asset correlation
GET  /api/correlation/assets     — Available assets for correlation
POST /api/correlation/score      — Score a trade by correlation
```

### Health & Status

```
GET  /api/health                 — Service health
GET  /api/status                 — Detailed status (broker, DB, Redis)
GET  /api/positions              — Current account positions
GET  /api/reports/daily          — Daily P&L report
```

---

## Configuration

### Risk Engine (Immutable)

**These settings are hardcoded and CANNOT be changed during live trading:**

```python
MAX_POSITION_SIZE = 10%           # Maximum position size per trade
MAX_DRAWDOWN_HALT = -15%          # Automatic emergency halt threshold
STOP_LOSS_IMMUTABLE = True        # Once set, SL cannot be moved
```

**Why immutable?** Protects against emotional trading and catastrophic losses.

### Asset Correlation (Flexible)

Choose any combination of assets for correlation analysis:

```json
{
  "assets": ["GLD", "SLV", "EUR/USD", "BTC", "SPY"],
  "threshold": 0.7,
  "lookback_days": 30
}
```

**Available assets:**
- Commodities: GLD, SLV, USO
- Forex: EUR/USD, GBP/USD, USD/JPY, AUD/USD
- Crypto: BTC, ETH, XRP
- Stocks: SPY, QQQ, IWM
- Index: VIX

---

## Monitoring & Alerts

### Log Files

```bash
# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f db

# View Redis logs
docker-compose logs -f redis
```

### Metrics

The bot exports metrics to `/api/metrics`:

```bash
curl http://localhost:8000/api/metrics
```

**Key metrics:**
- `trades_executed_total` — Cumulative trades
- `win_rate_pct` — Current win rate
- `profit_factor` — Gross profit / gross loss
- `drawdown_pct` — Current drawdown
- `open_positions` — Active trade count

### Error Handling

**Critical Errors (auto-halt):**
- Drawdown exceeds -15% → All trades closed automatically
- API connection loss → Retry 3x, then manual intervention required
- Database connection loss → API enters read-only mode

**To manually halt all trades:**
```bash
curl -X POST http://localhost:8000/api/risk/halt-all
```

---

## Deployment Scenarios

### Scenario 1: Paper Trading (Sandbox)

**Best for:** Testing, learning, validation

```env
TRADING_BROKER=ALPACA
ALPACA_BASE_URL=https://paper-api.alpaca.markets
MAX_ACCOUNT_SIZE=100000    # Start with $100k virtual
```

### Scenario 2: Small Live (25% of Capital)

**Best for:** Risk-controlled live trading

```env
TRADING_BROKER=ALPACA
ALPACA_BASE_URL=https://api.alpaca.markets
MAX_ACCOUNT_SIZE=10000     # Start with $10k real capital
```

### Scenario 3: Full Live (100%)

**Best for:** After Phase 2 validation

```env
TRADING_BROKER=ALPACA
ALPACA_BASE_URL=https://api.alpaca.markets
MAX_ACCOUNT_SIZE=100000    # Full account
```

---

## Troubleshooting

### Issue: "Connection refused on port 8000"

```bash
# Check if container is running
docker-compose ps

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Issue: "Broker authentication failed"

```bash
# Verify credentials in .env
cat .env | grep ALPACA_API_KEY

# Test connection manually
curl -H "Authorization: Bearer YOUR_KEY" https://paper-api.alpaca.markets/v2/account
```

### Issue: "Database migration failed"

```bash
# Reset migrations
docker-compose exec db psql -U postgres -c "DROP DATABASE trading_bot;"
docker-compose down
docker-compose up -d --build
```

### Issue: "Drawdown halted all trades"

```bash
# Check drawdown status
curl http://localhost:8000/api/risk/drawdown

# Review trades that triggered halt
curl http://localhost:8000/api/reports/daily

# Manual resume (after review)
curl -X POST http://localhost:8000/api/risk/resume
```

---

## Advanced Usage

### Running Backtests

```bash
curl -X POST http://localhost:8000/api/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "trades": [
      {
        "symbol": "GLD",
        "entry": 195.75,
        "stop_loss": 193.25,
        "tp1": 199.50,
        "tp2": 201.30,
        "grade": "A+"
      }
    ],
    "starting_capital": 10000,
    "only_grades": ["A+", "A"]
  }'
```

### Custom Risk Limits (Development Only)

To override risk limits (dev/testing only):

```bash
# DANGEROUS: Only in paper trading!
curl -X POST http://localhost:8000/api/risk/override \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"max_position_pct": 15}'
```

### Export Historical Data

```bash
# Export last 30 days of trades
curl "http://localhost:8000/api/reports/trades?days=30" > trades_30d.json

# Export correlation analysis history
curl "http://localhost:8000/api/correlation/history?days=30" > correlation_history.json
```

---

## Support & Debugging

**Still having issues?**

1. Check logs: `docker-compose logs -f`
2. Verify broker connection: `curl https://paper-api.alpaca.markets/v2/account`
3. Test database: `docker-compose exec db psql -U postgres -l`
4. Contact: Use `/api/status` for full system diagnostics

---

## Phase Roadmap

| Phase | Status | Features |
|-------|--------|----------|
| Phase 1 | ✅ | Scaffolding, Brokers, Vault |
| Phase 2 | ✅ | Grader, Backtest, Risk Engine |
| Phase 2b | ✅ | Live Strategy, Macro Events |
| Phase 3 | ✅ | Correlation Engine, Fixes |
| Phase 4 | 🟢 Ready | Live Trading 25% |
| Phase 5 | Planned | Full Live + Dashboard |

---

**Ready to trade? Start with `docker-compose up -d` and check `/docs`!** 🚀
