"""
Backtest Module - On-Demand Trade Simulation

Provides backtesting functionality for hypothetical trades.
"""

from .schemas import BacktestRequest, BacktestResponse
from .simulator import BacktestResults, BacktestSimulator

__all__ = ["BacktestSimulator", "BacktestResults", "BacktestRequest", "BacktestResponse"]
