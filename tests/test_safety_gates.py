"""
Tests for app.risk.safety_gates — the cross-cutting safety layer.

Covers all four gates the module implements:
- Stop-loss distance cap
- Consecutive-loss cooldown state machine
- Dry-run-minimum validation for autopilot live transition
- TradingView webhook IP allowlist (Cloudflare-tunnel-aware)
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.risk import safety_gates


@pytest.fixture(autouse=True)
def _reset_state():
    """Each test starts from a clean cooldown state."""
    safety_gates.reset_cooldown_for_test()
    yield
    safety_gates.reset_cooldown_for_test()


# ---------------------------------------------------------------------------
# SL distance cap
# ---------------------------------------------------------------------------


def test_sl_distance_within_cap_passes():
    ok, _, pct = safety_gates.validate_sl_distance(100.0, 97.0, cap_pct=5.0)
    assert ok is True
    assert pct == pytest.approx(3.0)


def test_sl_distance_exceeds_cap_rejected():
    ok, reason, pct = safety_gates.validate_sl_distance(100.0, 80.0, cap_pct=5.0)
    assert ok is False
    assert "SL_DISTANCE" in reason
    assert pct == pytest.approx(20.0)


def test_sl_distance_reads_env_default(monkeypatch):
    monkeypatch.setenv("MAX_SL_DISTANCE_PCT", "2.0")
    ok, _, _ = safety_gates.validate_sl_distance(100.0, 97.0)  # 3% > 2% cap
    assert ok is False


def test_sl_distance_zero_entry_rejected():
    ok, reason, _ = safety_gates.validate_sl_distance(0.0, 1.0)
    assert ok is False
    assert "entry_price" in reason


# ---------------------------------------------------------------------------
# Consecutive-loss cooldown
# ---------------------------------------------------------------------------


def test_cooldown_starts_inactive():
    in_cd, reason = safety_gates.is_in_cooldown()
    assert in_cd is False
    assert reason is None


def test_cooldown_engages_after_n_losses(monkeypatch):
    monkeypatch.setenv("MAX_CONSECUTIVE_LOSSES", "3")
    monkeypatch.setenv("COOLDOWN_MINUTES", "60")

    safety_gates.record_outcome("LOSS")
    assert safety_gates.is_in_cooldown()[0] is False  # 1 loss — not yet

    safety_gates.record_outcome("LOSS")
    assert safety_gates.is_in_cooldown()[0] is False  # 2 — still not

    safety_gates.record_outcome("LOSS")
    in_cd, reason = safety_gates.is_in_cooldown()
    assert in_cd is True
    assert "COOLDOWN" in reason


def test_a_win_resets_consecutive_counter(monkeypatch):
    monkeypatch.setenv("MAX_CONSECUTIVE_LOSSES", "3")
    safety_gates.record_outcome("LOSS")
    safety_gates.record_outcome("LOSS")
    safety_gates.record_outcome("WIN")
    safety_gates.record_outcome("LOSS")
    # Streak reset by the win → 1 loss only, no cooldown.
    assert safety_gates.is_in_cooldown()[0] is False


def test_cooldown_auto_expires_when_timer_elapsed(monkeypatch):
    monkeypatch.setenv("MAX_CONSECUTIVE_LOSSES", "1")
    monkeypatch.setenv("COOLDOWN_MINUTES", "60")
    safety_gates.record_outcome("LOSS")
    assert safety_gates.is_in_cooldown()[0] is True

    # Backdate the cooldown deadline.
    safety_gates._cooldown_until = datetime.utcnow() - timedelta(minutes=1)
    in_cd, reason = safety_gates.is_in_cooldown()
    assert in_cd is False
    assert reason is None
    # And the counter is reset too.
    assert safety_gates._consecutive_losses == 0


def test_cooldown_ignores_unknown_outcomes():
    safety_gates.record_outcome("CANCELLED")
    safety_gates.record_outcome("")
    safety_gates.record_outcome("PENDING")
    assert safety_gates._consecutive_losses == 0


def test_cooldown_status_payload():
    safety_gates.record_outcome("LOSS")
    status = safety_gates.cooldown_status()
    assert status["consecutive_losses"] == 1
    assert "max_consecutive_losses" in status
    assert "cooldown_minutes" in status


# ---------------------------------------------------------------------------
# Dry-run minimum
# ---------------------------------------------------------------------------


def test_dry_run_record_counts_would_submits():
    history = [
        {"mode": "dry_run", "decision": "would_submit"},
        {"mode": "dry_run", "decision": "would_submit"},
        {"mode": "dry_run", "decision": "rejected"},
        {"mode": "off", "decision": "ignored"},
        {"mode": "live", "decision": "submitted"},  # not dry_run
    ]
    assert safety_gates.count_dry_run_would_submits(history) == 2


def test_dry_run_validation_pass(monkeypatch):
    monkeypatch.setenv("MIN_DRY_RUN_TRADES", "2")
    history = [
        {"mode": "dry_run", "decision": "would_submit"},
        {"mode": "dry_run", "decision": "would_submit"},
    ]
    ok, reason = safety_gates.validate_dry_run_record(history)
    assert ok is True
    assert reason is None


def test_dry_run_validation_fail(monkeypatch):
    monkeypatch.setenv("MIN_DRY_RUN_TRADES", "5")
    history = [{"mode": "dry_run", "decision": "would_submit"}]
    ok, reason = safety_gates.validate_dry_run_record(history)
    assert ok is False
    assert "DRY_RUN_INSUFFICIENT" in reason
    assert "1/5" in reason


# ---------------------------------------------------------------------------
# IP allowlist
# ---------------------------------------------------------------------------


def test_ip_allowed_with_empty_allowlist_allows_anything():
    assert safety_gates.is_ip_allowed("1.2.3.4", "") is True
    assert safety_gates.is_ip_allowed("", "") is True


def test_ip_allowed_match():
    assert safety_gates.is_ip_allowed("52.89.214.238", "52.89.214.238,1.2.3.4") is True


def test_ip_not_allowed_mismatch():
    assert safety_gates.is_ip_allowed("9.9.9.9", "52.89.214.238,1.2.3.4") is False


def test_get_real_client_ip_prefers_cf_connecting():
    headers = {
        "CF-Connecting-IP": "52.89.214.238",
        "X-Forwarded-For": "1.1.1.1, 2.2.2.2",
    }
    assert safety_gates.get_real_client_ip(headers, fallback="3.3.3.3") == "52.89.214.238"


def test_get_real_client_ip_uses_xff_when_cf_absent():
    headers = {"X-Forwarded-For": "1.1.1.1, 2.2.2.2"}
    assert safety_gates.get_real_client_ip(headers, fallback="3.3.3.3") == "1.1.1.1"


def test_get_real_client_ip_falls_back_to_socket_host():
    assert safety_gates.get_real_client_ip({}, fallback="3.3.3.3") == "3.3.3.3"


def test_get_real_client_ip_is_case_insensitive():
    headers = {"cf-connecting-ip": "52.89.214.238"}
    assert safety_gates.get_real_client_ip(headers) == "52.89.214.238"
