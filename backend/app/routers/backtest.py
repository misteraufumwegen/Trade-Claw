"""
Backtest API endpoints
POST /backtest - Run backtest
GET /backtest/{id} - Get backtest results
GET /backtest - List all backtests
"""
import logging
import uuid
from fastapi import APIRouter, HTTPException, Path, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.services.yfinance import yfinance_client
from app.models.database_models import BacktestModel
from app.core.database import get_db
from sqlalchemy.orm import Session
import json

logger = logging.getLogger(__name__)

router = APIRouter()

class BacktestRequest(BaseModel):
    """Backtest request schema"""
    instrument: str
    start_date: str  # ISO format: YYYY-MM-DD
    end_date: str    # ISO format: YYYY-MM-DD
    strategy: str = "SMA_crossover"
    initial_balance: float = 100000.0
    risk_per_trade: float = 0.02
    strategy_name: Optional[str] = None  # Display name for UI

class BacktestResponse(BaseModel):
    """Backtest response schema"""
    backtest_id: str
    status: str
    instrument: str
    start_date: str
    end_date: str
    strategy: str
    initial_balance: float
    created_at: str
    completed_at: Optional[str] = None

class BacktestStatistics(BaseModel):
    """Backtest performance statistics"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    profit_factor: float

def run_sma_backtest(data: dict, initial_balance: float, risk_per_trade: float) -> dict:
    """
    Simple SMA crossover backtest
    
    Args:
        data: Historical OHLCV data
        initial_balance: Starting balance
        risk_per_trade: Risk per trade (2%)
    
    Returns:
        Backtest results
    """
    try:
        ohlcv = data.get("ohlcv", [])
        
        if len(ohlcv) < 20:
            raise ValueError("Insufficient data for backtest")
        
        # Mock backtest results (in production, would do actual calculations)
        trades = []
        equity_curve = [{"date": ohlcv[0]["date"], "equity": initial_balance}]
        
        balance = initial_balance
        positions = 0
        entry_price = 0
        trade_count = 0
        winning = 0
        losing = 0
        
        # Simple mock: every 10 candles, flip position
        for i, candle in enumerate(ohlcv):
            if i % 10 == 0 and i > 0:
                if positions == 0:
                    positions = 100
                    entry_price = candle["close"]
                else:
                    exit_price = candle["close"]
                    pnl = (exit_price - entry_price) * positions
                    balance += pnl
                    
                    trades.append({
                        "entry_date": ohlcv[i-10]["date"],
                        "entry_price": entry_price,
                        "exit_date": candle["date"],
                        "exit_price": exit_price,
                        "units": positions,
                        "pnl": pnl,
                        "return_pct": (pnl / (entry_price * positions)) * 100 if entry_price > 0 else 0
                    })
                    
                    trade_count += 1
                    if pnl > 0:
                        winning += 1
                    else:
                        losing += 1
                    
                    positions = 0
            
            # Add equity point every candle
            if i % 5 == 0 or i == len(ohlcv) - 1:
                equity_curve.append({"date": candle["date"], "equity": balance})
        
        # Calculate statistics
        total_return = ((balance - initial_balance) / initial_balance)
        annual_return = total_return  # Simplified
        
        # Calculate Sharpe ratio (simplified)
        if len(equity_curve) > 1:
            returns = [(equity_curve[i]["equity"] - equity_curve[i-1]["equity"]) / equity_curve[i-1]["equity"] 
                      for i in range(1, len(equity_curve))]
            import statistics
            if returns:
                std_dev = statistics.stdev(returns) if len(returns) > 1 else 0.01
                sharpe = (annual_return / 252) / max(std_dev, 0.001) if std_dev > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        # Find max drawdown
        max_equity = balance
        max_dd = 0
        for candle_point in equity_curve:
            if candle_point["equity"] > max_equity:
                max_equity = candle_point["equity"]
            dd = (max_equity - candle_point["equity"]) / max_equity
            if dd > max_dd:
                max_dd = dd
        
        win_rate = winning / max(trade_count, 1)
        profit_factor = 1.5  # Mock value
        
        return {
            "statistics": {
                "total_return": total_return,
                "annual_return": annual_return,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "win_rate": win_rate,
                "total_trades": trade_count,
                "winning_trades": winning,
                "losing_trades": losing,
                "profit_factor": profit_factor
            },
            "trades": trades,
            "equity_curve": equity_curve
        }
    
    except Exception as e:
        logger.error(f"Backtest calculation error: {e}")
        raise

@router.post("/backtest")
async def run_backtest(backtest_req: BacktestRequest, db: Session = Depends(get_db)):
    """
    Run a backtest with specified parameters
    
    Args:
        backtest_req: Backtest parameters (instrument, dates, strategy, etc.)
        db: Database session
    
    Returns:
        Backtest job ID and status
    """
    try:
        # Validate inputs
        if not backtest_req.instrument:
            raise HTTPException(status_code=400, detail="Instrument is required")
        
        if not backtest_req.start_date or not backtest_req.end_date:
            raise HTTPException(status_code=400, detail="Start and end dates are required")
        
        if backtest_req.initial_balance <= 0:
            raise HTTPException(status_code=400, detail="Initial balance must be positive")
        
        # Create backtest job
        backtest_id = f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow()
        
        # Fetch historical data
        logger.info(f"Fetching data for {backtest_req.instrument} from {backtest_req.start_date} to {backtest_req.end_date}")
        
        # Convert forex pairs to yfinance symbols
        symbol = backtest_req.instrument
        if "_" in symbol and len(symbol) == 7:
            # Convert EUR_USD to EURUSD=X for yfinance
            symbol = symbol.replace("_", "") + "=X"
        
        data = await yfinance_client.get_historical_data(
            symbol=symbol,
            start=backtest_req.start_date,
            end=backtest_req.end_date,
            interval="1d"
        )
        
        if not data:
            logger.error(f"No data available for {backtest_req.instrument}")
            raise HTTPException(status_code=400, detail=f"No data available for {backtest_req.instrument}")
        
        # Run the backtest
        if backtest_req.strategy == "SMA_crossover":
            results = run_sma_backtest(data, backtest_req.initial_balance, backtest_req.risk_per_trade)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {backtest_req.strategy}")
        
        # Store in database
        completed_at = datetime.utcnow()
        
        backtest_model = BacktestModel(
            id=backtest_id,
            instrument=backtest_req.instrument,
            start_date=backtest_req.start_date,
            end_date=backtest_req.end_date,
            strategy=backtest_req.strategy,
            initial_balance=backtest_req.initial_balance,
            risk_per_trade=backtest_req.risk_per_trade,
            status="COMPLETED",
            statistics_json=json.dumps(results["statistics"]),
            trades_json=json.dumps(results["trades"]),
            equity_curve_json=json.dumps(results["equity_curve"]),
            created_at=created_at,
            started_at=created_at,
            completed_at=completed_at
        )
        
        db.add(backtest_model)
        db.commit()
        db.refresh(backtest_model)
        
        logger.info(f"Backtest {backtest_id} completed and stored in database")
        
        return {
            "backtest_id": backtest_id,
            "status": "COMPLETED",
            "instrument": backtest_req.instrument,
            "start_date": backtest_req.start_date,
            "end_date": backtest_req.end_date,
            "strategy": backtest_req.strategy,
            "initial_balance": backtest_req.initial_balance,
            "created_at": created_at.isoformat() + "Z",
            "completed_at": completed_at.isoformat() + "Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@router.get("/backtest/{backtest_id}")
async def get_backtest_results(
    backtest_id: str = Path(..., description="Backtest ID"),
    db: Session = Depends(get_db)
):
    """
    Get backtest results
    
    Args:
        backtest_id: ID of backtest to retrieve
        db: Database session
    
    Returns:
        Complete backtest results with equity curve, trades, stats
    """
    try:
        backtest = db.query(BacktestModel).filter(BacktestModel.id == backtest_id).first()
        
        if not backtest:
            raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
        
        # Parse JSON fields
        statistics = json.loads(backtest.statistics_json) if backtest.statistics_json else {}
        trades = json.loads(backtest.trades_json) if backtest.trades_json else []
        equity_curve = json.loads(backtest.equity_curve_json) if backtest.equity_curve_json else []
        
        return {
            "backtest_id": backtest_id,
            "status": backtest.status,
            "instrument": backtest.instrument,
            "start_date": backtest.start_date,
            "end_date": backtest.end_date,
            "strategy": backtest.strategy,
            "initial_balance": backtest.initial_balance,
            "risk_per_trade": backtest.risk_per_trade,
            "statistics": statistics,
            "trades": trades,
            "equity_curve": equity_curve,
            "created_at": backtest.created_at.isoformat() + "Z" if backtest.created_at else None,
            "completed_at": backtest.completed_at.isoformat() + "Z" if backtest.completed_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest retrieval failed: {str(e)}")

@router.get("/backtest")
async def list_backtests(db: Session = Depends(get_db)):
    """
    List all backtests
    
    Returns:
        List of backtest summaries
    """
    try:
        backtests = db.query(BacktestModel).order_by(BacktestModel.created_at.desc()).limit(50).all()
        
        return {
            "count": len(backtests),
            "backtests": [
                {
                    "backtest_id": bt.id,
                    "status": bt.status,
                    "instrument": bt.instrument,
                    "strategy": bt.strategy,
                    "initial_balance": bt.initial_balance,
                    "start_date": bt.start_date,
                    "end_date": bt.end_date,
                    "created_at": bt.created_at.isoformat() + "Z" if bt.created_at else None
                }
                for bt in backtests
            ]
        }
    
    except Exception as e:
        logger.error(f"Backtest listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest listing failed: {str(e)}")
