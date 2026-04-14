"""
Backtest Module - On-Demand Trade Simulation

Provides backtesting functionality for hypothetical trades.
"""

from .simulator import BacktestSimulator, BacktestResults
from .schemas import BacktestRequest, BacktestResponse

__all__ = ["BacktestSimulator", "BacktestResults", "BacktestRequest", "BacktestResponse"]
