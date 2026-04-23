# Trade-Claw Dashboard

Real-time trading dashboard with live quotes, position management, order execution, and backtesting capabilities.

## Architecture

```
trade-claw-sprint-1/
├── frontend/              # Next.js React application
│   ├── app/              # App directory (Next.js 13+)
│   ├── public/           # Static assets
│   ├── package.json
│   └── tsconfig.json
├── backend/              # FastAPI Python application
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── models/       # Pydantic schemas
│   │   ├── services/     # External integrations (OANDA, yfinance)
│   │   ├── core/         # Configuration
│   │   └── main.py       # FastAPI app entry
│   └── requirements.txt
├── docker/               # Docker configuration
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml    # Full stack orchestration
├── .env.example          # Environment template
└── README.md
```

## Quick Start

### Prerequisites

- Docker & Docker Compose (or Python 3.11+ and Node.js 22+)
- OANDA API credentials (optional - will use mock data without them)

### Setup

1. **Clone and navigate to project:**
```bash
cd /root/.openclaw/workspace/trade-claw-sprint-1
```

2. **Create `.env` file from template:**
```bash
cp .env.example .env
# Edit .env and add your OANDA credentials (optional)
```

3. **Start the full stack:**
```bash
docker-compose up --build
```

4. **Access the application:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health

### Running Locally (Without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Quotes
- `GET /api/quotes?instruments=EUR_USD,GBP_USD` - Real-time quotes

### Positions
- `GET /api/positions` - List active positions

### Orders
- `POST /api/orders` - Place order
- `GET /api/orders` - List orders
- `POST /api/orders/{id}/cancel` - Cancel order

### Account
- `GET /api/account` - Account information

### Backtest
- `POST /api/backtest` - Run backtest
- `GET /api/backtest/{id}` - Get backtest results

See [API_DOCS.md](./API_DOCS.md) for detailed documentation.

## Services

### PostgreSQL
- Database for persistent storage
- Default: `postgres:5432`

### Redis
- Cache and real-time data
- Default: `redis:6379`

### FastAPI Backend
- Python REST API
- Default: `http://localhost:8000`
- Auto-reload in development

### Next.js Frontend
- React TypeScript UI
- Default: `http://localhost:3000`
- Live reload in development

## Development

### Adding Backend Endpoints

1. Create a new router in `backend/app/routers/`
2. Define Pydantic schemas in `backend/app/models/schemas.py`
3. Add services in `backend/app/services/`
4. Include router in `backend/main.py`

### Adding Frontend Pages

1. Create new page in `frontend/app/[route]/page.tsx`
2. Use Redux store for state management
3. Fetch from backend APIs in `useEffect`

## Configuration

All configuration via environment variables in `.env`:

- `OANDA_API_KEY` - Your OANDA API key
- `OANDA_ACCOUNT_ID` - Your OANDA account ID
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `DEBUG` - Enable debug logging

## Testing

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm test
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for cloud deployment options.

## Sprint Progress

See [PROGRESS.md](./PROGRESS.md) for sprint tracking and deliverables.

---

**Status:** 🟢 ACTIVE  
**Next Milestone:** Hour 3-5 Backend APIs
