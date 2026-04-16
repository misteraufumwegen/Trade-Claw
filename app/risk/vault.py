"""
RiskVault — in-memory risk state for standalone (no-db) operation.

Tracks stop-loss records, daily trades, drawdown status, and position-size
caps without requiring a database connection. Suitable for use in the
standalone RiskEngine and unit/integration tests.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StopLossRecord:
    trade_id: str
    order_id: str
    stop_loss: float
    symbol: str
    registered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    recorded_at: datetime = field(default_factory=datetime.utcnow)


class RiskVault:
    """
    In-memory risk control vault.

    Default limits (all overridable at construction time):
        position_size_cap_pct : 10.0   — max % of account per position
        drawdown_halt_pct     : -15.0  — halt trading when drawdown <= this
        stop_loss_immutable   : True   — stop-loss cannot be loosened after
                                         registration
    """

    def __init__(
        self,
        position_size_cap_pct: float = 10.0,
        drawdown_halt_pct: float = -15.0,
        stop_loss_immutable: bool = True,
    ) -> None:
        self.position_size_cap_pct = position_size_cap_pct
        self.drawdown_halt_pct = drawdown_halt_pct
        self.stop_loss_immutable = stop_loss_immutable

        self.active: bool = True
        self.halted: bool = False
        self.halt_reason: str | None = None

        self.stop_loss_records: dict[str, StopLossRecord] = {}
        self.daily_trades: list[TradeRecord] = []

    # ------------------------------------------------------------------
    # Stop-loss management
    # ------------------------------------------------------------------

    def register_stop_loss(
        self,
        trade_id: str,
        order_id: str,
        stop_loss: float,
        symbol: str,
    ) -> bool:
        """Register an immutable stop-loss for a trade. Returns True."""
        self.stop_loss_records[trade_id] = StopLossRecord(
            trade_id=trade_id,
            order_id=order_id,
            stop_loss=stop_loss,
            symbol=symbol,
        )
        return True

    def attempt_modify_stop_loss(
        self,
        trade_id: str,
        new_stop_loss: float,
    ) -> tuple[bool, str]:
        """
        Attempt to modify an existing stop-loss.

        Returns:
            (False, "IMMUTABLE: ...") when stop_loss_immutable is True.
            (True,  "OK")             when modification is allowed.
        """
        if trade_id not in self.stop_loss_records:
            return False, f"TRADE_NOT_FOUND: no record for {trade_id}"

        if self.stop_loss_immutable:
            original = self.stop_loss_records[trade_id].stop_loss
            return (
                False,
                f"IMMUTABLE: stop-loss {original} cannot be changed to {new_stop_loss}",
            )

        self.stop_loss_records[trade_id].stop_loss = new_stop_loss
        return True, "OK"

    # ------------------------------------------------------------------
    # Position-size validation
    # ------------------------------------------------------------------

    def validate_position_size(
        self,
        account_equity: float,
        position_value: float,
    ) -> tuple[bool, str, float]:
        """
        Check that position_value does not exceed position_size_cap_pct % of
        account_equity.

        Returns:
            (valid, reason, pct_of_equity)
        """
        if account_equity <= 0:
            return False, "INVALID: account_equity must be > 0", 0.0

        pct = (position_value / account_equity) * 100.0

        if pct > self.position_size_cap_pct:
            return (
                False,
                f"POSITION_SIZE: {pct:.2f}% exceeds cap of {self.position_size_cap_pct:.2f}%",
                pct,
            )

        return True, "OK", pct

    # ------------------------------------------------------------------
    # Drawdown check
    # ------------------------------------------------------------------

    def check_drawdown(
        self,
        current_equity: float,
        peak_equity: float,
    ) -> tuple[bool, str, float]:
        """
        Calculate drawdown and halt trading if it breaches the limit.

        Returns:
            (safe, reason, drawdown_pct)
        where drawdown_pct is a negative value (e.g. -15.0 = 15 % loss).
        """
        if peak_equity <= 0:
            return True, "OK: peak_equity is zero, skipping check", 0.0

        dd_pct = ((current_equity - peak_equity) / peak_equity) * 100.0

        if dd_pct <= self.drawdown_halt_pct:
            self.halted = True
            self.halt_reason = (
                f"Drawdown {dd_pct:.2f}% breached halt level {self.drawdown_halt_pct:.2f}%"
            )
            return (
                False,
                self.halt_reason,
                dd_pct,
            )

        return True, f"OK: drawdown {dd_pct:.2f}%", dd_pct

    # ------------------------------------------------------------------
    # Trade recording
    # ------------------------------------------------------------------

    def record_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        """Append a trade to the daily_trades list. Returns True."""
        self.daily_trades.append(
            TradeRecord(
                trade_id=trade_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
        )
        return True

    def get_daily_trade_count(self) -> int:
        """Return the number of trades recorded today."""
        return len(self.daily_trades)

    # ------------------------------------------------------------------
    # Halt management
    # ------------------------------------------------------------------

    def is_halted(self) -> bool:
        """Return whether trading is currently halted."""
        return self.halted

    def unhalt(self) -> bool:
        """
        Manually clear a halt condition (supervisor use only).
        Returns True.
        """
        self.halted = False
        self.halt_reason = None
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return a serialisable status snapshot."""
        return {
            "active": self.active,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "position_size_cap_pct": self.position_size_cap_pct,
            "drawdown_halt_pct": self.drawdown_halt_pct,
            "stop_loss_immutable": self.stop_loss_immutable,
            "open_stop_loss_records": len(self.stop_loss_records),
            "daily_trade_count": len(self.daily_trades),
        }
