# Trading Bot - Phase 1 Scaffold

A multi-broker trading platform built with FastAPI, PostgreSQL, and Redis. Supports Alpaca and OANDA brokers with sandbox/demo environments for safe testing.

## Quick Start (All Platforms)

### Prerequisites

- **Docker Desktop** (macOS, Windows) or **Docker + Docker Compose** (Linux)
  - macOS: https://www.docker.com/products/docker-desktop/
  - Windows: https://www.docker.com/products/docker-desktop/
  - Linux: `sudo apt install docker.io docker-compose` (Debian/Ubuntu)
- **Python 3.11+** (optional, for local development)

### 1. Clone & Setup

```bash
cd trading-bot
cp .env.example .env
```

Edit `.env` with your sandbox credentials (Alpaca/OANDA demo keys).

### 2. Start Services (Docker)

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **Redis** on `localhost:6379`
- **FastAPI** on `localhost:8000`

### 3. Verify Installation

```bash
# Health check
curl http://localhost:8000/api/health

# Expected response:
# {"status":"healthy","timestamp":"2026-04-14T...",
#  "service":"trading-bot-api","version":"0.1.0"}
```

### 4. View API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Platform-Specific Instructions

### macOS (Docker Desktop)

1. **Install Docker Desktop:**
   ```bash
   # Using Homebrew
   brew install --cask docker
   ```

2. **Launch Docker Desktop** (from Applications)

3. **Start the bot:**
   ```bash
   docker-compose up -d
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f api
   ```

### Windows (Docker Desktop)

1. **Install Docker Desktop:**
   - Download: https://www.docker.com/products/docker-desktop/
   - Run installer, enable WSL2

2. **Launch Docker Desktop** (from Start menu)

3. **Open PowerShell or Git Bash:**
   ```powershell
   docker-compose up -d
   ```

4. **View logs:**
   ```powershell
   docker-compose logs -f api
   ```

### Linux (Debian/Ubuntu)

1. **Install Docker & Docker Compose:**
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose -y
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Start the bot:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f api
   ```

## Project Structure

```
trading-bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   └── interfaces/
│       ├── __init__.py
│       └── broker.py        # BrokerInterface abstract class
├── tests/                   # Unit and integration tests
├── migrations/
│   └── init.sql            # PostgreSQL schema
├── docker-compose.yml      # Multi-container orchestration
├── Dockerfile              # API container image
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

## Broker Setup

### Alpaca (Sandbox)

1. Sign up: https://app.alpaca.markets/
2. Create **Sandbox** account (paper trading)
3. Get API keys from dashboard
4. Add to `.env`:
   ```
   ALPACA_API_KEY=your_sandbox_key
   ALPACA_API_SECRET=your_sandbox_secret
   ALPACA_ENVIRONMENT=sandbox
   ```

### OANDA (Demo)

1. Sign up: https://www.oanda.com/
2. Create **Demo** account
3. Get API token from account settings
4. Add to `.env`:
   ```
   OANDA_API_KEY=your_demo_token
   OANDA_ACCOUNT_ID=your_demo_account_id
   OANDA_ENVIRONMENT=demo
   ```

## Common Commands

### Run Services

```bash
# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View live logs
docker-compose logs -f api

# Rebuild containers
docker-compose up -d --build
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U trading_user -d trading_bot

# View schema
\dt  # Tables
\di  # Indexes
```

### Redis Access

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Check keys
KEYS *
GET key_name
```

### API Examples

```bash
# Health check
curl http://localhost:8000/api/health

# Get accounts (placeholder)
curl http://localhost:8000/api/accounts

# Get positions (placeholder)
curl http://localhost:8000/api/positions
```

## Development

### Local Python Setup (Optional)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

### Add a New Endpoint

Edit `app/main.py`:

```python
@app.get("/api/your-endpoint", tags=["YourTag"])
async def your_endpoint():
    return {"data": "your response"}
```

Restart: `docker-compose restart api`

## Troubleshooting

### Docker Won't Start

```bash
# Check Docker daemon
docker ps

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

### Database Connection Error

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify credentials in .env
grep DB_ .env

# Rebuild database
docker-compose down -v
docker-compose up -d postgres
sleep 5
docker-compose up -d api
```

### Port Already in Use

```bash
# Change port in .env or docker-compose.yml
API_PORT=8001  # Instead of 8000
REDIS_PORT=6380  # Instead of 6379
```

## Next Steps

- [ ] Implement AlpacaAdapter (Day 2-3)
- [ ] Implement OandaAdapter (Day 2-3)
- [ ] Add unit tests (Day 2-3)
- [ ] Credential vault encryption (Day 4-5)
- [ ] Database migrations with Alembic (Day 4-5)
- [ ] Integration tests (End of Week 1)
- [ ] Frontend scaffold (TBD)

## Documentation

- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **OpenAPI Schema:** http://localhost:8000/openapi.json
- **Developer Guide:** `docs/DEVELOPER_GUIDE.md` (coming soon)

## Support

For issues or questions, check:
1. `docker-compose logs` for error messages
2. PostgreSQL schema: `migrations/init.sql`
3. Environment template: `.env.example`

---

**Phase 1 Status:** ✅ Scaffolding Complete (2026-04-14)
