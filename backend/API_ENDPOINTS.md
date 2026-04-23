# Trade-Claw Backend API Endpoints

## Overview
8 RESTful endpoints for real-time trading, order management, and backtesting.

---

## 1. GET /api/quotes
**Real-time quotes from OANDA or yfinance**

### Request
```
GET /api/quotes?instruments=EUR_USD,GBP_USD&source=auto
```

### Query Parameters
- `instruments` (required): Comma-separated instrument codes (e.g., EUR_USD,GBP_USD,USD_JPY)
- `source` (optional): Data source - `auto`, `oanda`, or `yfinance` (default: auto)

### Response (200 OK)
```json
{
  "quotes": [
    {
      "instrument": "EUR_USD",
      "bid": 1.0850,
      "ask": 1.0851,
      "time": "2026-04-23T18:04:00Z",
      "source": "oanda"
    }
  ],
  "status": "ok"
}
```

### Error Responses
- `400`: Invalid source parameter
- `502`: Data source unavailable
- `503`: No data source available

---

## 2. GET /api/positions
**Get all active positions with P&L**

### Request
```
GET /api/positions
```

### Response (200 OK)
```json
{
  "positions": [
    {
      "instrument": "EUR_USD",
      "units": 100000,
      "entry_price": 1.0800,
      "current_price": 1.0850,
      "unrealized_pnl": 500.0,
      "percentage_return": 0.46,
      "pip_value": 10.0
    }
  ],
  "total_unrealized_pnl": 500.0,
  "count": 1,
  "status": "ok"
}
```

### Error Responses
- `502`: Failed to retrieve positions
- `500`: Server error

---

## 3. POST /api/orders
**Place a new order**

### Request
```json
POST /api/orders
{
  "instrument": "EUR_USD",
  "units": 100000,
  "order_type": "MARKET",
  "price": null,
  "stop_loss": 1.0700,
  "take_profit": 1.0900
}
```

### Request Body
- `instrument` (required): Instrument code (e.g., EUR_USD)
- `units` (required): Number of units (must be > 0)
- `order_type` (required): MARKET, LIMIT, or STOP
- `price` (optional): Required for LIMIT orders
- `stop_loss` (optional): Stop loss price
- `take_profit` (optional): Take profit price

### Response (200 OK)
```json
{
  "order_id": "12345",
  "instrument": "EUR_USD",
  "units": 100000,
  "status": "FILLED"
}
```

### Error Responses
- `400`: Invalid order data, validation failed
- `500`: Order placement error

---

## 4. GET /api/orders
**List all open orders with optional filtering**

### Request
```
GET /api/orders?status=PENDING&instrument=EUR_USD
```

### Query Parameters
- `status` (optional): Filter by PENDING, FILLED, CANCELLED
- `instrument` (optional): Filter by instrument code

### Response (200 OK)
```json
{
  "orders": [
    {
      "order_id": "12345",
      "instrument": "EUR_USD",
      "units": 100000,
      "order_type": "MARKET",
      "status": "PENDING",
      "price": null,
      "created_at": "2026-04-23T18:04:00Z"
    }
  ],
  "count": 1,
  "status": "ok"
}
```

### Error Responses
- `502`: Failed to retrieve orders
- `500`: Server error

---

## 5. POST /api/orders/{id}/cancel
**Cancel an open order**

### Request
```
POST /api/orders/12345/cancel
```

### Path Parameters
- `id` (required): Order ID to cancel

### Response (200 OK)
```json
{
  "order_id": "12345",
  "status": "CANCELLED",
  "cancelled_at": "2026-04-23T18:05:00Z"
}
```

### Error Responses
- `400`: Order not found or already closed
- `500`: Cancellation error

---

## 6. GET /api/account
**Get account information**

### Request
```
GET /api/account
```

### Response (200 OK)
```json
{
  "account_id": "001-001-1234567-001",
  "balance": 100000.0,
  "equity": 100500.0,
  "margin_used": 10000.0,
  "margin_available": 90000.0,
  "margin_rate": 0.05,
  "unrealized_pnl": 500.0,
  "realized_pnl": 0.0,
  "total_pnl": 500.0,
  "currency": "USD",
  "timestamp": "2026-04-23T18:04:00Z",
  "status": "ok"
}
```

### Error Responses
- `500`: Account retrieval error

---

