"""
Autopilot state and TradingView webhook handler.

Single-process in-memory state (a runtime flag + small audit ring buffer).
On restart, the autopilot is OFF by default. The user must explicitly arm
it from the UI or via API. This is a deliberate safety choice — we never
want a crashloop to silently re-enable autonomous trading.

The webhook endpoint is mounted in ``app/main.py`` so it can share the
shared session router and DB. This module just owns the small business
logic that wraps it.
"""

from __future__ import annotations

import hmac
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AutopilotState:
    """Runtime state for the autopilot subsystem.

    The ``mode`` field decides what happens to incoming TradingView signals:
        - ``"off"``     → ignore (logged, but no order)
        - ``"dry_run"`` → run the pipeline but do NOT submit (returns the
                          decision so you can validate the wiring)
        - ``"live"``    → run the pipeline and submit when all gates pass
    """

    mode: str = "off"  # "off" | "dry_run" | "live"
    session_id: str | None = None
    threshold: float = 0.5  # ML threshold the gate enforces
    require_grade: tuple[str, ...] = ("A+", "A")
    enabled_at: datetime | None = None
    history: deque[dict] = field(default_factory=lambda: deque(maxlen=50))


_state = AutopilotState()


def get_state() -> dict:
    return {
        "mode": _state.mode,
        "session_id": _state.session_id,
        "threshold": _state.threshold,
        "require_grade": list(_state.require_grade),
        "enabled_at": _state.enabled_at.isoformat() if _state.enabled_at else None,
        "history": list(_state.history),
    }


def set_state(
    *,
    mode: str | None = None,
    session_id: str | None = None,
    threshold: float | None = None,
    require_grade: list[str] | None = None,
    force: bool = False,
) -> dict:
    """Update autopilot state.

    Going ``dry_run → live`` is gated by ``safety_gates.validate_dry_run_record``
    unless ``force=True``. This prevents flipping straight from "untested" to
    "real money" without rehearsing the pipeline first.
    """
    if mode is not None:
        if mode not in {"off", "dry_run", "live"}:
            raise ValueError("mode must be off | dry_run | live")
        if mode == "live" and not force:
            # Local import to avoid pulling sqlalchemy into the autopilot
            # module's import path.
            from app.risk.safety_gates import validate_dry_run_record  # noqa: PLC0415

            ok, reason = validate_dry_run_record(list(_state.history))
            if not ok:
                raise ValueError(reason or "DRY_RUN_INSUFFICIENT")
        _state.mode = mode
        _state.enabled_at = datetime.utcnow() if mode != "off" else None
    if session_id is not None:
        _state.session_id = session_id
    if threshold is not None:
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("threshold must be in [0, 1]")
        _state.threshold = threshold
    if require_grade is not None:
        _state.require_grade = tuple(require_grade)
    return get_state()


def record(event: dict) -> None:
    event = {**event, "ts": datetime.utcnow().isoformat()}
    _state.history.append(event)


# ---------------------------------------------------------------------------
# Shared-secret verification
# ---------------------------------------------------------------------------


def verify_secret(provided: str | None) -> bool:
    """Constant-time compare against ``TV_WEBHOOK_SECRET``.

    Falls back to denying when the env var is unset (fail-closed).
    """
    expected = os.getenv("TV_WEBHOOK_SECRET", "").strip()
    if not expected:
        logger.warning("TV_WEBHOOK_SECRET not configured — denying all webhook traffic")
        return False
    if not provided:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


# ---------------------------------------------------------------------------
# Signal payload — what we expect from TradingView Pine alerts
# ---------------------------------------------------------------------------


@dataclass
class TradingViewSignal:
    symbol: str
    side: str  # BUY | SELL
    entry: float
    stop_loss: float
    take_profit: float
    size: float | None = None
    confidence: float | None = None
    grading_criteria: dict[str, bool] | None = None
    macro_aligned: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, body: dict) -> TradingViewSignal:
        side = str(body.get("side", body.get("action", ""))).upper().strip()
        if side in {"LONG", "BUY"}:
            side = "BUY"
        elif side in {"SHORT", "SELL"}:
            side = "SELL"
        else:
            raise ValueError(f"Unsupported side/action in payload: {body!r}")

        symbol = str(body.get("symbol", "")).strip().upper()
        if not symbol:
            raise ValueError("Missing 'symbol' in payload")

        try:
            entry = float(body["entry"])
            stop_loss = float(body["stop_loss"])
            take_profit = float(body["take_profit"])
        except KeyError as exc:
            raise ValueError(f"Missing price field: {exc}") from None

        size = float(body["size"]) if "size" in body else None
        confidence = float(body["confidence"]) if "confidence" in body else None

        criteria = body.get("grading_criteria") or body.get("criteria")
        macro_aligned = body.get("macro_aligned")

        return cls(
            symbol=symbol,
            side=side,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size=size,
            confidence=confidence,
            grading_criteria=criteria if isinstance(criteria, dict) else None,
            macro_aligned=bool(macro_aligned) if macro_aligned is not None else None,
            raw=body,
        )
