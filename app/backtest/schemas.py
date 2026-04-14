"""
Backtest Request/Response Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TradeInput(BaseModel):
    """Single trade input for backtest."""
    trade_id: str = Field(..., description="Unique trade identifier")
    entry: float = Field(..., description="Entry price")
    stop_loss: float = Field(..., description="Stop loss price")
    tp1: float = Field(..., description="Take profit 1 price")
    tp2: float = Field(..., description="Take profit 2 price")
    direction: str = Field(default="Long", description="Trade direction: Long or Short")
    grade: str = Field(default="A+", description="Trade grade: A+, A, B, C, D")
    risk_pct: float = Field(default=2.0, description="Risk percentage per trade")


class BacktestRequest(BaseModel):
    """Request to run backtest."""
    trades: List[TradeInput] = Field(..., description="List of trades to backtest")
    starting_capital: float = Field(default=100.0, description="Starting capital in CHF")
    only_grades: Optional[List[str]] = Field(default=["A+", "A"], description="Filter trades by grade")
    

class TradeResult(BaseModel):
    """Single trade result."""
    trade_id: str
    entry: float
    exit: float
    direction: str
    r_multiple: float
    pnl: float
    scenario: str


class BacktestMetrics(BaseModel):
    """Performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    gross_profit: float
    gross_loss: float
    profit_factor: float = Field(..., description="Gross Profit / Gross Loss (capped at 999.99 if no losses)")
    avg_r: float
    max_drawdown_pct: float
    roi_pct: float
    final_equity: float
    sharpe_ratio: float


class BacktestResponse(BaseModel):
    """Backtest response."""
    success: bool
    timestamp: datetime
    trades_executed: int
    metrics: BacktestMetrics
    trades: List[TradeResult] = Field(default_factory=list)
    message: str