## 7. POST /api/backtest
**Run a backtest with historical data**

### Request
```json
POST /api/backtest
{
  "instrument": "EUR_USD",
  "start_date": "2025-01-01",
  "end_date": "2026-04-23",
  "strategy": "SMA_crossover",
  "initial_balance": 100000.0,
  "risk_per_trade": 0.02
}
```

### Request Body
- `instrument` (required): Instrument code
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (required): End date (YYYY-MM-DD)
- `strategy` (required): Strategy name (SMA_crossover, etc.)
- `initial_balance` (required): Starting capital (> 0)
- `risk_per_trade` (required): Risk percentage per trade

### Response (200 OK)
```json
{
  "backtest_id": "bt_20260423_001",
  "status": "COMPLETED",
  "instrument": "EUR_USD",
  "start_date": "2025-01-01",
  "end_date": "2026-04-23",
  "strategy": "SMA_crossover",
  "created_at": "2026-04-23T18:04:00Z"
}
```

### Error Responses
- `400`: Invalid parameters, insufficient data
- `500`: Backtest execution error

---

## 8. GET /api/backtest/{id}
**Get backtest results**

### Request
```
GET /api/backtest/bt_20260423_001
```

### Path Parameters
- `id` (required): Backtest ID

### Response (200 OK)
```json
{
  "backtest_id": "bt_20260423_001",
  "status": "COMPLETED",
  "instrument": "EUR_USD",
  "start_date": "2025-01-01",
  "end_date": "2026-04-23",
  "strategy": "SMA_crossover",
  "initial_balance": 100000.0,
  "statistics": {
    "total_return": 0.25,
    "annual_return": 0.45,
    "sharpe_ratio": 1.5,
    "max_drawdown": 0.15,
    "win_rate": 0.62,
    "total_trades": 47,
    "winning_trades": 29,
    "losing_trades": 18,
    "profit_factor": 1.8
  },
  "trades": [
    {
      "entry_date": "2026-01-15",
      "entry_price": 1.0800,
      "exit_date": "2026-01-20",
      "exit_price": 1.0850,
      "units": 100000,
      "pnl": 500.0,
      "return_pct": 0.46
    }
  ],
  "equity_curve": [
    {"date": "2026-01-01", "equity": 100000.0},
    {"date": "2026-01-15", "equity": 100500.0},
    {"date": "2026-04-23", "equity": 125000.0}
  ],
  "created_at": "2026-04-23T18:04:00Z",
  "completed_at": "2026-04-23T18:05:00Z"
}
```

### Error Responses
- `404`: Backtest not found
- `500`: Result retrieval error

---

## Data Sources

### OANDA Integration
- **Endpoint:** `https://api-practice.oanda.com/v3`
- **Auth:** Bearer token (set via OANDA_API_KEY)
- **Features:** Real-time quotes, position management, order execution
- **Fallback:** Automatic fallback to yfinance if unavailable

### yFinance Fallback
- **Source:** Yahoo Finance
- **Features:** Historical data, current quotes
- **Supported:** Forex pairs (EURUSD=X format), stocks, indices
- **Activated:** When FALLBACK_TO_YFINANCE=true and OANDA unavailable

---

## Error Handling

All endpoints include:
- **Comprehensive logging** at INFO and ERROR levels
- **Automatic fallback** from OANDA to yfinance for quotes
- **Validation** of all input parameters
- **HTTP status codes** for different error scenarios
- **Error messages** in response body

---

## Database Models

### OrderModel
Fields: id, instrument, units, order_type, status, price, stop_loss, take_profit, filled_price, timestamps, external_id

### PositionModel
Fields: id, instrument, units, entry_price, current_price, unrealized_pnl, percentage_return, pip_value, timestamps, external_id

### BacktestModel
Fields: id, instrument, start_date, end_date, strategy, initial_balance, risk_per_trade, status, statistics_json, trades_json, equity_curve_json, timestamps, error_message

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   cp .env.example .env
   export OANDA_API_KEY=your_key
   export OANDA_ACCOUNT_ID=your_account
   ```

3. **Run server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Test endpoints:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/quotes
   curl -X POST http://localhost:8000/api/orders \
     -H "Content-Type: application/json" \
     -d '{"instrument":"EUR_USD","units":100000,"order_type":"MARKET"}'
   ```

5. **View API docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
