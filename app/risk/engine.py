"""Risk validation engine - prevents high-risk orders and enforces drawdown limits."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from sqlalchemy.orm import Session

from app.db.models import Order, Position, RiskLimit


class RiskLevel(Enum):
    """Risk level classification."""
    OK = "OK"
    WARNING = "WARNING"
    BREACH = "BREACH"


@dataclass
class RiskValidationResult:
    """Result of risk validation."""
    approved: bool
    level: RiskLevel
    message: str
    reason: Optional[str] = None
    halt_triggered: bool = False


class DBRiskEngine:
    """
    DB-backed risk validation engine for order submission (Phase 4).

    Use this in FastAPI endpoints that have a SQLAlchemy session.
    For standalone / no-db use, see :class:`RiskEngine`.

    Enforces:
    - Maximum position size (10% of account)
    - Minimum R/R ratio (1.5:1)
    - Drawdown limits (-15% hard stop)
    - Stop loss immutability
    - Daily loss limits (-20%)
    """

    def __init__(self, db: Session):
        self.db = db

    def validate_order(
        self,
        session_id: str,
        account_balance: Decimal,
        symbol: str,
        side: str,
        size: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> RiskValidationResult:
        """
        Validate incoming order against risk limits.
        
        Args:
            session_id: Broker session ID
            account_balance: Account balance in base currency
            symbol: Trading symbol (e.g., BTC/USD)
            side: BUY or SELL
            size: Order size
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            RiskValidationResult with approval status and reason
        """
        # Fetch risk limits
        risk_limit = self.db.query(RiskLimit).filter(
            RiskLimit.session_id == session_id
        ).first()
        
        if not risk_limit:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message="No risk limits configured for this session",
                reason="MISSING_RISK_CONFIG"
            )
        
        # Check if trading is halted
        if risk_limit.is_halted:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message="Trading halted: Drawdown limit exceeded",
                reason="DRAWDOWN_HALT",
                halt_triggered=True
            )
        
        # 1. Validate Position Size (≤ 10% of account)
        position_size_check = self._validate_position_size(
            account_balance, entry_price, size, risk_limit
        )
        if not position_size_check.approved:
            return position_size_check
        
        # 2. Validate R/R Ratio (≥ 1.5:1)
        risk_reward_check = self._validate_risk_reward(
            entry_price, stop_loss, take_profit, side, risk_limit
        )
        if not risk_reward_check.approved:
            return risk_reward_check
        
        # 3. Check Drawdown Limits
        drawdown_check = self._validate_drawdown(session_id, size, entry_price, risk_limit)
        if not drawdown_check.approved:
            return drawdown_check
        
        # 4. Check Daily Loss Limit
        daily_loss_check = self._validate_daily_loss(session_id, risk_limit)
        if not daily_loss_check.approved:
            return daily_loss_check
        
        # 5. Validate Stop Loss Immutability (check if order exists)
        # This is enforced at API level - cannot move SL after order creation
        
        return RiskValidationResult(
            approved=True,
            level=RiskLevel.OK,
            message="Order approved - all risk checks passed",
        )

    def _validate_position_size(
        self,
        account_balance: Decimal,
        entry_price: Decimal,
        size: Decimal,
        risk_limit: RiskLimit,
    ) -> RiskValidationResult:
        """Check that position size does not exceed max % of account."""
        position_value = entry_price * size
        max_position_value = account_balance * Decimal(str(risk_limit.max_position_size_pct))
        
        if position_value > max_position_value:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message=f"Position size ${position_value:.2f} exceeds max ${max_position_value:.2f}",
                reason="POSITION_SIZE_EXCEEDED"
            )
        
        return RiskValidationResult(
            approved=True,
            level=RiskLevel.OK,
            message="Position size check passed"
        )

    def _validate_risk_reward(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        side: str,
        risk_limit: RiskLimit,
    ) -> RiskValidationResult:
        """Check that R/R ratio meets minimum threshold."""
        if side.upper() == "BUY":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SELL
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message="Invalid stop loss: must be below entry on BUY, above on SELL",
                reason="INVALID_STOP_LOSS"
            )
        
        if reward <= 0:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message="Invalid take profit: must be above entry on BUY, below on SELL",
                reason="INVALID_TAKE_PROFIT"
            )
        
        risk_reward_ratio = float(reward / risk)
        
        if risk_reward_ratio < risk_limit.min_risk_reward_ratio:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.WARNING,
                message=f"R/R ratio {risk_reward_ratio:.2f}:1 below minimum {risk_limit.min_risk_reward_ratio}:1",
                reason="RISK_REWARD_TOO_LOW"
            )
        
        return RiskValidationResult(
            approved=True,
            level=RiskLevel.OK,
            message=f"R/R ratio {risk_reward_ratio:.2f}:1 approved"
        )

    def _validate_drawdown(
        self,
        session_id: str,
        size: Decimal,
        entry_price: Decimal,
        risk_limit: RiskLimit,
    ) -> RiskValidationResult:
        """
        Check that the current drawdown has not breached the configured limit.

        SIGN CONVENTION (documented for clarity, see review finding M1):
        ``current_drawdown_pct`` and ``max_drawdown_pct`` are both stored as
        **negative** numbers — e.g. ``-0.15`` means "15 % loss is the ceiling".
        A deeper (more negative) current drawdown than the threshold is a
        breach:

            threshold = -0.15   (max 15 % loss allowed)
            current   = -0.20   → -0.20 < -0.15 → BREACH
            current   = -0.05   → -0.05 < -0.15 is False → OK
        """
        current_drawdown = risk_limit.current_drawdown_pct
        max_drawdown_threshold = risk_limit.max_drawdown_pct

        # Equivalent, more readable form: |current| > |threshold|.
        # We keep the numeric comparison to avoid ambiguity when sign is 0.
        if current_drawdown < max_drawdown_threshold:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message=(
                    f"Drawdown {current_drawdown:.2%} exceeds limit "
                    f"{max_drawdown_threshold:.2%}"
                ),
                reason="DRAWDOWN_LIMIT_BREACHED",
                halt_triggered=True,
            )

        return RiskValidationResult(
            approved=True,
            level=RiskLevel.OK,
            message=f"Drawdown check passed (current: {current_drawdown:.2%})",
        )

    def _validate_daily_loss(
        self,
        session_id: str,
        risk_limit: RiskLimit,
    ) -> RiskValidationResult:
        """Check daily-loss limit.

        Same sign convention as ``_validate_drawdown``: both values are stored
        as negative percentages; the current daily loss is breached when it is
        *more negative* than the threshold.
        """
        current_daily_loss = risk_limit.current_daily_loss_pct
        max_daily_loss = risk_limit.max_daily_loss_pct

        if current_daily_loss < max_daily_loss:
            return RiskValidationResult(
                approved=False,
                level=RiskLevel.BREACH,
                message=(
                    f"Daily loss {current_daily_loss:.2%} exceeds limit "
                    f"{max_daily_loss:.2%}"
                ),
                reason="DAILY_LOSS_LIMIT_BREACHED",
            )

        return RiskValidationResult(
            approved=True,
            level=RiskLevel.OK,
            message=f"Daily loss check passed (current: {current_daily_loss:.2%})",
        )

    def calculate_position_size(
        self,
        account_balance: Decimal,
        risk_pct: float,
        entry_price: Decimal,
        stop_loss: Decimal,
    ) -> Decimal:
        """
        Calculate maximum position size for a given risk tolerance.
        
        Args:
            account_balance: Total account balance
            risk_pct: Risk percentage per trade (e.g., 0.02 = 2%)
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Maximum size in units
        """
        risk_amount = account_balance * Decimal(str(risk_pct))
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return Decimal(0)
        
        position_size = risk_amount / risk_per_unit
        return position_size

    def check_drawdown_halt(self, session_id: str) -> bool:
        """
        Check if drawdown breach should halt all trading.
        
        Returns:
            True if trading should be halted
        """
        risk_limit = self.db.query(RiskLimit).filter(
            RiskLimit.session_id == session_id
        ).first()
        
        if not risk_limit:
            return False
        
        if risk_limit.current_drawdown_pct < risk_limit.max_drawdown_pct:
            risk_limit.is_halted = True
            self.db.commit()
            return True
        
        return False

    def update_position_pnl(
        self,
        session_id: str,
        account_balance: Decimal,
    ) -> None:
        """
        Update P&L for all open positions and recalculate drawdown.
        Called periodically or after fills.
        """
        positions = self.db.query(Position).filter(
            Position.session_id == session_id,
            Position.status == "OPEN"
        ).all()
        
        total_unrealized_pnl = Decimal(0)
        
        for position in positions:
            # Calculate unrealized P&L
            if position.side.upper() == "LONG":
                position.unrealized_pnl = (position.current_price - position.entry_price) * position.size
            else:  # SHORT
                position.unrealized_pnl = (position.entry_price - position.current_price) * position.size
            
            total_unrealized_pnl += position.unrealized_pnl
        
        # Update risk limit with drawdown
        risk_limit = self.db.query(RiskLimit).filter(
            RiskLimit.session_id == session_id
        ).first()
        
        if risk_limit and account_balance > 0:
            drawdown_pct = float(total_unrealized_pnl / account_balance)
            risk_limit.current_drawdown_pct = drawdown_pct

            # Check if halt should be triggered
            if drawdown_pct < risk_limit.max_drawdown_pct and risk_limit.halt_on_breach:
                risk_limit.is_halted = True

        self.db.commit()


# ---------------------------------------------------------------------------
# Standalone RiskEngine (no database required)
# ---------------------------------------------------------------------------

from datetime import datetime as _datetime  # local import to avoid top-level cycle
from typing import Tuple as _Tuple
from app.risk.vault import RiskVault  # noqa: E402


class RiskEngine:
    """
    Standalone risk engine backed by an in-memory :class:`RiskVault`.

    Suitable for unit/integration tests and Phase 2 API endpoints that do
    not have access to a SQLAlchemy session.  For production order validation
    with a live database, use :class:`DBRiskEngine`.
    """

    def __init__(self) -> None:
        self.vault = RiskVault()

    def pre_trade_check(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        account_equity: float,
        stop_loss: float,
        take_profit: float,
    ) -> _Tuple[bool, dict]:
        """
        Run pre-trade risk checks.

        Returns:
            (approved: bool, details: dict)  where details['checks'] maps
            each check name to True (passed) or False (failed).
        """
        checks: dict = {}

        # Halt check
        if self.vault.is_halted():
            checks["halted"] = False
            return False, {"checks": checks, "halt_reason": self.vault.halt_reason}
        checks["halted"] = True

        # Position size check
        position_value = quantity * entry_price
        ps_valid, ps_reason, ps_pct = self.vault.validate_position_size(
            account_equity, position_value
        )
        checks["position_size"] = ps_valid
        if not ps_valid:
            return False, {"checks": checks, "reason": ps_reason, "position_pct": ps_pct}

        # All checks passed
        return True, {"checks": checks}

    def execute_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        """Execute a trade: record it and register the immutable stop-loss."""
        self.vault.record_trade(
            trade_id, symbol, side, quantity, entry_price, stop_loss, take_profit
        )
        self.vault.register_stop_loss(
            trade_id=trade_id,
            order_id=trade_id,
            stop_loss=stop_loss,
            symbol=symbol,
        )
        return True

    def get_status(self) -> dict:
        """Return a serialisable status snapshot."""
        return {
            "vault_status": self.vault.status(),
            "halted": self.vault.is_halted(),
            "timestamp": _datetime.utcnow().isoformat(),
        }
