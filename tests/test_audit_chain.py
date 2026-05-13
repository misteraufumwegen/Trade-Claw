"""
Tests for the SHA-256 hash chain that makes the audit log tamper-evident.

Covers:
- Pure compute_hash (deterministic, sensitive to every input)
- before_insert listener populates hash_chain on every new row
- Chain verifies clean across many rows
- Editing a row's content is detected
- Deleting a middle row is detected (subsequent rows' prev_hash invalid)
- Pre-chain rows (hash_chain=NULL) are tolerated and resync the chain
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AuditLog, Base, BrokerSession
from app.security.audit_chain import (
    attach_listener,
    compute_hash,
    reset_listener_for_test,
    verify_chain,
)


@pytest.fixture(scope="module", autouse=True)
def _wire_listener():
    """Attach the before_insert listener once for this test module."""
    reset_listener_for_test()
    attach_listener()
    yield
    # Leave it attached — other tests using AuditLog also benefit.


@pytest.fixture
def session() -> Session:
    """Fresh in-memory SQLite per test so chains start clean."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Maker = sessionmaker(bind=engine)
    s = Maker()
    # Bootstrap a broker_session referenced by AuditLog FK.
    s.add(
        BrokerSession(
            session_id="s-test",
            user_id="u",
            broker_type="mock",
            credentials_vault_key="k",
            is_active=True,
        )
    )
    s.commit()
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Pure compute_hash
# ---------------------------------------------------------------------------


def test_compute_hash_is_deterministic():
    ts = datetime(2026, 5, 13, 12, 0)
    h1 = compute_hash(None, ts, "s", "ACT", "BTC", "details", "INFO")
    h2 = compute_hash(None, ts, "s", "ACT", "BTC", "details", "INFO")
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_sensitive_to_every_field():
    ts = datetime(2026, 5, 13, 12, 0)
    base = compute_hash(None, ts, "s", "ACT", "BTC", "details", "INFO")
    # Each variation must produce a different hash.
    assert base != compute_hash("a", ts, "s", "ACT", "BTC", "details", "INFO")
    assert base != compute_hash(None, datetime(2026, 5, 14), "s", "ACT", "BTC", "details", "INFO")
    assert base != compute_hash(None, ts, "OTHER", "ACT", "BTC", "details", "INFO")
    assert base != compute_hash(None, ts, "s", "OTHER", "BTC", "details", "INFO")
    assert base != compute_hash(None, ts, "s", "ACT", "ETH", "details", "INFO")
    assert base != compute_hash(None, ts, "s", "ACT", "BTC", "tampered", "INFO")
    assert base != compute_hash(None, ts, "s", "ACT", "BTC", "details", "WARNING")


# ---------------------------------------------------------------------------
# Listener populates hash_chain
# ---------------------------------------------------------------------------


def test_listener_chains_inserts(session: Session):
    e1 = AuditLog(session_id="s-test", action="A1", details="d1", severity="INFO")
    e2 = AuditLog(session_id="s-test", action="A2", details="d2", severity="INFO")
    e3 = AuditLog(session_id="s-test", action="A3", details="d3", severity="INFO")
    session.add_all([e1, e2, e3])
    session.commit()

    for entry in (e1, e2, e3):
        session.refresh(entry)
        assert entry.hash_chain is not None
        assert len(entry.hash_chain) == 64

    # Hashes must differ from each other (chain links them sequentially).
    assert e1.hash_chain != e2.hash_chain != e3.hash_chain


def test_verify_chain_intact(session: Session):
    for i in range(5):
        session.add(
            AuditLog(
                session_id="s-test",
                action="STEP",
                symbol="BTC",
                details=f"d{i}",
                severity="INFO",
            )
        )
    session.commit()
    result = verify_chain(session)
    assert result["valid"] is True
    assert result["rows_checked"] == 5
    assert result["first_break_id"] is None


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------


def test_editing_a_row_is_detected(session: Session):
    rows = [
        AuditLog(session_id="s-test", action="STEP", details=f"d{i}", severity="INFO")
        for i in range(5)
    ]
    session.add_all(rows)
    session.commit()
    target_id = rows[2].id
    target_old_details = rows[2].details

    # Bypass any application-level immutability by raw UPDATE.
    session.execute(
        AuditLog.__table__.update().where(AuditLog.id == target_id).values(details="TAMPERED")
    )
    session.commit()

    result = verify_chain(session)
    assert result["valid"] is False
    assert result["first_break_id"] == target_id
    assert "hash mismatch" in result["first_break_reason"]
    # Sanity: we did change something
    assert target_old_details != "TAMPERED"


def test_deleting_middle_row_is_detected(session: Session):
    rows = [
        AuditLog(session_id="s-test", action="STEP", details=f"d{i}", severity="INFO")
        for i in range(5)
    ]
    session.add_all(rows)
    session.commit()
    victim_id = rows[2].id

    session.execute(AuditLog.__table__.delete().where(AuditLog.id == victim_id))
    session.commit()

    result = verify_chain(session)
    # The row after the deleted one now references the deleted row's hash,
    # which is no longer adjacent, so verification breaks at row #4 (now
    # immediately after the gap).
    assert result["valid"] is False
    assert result["first_break_id"] is not None


def test_pre_chain_rows_resync_the_chain(session: Session):
    # Simulate a row inserted before the chain was wired up (no hash).
    session.execute(
        AuditLog.__table__.insert().values(
            session_id="s-test",
            action="PRE_CHAIN",
            details="legacy",
            severity="INFO",
            timestamp=datetime.utcnow(),
            hash_chain=None,
        )
    )
    session.commit()

    # New chained rows go in. They should verify just fine — the chain
    # resyncs after the gap caused by the NULL row.
    session.add(AuditLog(session_id="s-test", action="A", details="d", severity="INFO"))
    session.add(AuditLog(session_id="s-test", action="B", details="d", severity="INFO"))
    session.commit()

    result = verify_chain(session)
    assert result["valid"] is True
    assert result["rows_checked"] == 3


# ---------------------------------------------------------------------------
# Limit (tail-only) walk
# ---------------------------------------------------------------------------


def test_verify_chain_with_limit_walks_only_recent(session: Session):
    for i in range(10):
        session.add(AuditLog(session_id="s-test", action="STEP", details=f"d{i}", severity="INFO"))
    session.commit()
    result = verify_chain(session, limit=3)
    assert result["valid"] is True
    assert result["rows_checked"] == 3


def test_verify_chain_empty_table(session: Session):
    result = verify_chain(session)
    assert result["valid"] is True
    assert result["rows_checked"] == 0
    result_limited = verify_chain(session, limit=10)
    assert result_limited["valid"] is True
    assert result_limited["rows_checked"] == 0
