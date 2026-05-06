"""
Trainer for the ``SetupQualityScorer`` neural net.

Two modes:

* **Live retrain** — read all closed ``trade_outcomes`` rows that have a label
  (WIN/LOSS), build (X, y) tensors, train for a configurable number of
  epochs, save a checkpoint, and (optionally) make it the active model.
* **Bootstrap** — same shape, but the (X, y) data comes from a synthetic
  dataset built by ``app/ml/bootstrap.py`` (Phase 3) instead of live trades.

The trainer is intentionally tiny — we only have a few thousand examples in
the foreseeable future, so a 64→32 NN trains in seconds on CPU.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from .service import FEATURE_NAMES, _default_checkpoint_path, initialize_model

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


@dataclass
class TrainingResult:
    samples: int
    wins: int
    losses: int
    epochs: int
    final_loss: float
    final_accuracy: float
    checkpoint_path: str
    activated: bool
    started_at: str
    finished_at: str


def _checkpoints_dir() -> Path:
    p = _default_checkpoint_path().parent
    p.mkdir(parents=True, exist_ok=True)
    return p


def _label_for_outcome(outcome: str) -> float | None:
    """Convert ``trade_outcomes.outcome`` to a binary label.

    BREAKEVEN is dropped (label=None) because it carries little signal.
    CANCELLED / REJECTED don't represent a trade-going-right-or-wrong, so
    they're also dropped.
    """
    if outcome == "WIN":
        return 1.0
    if outcome == "LOSS":
        return 0.0
    return None


def _collect_training_data(db: "Session") -> tuple[list[list[float]], list[float]]:
    from app.db.models import TradeOutcome  # noqa: PLC0415

    rows = (
        db.query(TradeOutcome)
        .filter(TradeOutcome.outcome.in_(["WIN", "LOSS"]))
        .all()
    )
    X: list[list[float]] = []
    y: list[float] = []
    for row in rows:
        label = _label_for_outcome(row.outcome)
        if label is None:
            continue
        X.append([float(getattr(row, name) or 0.0) for name in FEATURE_NAMES])
        y.append(label)
    return X, y


def train_from_outcomes(
    db: "Session",
    *,
    epochs: int = 200,
    learning_rate: float = 1e-3,
    activate: bool = True,
    extra_data: tuple[Sequence[Sequence[float]], Sequence[float]] | None = None,
) -> TrainingResult:
    """Train ``SetupQualityScorer`` on the live outcomes table.

    ``extra_data`` lets the bootstrap pipeline append synthetic samples to
    the live ones — useful when there are too few real trades yet.
    """
    started = datetime.utcnow()
    try:
        import torch  # noqa: PLC0415
        import torch.nn as nn  # noqa: PLC0415

        from ml_bot_phase1.src.models.setup_scorer import SetupQualityScorer  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is not installed; cannot retrain. Run "
            "'pip install -r requirements.txt'."
        ) from exc

    X, y = _collect_training_data(db)
    if extra_data is not None:
        X.extend([list(map(float, row)) for row in extra_data[0]])
        y.extend([float(v) for v in extra_data[1]])

    if len(X) < 8:
        raise ValueError(
            f"Not enough labelled trades to train (have {len(X)}, need ≥ 8). "
            "Either close more trades or run a bootstrap (Phase 3)."
        )

    wins = int(sum(y))
    losses = len(y) - wins
    if wins == 0 or losses == 0:
        raise ValueError(
            f"Need both wins and losses to train (wins={wins}, losses={losses})."
        )

    Xt = torch.tensor(X, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

    # Class weighting — wins are typically rarer than losses early on; this
    # keeps gradient updates balanced.
    pos_weight = torch.tensor([losses / max(wins, 1)], dtype=torch.float32)
    criterion = nn.BCELoss()
    model = SetupQualityScorer(input_size=Xt.shape[1], device="cpu")
    optim = torch.optim.Adam(model.parameters(), lr=learning_rate)

    last_loss = 0.0
    last_acc = 0.0
    model.train()
    for _epoch in range(epochs):
        optim.zero_grad()
        preds = model(Xt)
        # BCELoss with pos_weight via manual scaling — BCEWithLogitsLoss has
        # pos_weight directly but requires logits. Sigmoid output makes BCE
        # the simpler choice; we approximate weighting by a per-sample factor.
        weights = torch.where(yt > 0.5, pos_weight, torch.ones_like(yt))
        loss = (criterion(preds, yt) * weights).mean()
        loss.backward()
        optim.step()
        last_loss = float(loss.item())
        with torch.no_grad():
            preds_bin = (preds >= 0.5).float()
            last_acc = float((preds_bin == yt).float().mean().item())

    timestamp = started.strftime("%Y%m%dT%H%M%S")
    ckpt_dir = _checkpoints_dir()
    ckpt_path = ckpt_dir / f"scorer_{timestamp}.pt"
    torch.save({"state_dict": model.state_dict()}, ckpt_path)

    metadata = {
        "samples": len(X),
        "wins": wins,
        "losses": losses,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "final_loss": last_loss,
        "final_accuracy": last_acc,
        "started_at": started.isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
    }
    (ckpt_dir / f"scorer_{timestamp}.json").write_text(json.dumps(metadata, indent=2))

    activated = False
    if activate:
        active_path = _default_checkpoint_path()
        # Copy contents — symlinks are awkward on Windows.
        active_path.write_bytes(ckpt_path.read_bytes())
        initialize_model(active_path)
        activated = True

    finished = datetime.utcnow()
    logger.info(
        "Training finished: samples=%d wins=%d losses=%d loss=%.4f acc=%.3f "
        "checkpoint=%s active=%s",
        len(X),
        wins,
        losses,
        last_loss,
        last_acc,
        ckpt_path,
        activated,
    )
    return TrainingResult(
        samples=len(X),
        wins=wins,
        losses=losses,
        epochs=epochs,
        final_loss=last_loss,
        final_accuracy=last_acc,
        checkpoint_path=str(ckpt_path),
        activated=activated,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )


def list_checkpoints() -> list[dict]:
    """List available checkpoints with their metadata."""
    ckpt_dir = _checkpoints_dir()
    out: list[dict] = []
    active_path = _default_checkpoint_path()
    active_bytes = active_path.read_bytes() if active_path.exists() else None
    for ckpt in sorted(ckpt_dir.glob("scorer_*.pt")):
        meta_path = ckpt.with_suffix(".json")
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:  # noqa: BLE001
                meta = {}
        is_active = (
            active_bytes is not None and ckpt.read_bytes() == active_bytes
        )
        out.append(
            {
                "checkpoint": ckpt.name,
                "path": str(ckpt),
                "is_active": is_active,
                **meta,
            }
        )
    return out


def activate_checkpoint(name: str) -> bool:
    """Make a saved checkpoint the active one."""
    ckpt_dir = _checkpoints_dir()
    src = ckpt_dir / name
    if not src.exists():
        return False
    active_path = _default_checkpoint_path()
    active_path.write_bytes(src.read_bytes())
    initialize_model(active_path)
    return True
