"""
Backtest API endpoints
POST /backtest - Run backtest
GET /backtest/{id} - Get backtest results
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class BacktestRequest(BaseModel):
    """Backtest request schema"""
    instrument: str
    start_date: str  # YYYY-MM-DD
    end_date: str
    strategy: str = "SMA_crossover"
    initial_balance: float = 100000.0
    risk_per_trade: float = 0.02
    
@router.post("/backtest")
async def run_backtest(backtest: BacktestRequest):
    """
    Run a backtest with specified parameters
    
    Args:
        backtest: Backtest parameters (instrument, dates, strategy, etc.)
    
    Returns:
        Backtest job ID and status
    """
    # Mock response - will be replaced with real backtest engine
    return {
        "backtest_id": "bt_20260423_001",
        "status": "RUNNING",
        "instrument": backtest.instrument,
        "start_date": backtest.start_date,
        "end_date": backtest.end_date,
        "strategy": backtest.strategy,
        "created_at": "2026-04-23T18:04:00Z"
    }

@router.get("/backtest/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    """
    Get backtest results
    
    Args:
        backtest_id: ID of backtest to retrieve
    
    Returns:
        Complete backtest results with equity curve, trades, stats
    """
    # Mock response
    return {
        "backtest_id": backtest_id,
        "status": "COMPLETED",
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
        "completed_at": "2026-04-23T18:04:00Z"
    }
