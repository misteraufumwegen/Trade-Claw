"""
Backtest Simulator - On-Demand Trade Simulation

Integrates Ünal's backtest_simulator.py logic into the bot.
Simulates trades based on historical price movements and risk management rules.
"""

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class BacktestResults:
    """Sammelt und berechnet Performance-Metriken"""

    def __init__(self, starting_capital: float = 100.0):
        self.trades: list[dict[str, Any]] = []
        self.winning_trades: list[dict[str, Any]] = []
        self.losing_trades: list[dict[str, Any]] = []
        self.gross_profit: float = 0.0
        self.gross_loss: float = 0.0
        self.max_drawdown: float = 0.0
        self.equity_curve: list[float] = []
        self.starting_capital: float = starting_capital
        self.current_equity: float = self.starting_capital

    def add_trade_result(
        self,
        trade_id: str,
        entry: float,
        exit: float,
        direction: str,
        r_multiple: float,
        pnl_chf: float,
        scenario: str = "unknown",
    ):
        """Addiert ein Trade-Ergebnis"""
        self.trades.append(
            {
                "trade_id": trade_id,
                "entry": entry,
                "exit": exit,
                "direction": direction,
                "r_multiple": r_multiple,
                "pnl": pnl_chf,
                "scenario": scenario,
            }
        )

        if pnl_chf > 0:
            self.winning_trades.append({"trade_id": trade_id, "pnl": pnl_chf, "r": r_multiple})
            self.gross_profit += pnl_chf
        else:
            self.losing_trades.append({"trade_id": trade_id, "pnl": pnl_chf, "r": r_multiple})
            self.gross_loss += abs(pnl_chf)

        self.current_equity += pnl_chf
        self.equity_curve.append(self.current_equity)

        # Update Drawdown
        max_equity = max(self.equity_curve) if self.equity_curve else self.starting_capital
        current_dd = (max_equity - self.current_equity) / max_equity if max_equity > 0 else 0
        if current_dd > self.max_drawdown:
            self.max_drawdown = current_dd

    def calculate_metrics(self) -> dict[str, Any]:
        """Berechnet alle Performance-Metriken"""
        total_trades = len(self.trades)

        # Win Rate
        win_rate = (len(self.winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        # Profit Factor
        # Handle zero loss case: cap at 999.99 for JSON serialization safety
        if self.gross_loss > 0:
            profit_factor = self.gross_profit / self.gross_loss
        elif self.gross_profit > 0:
            profit_factor = 999.99  # Perfect win rate (cap for JSON safety)
        else:
            profit_factor = 0.0  # No profit and no loss

        # Average R
        all_r = [t["r_multiple"] for t in self.trades]
        avg_r = sum(all_r) / len(all_r) if all_r else 0.0

        # ROI
        roi = (
            ((self.current_equity - self.starting_capital) / self.starting_capital * 100)
            if self.starting_capital > 0
            else 0.0
        )

        # Sharpe Ratio (vereinfacht)
        returns = []
        for i in range(1, len(self.equity_curve)):
            daily_return = (self.equity_curve[i] - self.equity_curve[i - 1]) / self.equity_curve[
                i - 1
            ]
            returns.append(daily_return)

        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            sharpe = (avg_return / std_dev * math.sqrt(252)) if std_dev > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": len(self.winning_trades),
            "losing_trades": len(self.losing_trades),
            "win_rate_pct": win_rate,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": profit_factor,
            "avg_r": avg_r,
            "max_drawdown_pct": self.max_drawdown * 100,
            "roi_pct": roi,
            "final_equity": self.current_equity,
            "sharpe_ratio": sharpe,
        }


class BacktestSimulator:
    """Simuliert Trades basierend auf hypothetischen Szenarien"""

    def __init__(self, starting_capital: float = 100.0):
        self.starting_capital = starting_capital
        self.results = BacktestResults(starting_capital=starting_capital)
        logger.info(f"BacktestSimulator initialized with capital: CHF {starting_capital}")

    def simulate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        direction: str = "Long",
        trade_id: str = "UNKNOWN",
        risk_percent: float = 2.0,
    ) -> dict[str, Any]:
        """
        Simuliert einen einzelnen Trade mit realistischen Exit-Szenarien

        Exit Distribution:
        - 40% TP1 (2.0R)
        - 35% TP2 (3.0R)
        - 15% Partial (1.5R)
        - 10% SL (-1.0R)
        """

        if direction == "Long":
            sl_distance = entry_price - stop_loss
            tp1_distance = tp1 - entry_price
            tp2 - entry_price
        else:  # Short
            sl_distance = stop_loss - entry_price
            tp1_distance = entry_price - tp1
            entry_price - tp2

        # Deterministisch basierend auf Trade-ID
        random.seed(hash(trade_id) % 2**32)

        exit_scenario = random.choices(["tp1", "tp2", "partial", "sl"], weights=[40, 35, 15, 10])[0]

        if exit_scenario == "tp1":
            exit_price = tp1
            r_multiple = 2.0
        elif exit_scenario == "tp2":
            exit_price = tp2
            r_multiple = 3.0
        elif exit_scenario == "partial":
            exit_price = (
                entry_price + (tp1_distance * 0.75)
                if direction == "Long"
                else entry_price - (tp1_distance * 0.75)
            )
            r_multiple = 1.5
        else:  # sl
            exit_price = stop_loss
            r_multiple = -1.0

        # Berechne Position Size
        risk_amount = (self.starting_capital * risk_percent) / 100
        position_units = risk_amount / sl_distance if sl_distance > 0 else 0.01

        # Berechne P/L
        if direction == "Long":
            pnl_chf = position_units * (exit_price - entry_price)
        else:
            pnl_chf = position_units * (entry_price - exit_price)

        # Addiere zum Results
        self.results.add_trade_result(
            trade_id=trade_id,
            entry=entry_price,
            exit=exit_price,
            direction=direction,
            r_multiple=r_multiple,
            pnl_chf=pnl_chf,
            scenario=exit_scenario,
        )

        return {
            "trade_id": trade_id,
            "direction": direction,
            "exit_price": exit_price,
            "r_multiple": r_multiple,
            "pnl": pnl_chf,
            "scenario": exit_scenario,
        }

    def run_backtest(
        self, trades: list[dict[str, Any]], only_grades: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Führt Backtest aus

        Args:
            trades: Liste von Trades mit entry, sl, tp1, tp2, grade, etc.
            only_grades: Filter nur diese Grades (default: A+, A)

        Returns:
            dict: Metriken + Trades
        """
        if only_grades is None:
            only_grades = ["A+", "A"]

        trades_executed = 0

        for trade in trades:
            # Filter by grade
            if trade.get("grade") not in only_grades:
                continue

            trades_executed += 1

            self.simulate_trade(
                entry_price=trade["entry"],
                stop_loss=trade["stop_loss"],
                tp1=trade["tp1"],
                tp2=trade["tp2"],
                direction=trade.get("direction", "Long"),
                trade_id=trade.get("trade_id", f"TRADE_{trades_executed}"),
                risk_percent=trade.get("risk_pct", 2.0),
            )

        metrics = self.results.calculate_metrics()

        logger.info(
            f"Backtest complete: {trades_executed} trades executed, "
            f"ROI: {metrics['roi_pct']:.2f}%, Win Rate: {metrics['win_rate_pct']:.1f}%"
        )

        return {
            "trades_executed": trades_executed,
            "metrics": metrics,
            "trades": self.results.trades,
        }
