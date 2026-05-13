"""
Cross-cutting safety gates: defensive checks that apply to every order path
(manual UI, REST API, autopilot webhook).

These complement :mod:`app.risk.engine` rather than replacing it. Each gate is
a pure function (easy to test, no I/O) except for the consecutive-loss
cooldown, which owns a tiny module-level state machine fed by the outcome
poller in ``app.main``.

Why a separate module: the production path (``DBRiskEngine``) and the
standalone path (``RiskEngine``) need the same defensive caps without
duplicating logic, and the autopilot webhook needs cooldown awareness
before it even calls the engine. A single import point keeps these
contracts in one place.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Env helpers — read at call time so tests can monkeypatch
# ---------------------------------------------------------------------------


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Stop-loss distance cap
# ---------------------------------------------------------------------------


def validate_sl_distance(
    entry_price: float,
    stop_loss: float,
    cap_pct: float | None = None,
) -> tuple[bool, str, float]:
    """Reject orders whose stop-loss is further than ``cap_pct`` away from
    the entry price.

    Defends against malformed TradingView payloads or a model that proposes
    a self-destructive stop. Returns ``(valid, reason, distance_pct)``.
    """
    if cap_pct is None:
        cap_pct = _env_float("MAX_SL_DISTANCE_PCT", 5.0)
    if entry_price <= 0:
        return False, "INVALID: entry_price must be > 0", 0.0
    distance_pct = abs(entry_price - stop_loss) / entry_price * 100.0
    if distance_pct > cap_pct:
        return (
            False,
            f"SL_DISTANCE: {distance_pct:.2f}% exceeds cap of {cap_pct:.2f}%",
            distance_pct,
        )
    return True, "OK", distance_pct


# ---------------------------------------------------------------------------
# Consecutive-loss cooldown — module-level state machine
# ---------------------------------------------------------------------------


_consecutive_losses: int = 0
_cooldown_until: datetime | None = None


def _maybe_clear_cooldown() -> None:
    """If the cooldown timer has elapsed, drop it and reset the counter."""
    global _cooldown_until, _consecutive_losses
    if _cooldown_until is not None and datetime.utcnow() >= _cooldown_until:
        _cooldown_until = None
        _consecutive_losses = 0


def record_outcome(label: str) -> None:
    """Track a single trade outcome. Call this from the outcome poller after
    a position is resolved. ``label`` is "WIN" or "LOSS" (case-insensitive,
    anything else is ignored)."""
    global _consecutive_losses, _cooldown_until
    norm = (label or "").strip().upper()
    if norm == "LOSS":
        _consecutive_losses += 1
        cap = _env_int("MAX_CONSECUTIVE_LOSSES", 3)
        if _consecutive_losses >= cap and _cooldown_until is None:
            cooldown_min = _env_int("COOLDOWN_MINUTES", 60)
            _cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_min)
            logger.warning(
                "Consecutive-loss cooldown engaged: %d losses, %d min pause",
                _consecutive_losses,
                cooldown_min,
            )
    elif norm == "WIN":
        if _consecutive_losses > 0 or _cooldown_until is not None:
            logger.info("Win recorded — consecutive-loss counter reset")
        _consecutive_losses = 0
        _cooldown_until = None


def is_in_cooldown() -> tuple[bool, str | None]:
    """Return ``(True, reason)`` while the cooldown is active. Side-effects:
    auto-clears the state if the timer has elapsed."""
    _maybe_clear_cooldown()
    if _cooldown_until is None:
        return False, None
    remaining = _cooldown_until - datetime.utcnow()
    minutes_left = int(remaining.total_seconds() // 60) + 1
    return (
        True,
        f"COOLDOWN: {_consecutive_losses} consecutive losses, {minutes_left} min remaining",
    )


def cooldown_status() -> dict:
    """Diagnostic snapshot — safe to expose via API."""
    _maybe_clear_cooldown()
    return {
        "consecutive_losses": _consecutive_losses,
        "max_consecutive_losses": _env_int("MAX_CONSECUTIVE_LOSSES", 3),
        "cooldown_until": _cooldown_until.isoformat() if _cooldown_until else None,
        "cooldown_minutes": _env_int("COOLDOWN_MINUTES", 60),
    }


def reset_cooldown_for_test() -> None:
    """Reset module state. Used by tests; not exported via __init__."""
    global _consecutive_losses, _cooldown_until
    _consecutive_losses = 0
    _cooldown_until = None


# ---------------------------------------------------------------------------
# Dry-run minimum before live transition
# ---------------------------------------------------------------------------


def count_dry_run_would_submits(history: list[dict[str, Any]]) -> int:
    """Count how many decisions in the autopilot history were dry-run trades
    that *would* have submitted in live mode. These are the meaningful
    rehearsal data points."""
    # All forms the autopilot pipeline currently emits when the pipeline
    # cleared every gate and the only thing stopping a real order was the
    # dry_run mode flag. Keep this list aligned with main.tradingview_webhook.
    accepted = {"would_submit", "submitted", "dry_run_submit", "approved_dry_run"}
    n = 0
    for entry in history:
        if entry.get("mode") != "dry_run":
            continue
        if entry.get("decision", "") in accepted:
            n += 1
    return n


def validate_dry_run_record(
    history: list[dict[str, Any]],
    min_count: int | None = None,
) -> tuple[bool, str | None]:
    """Gate the dry_run → live transition. Returns ``(ok, reason)``."""
    if min_count is None:
        min_count = _env_int("MIN_DRY_RUN_TRADES", 20)
    actual = count_dry_run_would_submits(history)
    if actual < min_count:
        return (
            False,
            f"DRY_RUN_INSUFFICIENT: only {actual}/{min_count} would-submit "
            f"dry-run trades recorded. Run dry_run longer or pass force=true.",
        )
    return True, None


# ---------------------------------------------------------------------------
# TradingView webhook IP allowlist
# ---------------------------------------------------------------------------


# Publicly documented TradingView outgoing IPs as of 2026-05. Treat as
# advisory — users who tunnel via Cloudflared see the tunnel egress IPs and
# should rely on CF-Connecting-IP instead.
TRADINGVIEW_PUBLIC_IPS: tuple[str, ...] = (
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7",
)


def get_real_client_ip(headers: dict[str, str], fallback: str = "") -> str:
    """Resolve the real client IP, accounting for Cloudflare tunnels and
    generic reverse proxies. Header keys are matched case-insensitively
    (caller should pass a normalized dict)."""
    norm = {k.lower(): v for k, v in headers.items()}
    cf = norm.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xff = norm.get("x-forwarded-for")
    if xff:
        # XFF is comma-separated, left-most is the original client
        return xff.split(",")[0].strip()
    return fallback or ""


def is_ip_allowed(client_ip: str, allowlist_csv: str) -> bool:
    """Check if ``client_ip`` is in ``allowlist_csv``. Empty allowlist means
    "no allowlist configured" → allow all (preserves current behaviour)."""
    raw = (allowlist_csv or "").strip()
    if not raw:
        return True
    allowed = {ip.strip() for ip in raw.split(",") if ip.strip()}
    return client_ip in allowed
