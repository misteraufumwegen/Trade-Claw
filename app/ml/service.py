"""
ML service layer for Trade-Claw.

Three responsibilities:

1. **Feature extraction** — convert pre-trade inputs (HTTP DTO, broker context,
   risk-engine state) into the 20-element feature vector consumed by the
   ``SetupQualityScorer``.
2. **Inference** — load the active model checkpoint (if any) and produce a
   probability-of-success in [0, 1] for a feature vector. When no checkpoint
   is available, the service returns ``None`` so the caller can decide
   whether to pass-through (default) or fail closed.
3. **Outcome resolution** — given a closed broker order, classify the trade
   as WIN/LOSS/BREAKEVEN/CANCELLED/REJECTED and write the result back into
   the ``trade_outcomes`` row. This is the labelling step for future
   training.

Design notes:
- We deliberately keep PyTorch import optional so the FastAPI app boots even
  when torch isn't installed yet (useful for dev / smoke tests).
- The feature schema mirrors ``ml_bot_phase1/src/models/setup_scorer.py`` so
  the same checkpoints work in both code paths.
- Active checkpoint is selected via ``ML_MODEL_PATH`` env var (defaults to
  ``checkpoints/scorer_active.pt`` under the project root).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    pass

# Feature names — order matters: the model takes a fixed-shape vector.
FEATURE_NAMES: tuple[str, ...] = (
    "f_structural_level",
    "f_liquidity_sweep",
    "f_momentum",
    "f_volume",
    "f_risk_reward",
    "f_macro_alignment",
    "f_on_chain",
    "f_volatility",
    "f_trend_strength",
    "f_drawdown",
    "f_time_since_trade",
    "f_correlation_spy",
    "f_position_size",
    "f_margin_util",
    "f_concurrent_trades",
    "f_losing_streak",
    "f_profit_distance",
    "f_mtf_alignment",
    "f_price_action",
    "f_confluence",
)
FEATURE_COUNT = len(FEATURE_NAMES)
assert FEATURE_COUNT == 20, "Feature schema must remain 20-wide"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _default_checkpoint_path() -> Path:
    return _project_root() / "checkpoints" / "scorer_active.pt"


# ---------------------------------------------------------------------------
# Feature snapshot — what we save when an order is submitted
# ---------------------------------------------------------------------------


@dataclass
class FeatureSnapshot:
    """20-element feature vector + a few raw inputs we keep for context.

    All ``f_*`` values are normalised to [0, 1] in line with the
    ``SetupQualityScorer`` contract. ``raw_*`` inputs are *not* features but
    are forwarded so we can reconstruct context for outcome computation.
    """

    f_structural_level: float = 0.0
    f_liquidity_sweep: float = 0.0
    f_momentum: float = 0.0
    f_volume: float = 0.0
    f_risk_reward: float = 0.0
    f_macro_alignment: float = 0.0
    f_on_chain: float = 0.5
    f_volatility: float = 0.5
    f_trend_strength: float = 0.5
    f_drawdown: float = 0.0
    f_time_since_trade: float = 0.5
    f_correlation_spy: float = 0.5
    f_position_size: float = 0.5
    f_margin_util: float = 0.5
    f_concurrent_trades: float = 1.0
    f_losing_streak: float = 1.0
    f_profit_distance: float = 0.5
    f_mtf_alignment: float = 0.5
    f_price_action: float = 0.5
    f_confluence: float = 0.5

    def as_vector(self) -> list[float]:
        """Return features as an ordered list, matching ``FEATURE_NAMES``."""
        return [getattr(self, name) for name in FEATURE_NAMES]

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def _clip01(value: float) -> float:
    if value != value:  # NaN
        return 0.5
    return max(0.0, min(1.0, float(value)))


def extract_features(
    *,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    size: float,
    account_balance: float | None = None,
    grading_criteria: dict[str, bool] | None = None,
    drawdown_pct: float | None = None,
    open_position_count: int | None = None,
    losing_streak: int | None = None,
    macro_aligned: bool | None = None,
    correlation_score: float | None = None,
    volatility_pct: float | None = None,
) -> FeatureSnapshot:
    """Build the feature vector from inputs that are available at submit time.

    The function is deliberately defensive: callers will not always be able
    to pass everything (e.g. account balance during a webhook submit before
    the broker call). Missing values fall back to neutral 0.5.
    """
    snap = FeatureSnapshot()

    # Surgical-precision criteria — booleans become 0.0 / 1.0
    if grading_criteria:
        snap.f_structural_level = 1.0 if grading_criteria.get("structural_level") else 0.0
        snap.f_liquidity_sweep = 1.0 if grading_criteria.get("liquidity_sweep") else 0.0
        snap.f_momentum = 1.0 if grading_criteria.get("momentum") else 0.0
        snap.f_volume = 1.0 if grading_criteria.get("volume") else 0.0

    # Risk/Reward — encode as ratio normalised to [0, 1] where 1:3 = 1.0
    side_upper = side.upper()
    if side_upper == "BUY":
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit
    if risk > 0:
        rr = reward / risk
        snap.f_risk_reward = _clip01(rr / 3.0)  # 1:3 saturates
    else:
        snap.f_risk_reward = 0.0

    if macro_aligned is True:
        snap.f_macro_alignment = 1.0
    elif macro_aligned is False:
        snap.f_macro_alignment = 0.0
    else:
        snap.f_macro_alignment = 0.5

    # Drawdown is typically negative (-0.05 = -5%); we flip sign so a deep
    # drawdown pushes the feature toward 1.0.
    if drawdown_pct is not None:
        snap.f_drawdown = _clip01(abs(drawdown_pct) / 0.20)

    if open_position_count is not None:
        # 0 → 1.0 (no concurrent trades), 5+ → 0.0 (capacity exhausted)
        snap.f_concurrent_trades = _clip01(1.0 - (open_position_count / 5.0))

    if losing_streak is not None:
        # 0 → 1.0; 3+ losses → 0.0
        snap.f_losing_streak = _clip01(1.0 - (losing_streak / 3.0))

    if correlation_score is not None:
        snap.f_correlation_spy = _clip01(correlation_score)

    if volatility_pct is not None:
        snap.f_volatility = _clip01(volatility_pct / 0.05)  # 5% daily vol = 1.0

    if account_balance and account_balance > 0:
        notional = size * entry_price
        snap.f_position_size = _clip01(1.0 - (notional / account_balance))
        snap.f_margin_util = _clip01(notional / account_balance)
        snap.f_profit_distance = _clip01(reward / max(account_balance * 0.01, 1e-6))

    return snap


# ---------------------------------------------------------------------------
# Scorer — wraps the optional PyTorch model
# ---------------------------------------------------------------------------


class _ModelHolder:
    """Tiny in-process holder for the active checkpoint; thread-safe-enough
    for our single-process FastAPI deployment."""

    def __init__(self) -> None:
        self.model = None
        self.path: Path | None = None
        self.loaded_at: datetime | None = None
        self.is_torch_available = False
        try:
            import torch  # noqa: F401

            self.is_torch_available = True
        except ImportError:
            logger.warning(
                "PyTorch not installed; ML scoring will pass-through. "
                "Install via 'pip install torch' to enable model inference."
            )

    def load(self, path: Path) -> bool:
        if not self.is_torch_available:
            return False
        if not path.exists():
            logger.info("No model checkpoint at %s", path)
            self.model = None
            self.path = path
            return False
        try:
            import torch  # noqa: PLC0415

            from ml_bot_phase1.src.models.setup_scorer import SetupQualityScorer  # noqa: PLC0415

            checkpoint = torch.load(path, map_location="cpu", weights_only=False)
            model = SetupQualityScorer(input_size=FEATURE_COUNT, device="cpu")
            state = checkpoint.get("state_dict", checkpoint)
            model.load_state_dict(state)
            model.eval()
            self.model = model
            self.path = path
            self.loaded_at = datetime.utcnow()
            logger.info("ML model loaded from %s", path)
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load checkpoint %s", path)
            self.model = None
            return False

    def score(self, vector: list[float]) -> float | None:
        if self.model is None:
            return None
        try:
            import torch  # noqa: PLC0415

            with torch.no_grad():
                t = torch.tensor([vector], dtype=torch.float32)
                out = self.model(t)
                return float(out.item())
        except Exception:  # noqa: BLE001
            logger.exception("ML inference failed")
            return None


_holder = _ModelHolder()


def initialize_model(path: Path | str | None = None) -> bool:
    """Load (or reload) the active checkpoint. Safe to call any time."""
    p = Path(path) if path else _default_checkpoint_path()
    return _holder.load(p)


def score_features(features: FeatureSnapshot) -> float | None:
    """Return probability-of-success in [0, 1], or ``None`` when no model."""
    return _holder.score(features.as_vector())


def model_status() -> dict:
    """Diagnostic for the UI / API."""
    return {
        "torch_available": _holder.is_torch_available,
        "model_loaded": _holder.model is not None,
        "checkpoint_path": str(_holder.path) if _holder.path else None,
        "loaded_at": _holder.loaded_at.isoformat() if _holder.loaded_at else None,
        "feature_count": FEATURE_COUNT,
        "feature_names": list(FEATURE_NAMES),
    }


# Auto-load on import so the first request doesn't pay the latency.
initialize_model()


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------


def classify_outcome(
    *,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    closed_price: float | None,
    status: str,
) -> tuple[str, float]:
    """Decide the WIN/LOSS/BREAKEVEN/... label and the realized P&L.

    Heuristic, but deterministic:
    - status REJECTED → REJECTED, pnl=0
    - status CANCELLED with no fill → CANCELLED, pnl=0
    - filled with closed price ≥ TP for BUY (≤ TP for SELL) → WIN
    - filled with closed price ≤ SL for BUY (≥ SL for SELL) → LOSS
    - filled, anywhere in between → BREAKEVEN if within 10% of risk distance,
      otherwise WIN/LOSS based on direction-of-move
    """
    upper = (status or "").upper()
    if upper == "REJECTED":
        return "REJECTED", 0.0
    if closed_price is None:
        return "CANCELLED", 0.0
    if upper == "CANCELLED":
        return "CANCELLED", 0.0

    side_u = side.upper()
    risk = abs(entry_price - stop_loss) or 1e-9
    if side_u == "BUY":
        pnl = closed_price - entry_price
        if closed_price >= take_profit:
            return "WIN", pnl
        if closed_price <= stop_loss:
            return "LOSS", pnl
    else:  # SELL
        pnl = entry_price - closed_price
        if closed_price <= take_profit:
            return "WIN", pnl
        if closed_price >= stop_loss:
            return "LOSS", pnl

    if abs(pnl) < risk * 0.1:
        return "BREAKEVEN", pnl
    return ("WIN" if pnl > 0 else "LOSS"), pnl
