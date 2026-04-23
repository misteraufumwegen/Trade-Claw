"""
Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Quote Models
class Quote(BaseModel):
    """Real-time quote"""
    instrument: str
    bid: float
    ask: float
    time: datetime
    source: str

# Position Models
class Position(BaseModel):
    """Trading position"""
    instrument: str
    units: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    percentage_return: float
    pip_value: float

# Order Models
class OrderRequest(BaseModel):
    """Order request"""
    instrument: str
    units: int
    order_type: str = "MARKET"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class Order(BaseModel):
    """Order response"""
    order_id: str
    instrument: str
    units: int
    status: str
    order_type: str
    created_at: datetime

# Account Models
class Account(BaseModel):
    """Account information"""
    account_id: str
    balance: float
    equity: float
    margin_used: float
    margin_available: float
    unrealized_pnl: float
    total_pnl: float
    currency: str

# Backtest Models
class BacktestRequest(BaseModel):
    """Backtest request"""
    instrument: str
    start_date: str
    end_date: str
    strategy: str = "SMA_crossover"
    initial_balance: float = 100000.0
    risk_per_trade: float = 0.02

class BacktestTrade(BaseModel):
    """Individual trade from backtest"""
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    units: int
    pnl: float
    return_pct: float

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

class BacktestResults(BaseModel):
    """Complete backtest results"""
    backtest_id: str
    status: str
    statistics: BacktestStatistics
    trades: List[BacktestTrade]
    equity_curve: List[dict]
    completed_at: datetime
