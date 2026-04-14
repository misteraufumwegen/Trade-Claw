"""
Risk Management Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class RiskStatus(str, Enum):
    """Risk status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    HALTED = "halted"


class RiskLimits(BaseModel):
    """Risk limit configuration."""
    max_position_size_pct: float = Field(default=10.0, description="Max position size as % of account (hard limit)")
    max_drawdown_pct: float = Field(default=-15.0, description="Max drawdown before auto-halt")
    daily_loss_limit_pct: float = Field(default=-5.0, description="Daily loss limit")
    max_trades_per_day: int = Field(default=10, description="Max trades per day")
    

class RiskVaultData(BaseModel):
    """Data stored in risk vault."""
    position_size_cap_pct: float = Field(default=10.0)
    drawdown_halt_pct: float = Field(default=-15.0)
    stop_loss_immutable: bool = Field(default=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    

class RiskStatus(BaseModel):
    """Current risk status."""
    status: str  # healthy, warning, critical, halted
    current_drawdown_pct: float
    current_position_size_pct: float
    daily_loss_pct: float
    trades_today: int
    halted: bool
    halt_reason: Optional[str] = None
    message: str
