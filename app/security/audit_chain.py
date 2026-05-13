"""
Tamper-evident audit log via SHA-256 hash chain.

Why this exists:
- ``AuditLog`` already has an application-level immutability test guarding
  against accidental edits through the ORM.
- But anyone with direct DB access can still mutate or delete rows.
- A hash chain makes any such tampering detectable after the fact.

How it works:
Each new ``AuditLog`` row's ``hash_chain`` is computed as::

    SHA256(prev_hash || ts || session_id || action || symbol || details || severity)

Editing any row's content → recompute gives a different hash → mismatch.
Inserting a row in the middle → every subsequent prev_hash is wrong.
Deleting a row → next row's prev_hash points to a now-missing predecessor.

The :func:`attach_listener` function hooks SQLAlchemy's ``before_insert``
event so every existing ``db.add(AuditLog(...))`` call across the app picks
up a chained hash without changes to callers. Verification is the
:func:`verify_chain` walker, exposed via the ``/api/v1/audit/verify``
endpoint.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog

# Session class identifier for event registration. Using the base Session
# class catches any sessionmaker-derived class.
_SessionCls = Session

_listener_attached: bool = False


def compute_hash(
    prev_hash: str | None,
    ts: datetime,
    session_id: str | None,
    action: str,
    symbol: str | None,
    details: str | None,
    severity: str | None,
) -> str:
    """Deterministic SHA-256 over a join of the chain inputs."""
    payload = "|".join(
        [
            prev_hash or "",
            ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
            session_id or "",
            action or "",
            symbol or "",
            details or "",
            severity or "INFO",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def attach_listener() -> None:
    """Register the before_flush hook on Session. Idempotent.

    Uses ``before_flush`` (not ``before_insert``) because the latter fires
    per-row and within a multi-row commit each row's listener would see a
    stale DB head — the prior inserts in the same transaction are not yet
    visible to the connection's SELECT. By processing every pending
    ``AuditLog`` once in flush order we chain them all consistently before
    a single INSERT goes out.
    """
    global _listener_attached
    if _listener_attached:
        return

    @event.listens_for(_SessionCls, "before_flush")
    def _chain_audit_logs(session, flush_context, instances):  # noqa: ARG001
        new_logs = [obj for obj in session.new if isinstance(obj, AuditLog)]
        if not new_logs:
            return
        # Latest already-committed chain head, visible to this session.
        prev_hash = session.execute(
            select(AuditLog.hash_chain).order_by(AuditLog.id.desc()).limit(1)
        ).scalar()
        # Materialise defaults BEFORE hashing so the value stored matches
        # what we hashed. SQLAlchemy applies column defaults during flush
        # right after this event, so we have to do it ourselves.
        for log in new_logs:
            if log.timestamp is None:
                log.timestamp = datetime.utcnow()
            if log.severity is None:
                log.severity = "INFO"
            log.hash_chain = compute_hash(
                prev_hash=prev_hash,
                ts=log.timestamp,
                session_id=log.session_id,
                action=log.action,
                symbol=log.symbol,
                details=log.details,
                severity=log.severity,
            )
            prev_hash = log.hash_chain

    _listener_attached = True


def verify_chain(db: Session, limit: int | None = None) -> dict:
    """Walk the audit log in id order, recompute each hash, compare to stored.

    When ``limit`` is set, only the latest ``limit`` rows are checked (still
    in chronological order). Useful for cheap recent-tampering checks on
    every safety-dashboard refresh.

    Returns
    -------
    dict with keys::

        valid              : bool — True when the whole walked range matches
        rows_checked       : int  — number of rows visited
        first_break_id     : int | None — id of the first mismatched row
        first_break_reason : str | None — short human-readable reason
        chain_head_hash    : str | None — last verified hash (for diagnostics)
    """
    base_q = db.query(AuditLog).order_by(AuditLog.id.asc())
    if limit is not None:
        # Look only at the latest N rows. We still need the predecessor's
        # hash to verify the start of the walked range, so:
        latest_ids = db.query(AuditLog.id).order_by(AuditLog.id.desc()).limit(limit).all()
        if not latest_ids:
            return {
                "valid": True,
                "rows_checked": 0,
                "first_break_id": None,
                "first_break_reason": None,
                "chain_head_hash": None,
            }
        min_id = min(r[0] for r in latest_ids)
        prev_row = (
            db.query(AuditLog).filter(AuditLog.id < min_id).order_by(AuditLog.id.desc()).first()
        )
        prev_hash = prev_row.hash_chain if prev_row else None
        rows_iter = base_q.filter(AuditLog.id >= min_id).yield_per(100)
    else:
        prev_hash = None
        rows_iter = base_q.yield_per(100)

    rows_checked = 0
    last_verified_hash = prev_hash
    for row in rows_iter:
        rows_checked += 1
        if row.hash_chain is None:
            # Pre-chain row (existed before this feature shipped). Break the
            # chain context here — we cannot verify older rows but the chain
            # picks up again at the next row that has a hash.
            prev_hash = None
            continue
        expected = compute_hash(
            prev_hash=prev_hash,
            ts=row.timestamp,
            session_id=row.session_id,
            action=row.action,
            symbol=row.symbol,
            details=row.details,
            severity=row.severity,
        )
        if expected != row.hash_chain:
            return {
                "valid": False,
                "rows_checked": rows_checked,
                "first_break_id": row.id,
                "first_break_reason": (
                    f"hash mismatch at id={row.id} action={row.action!r}: "
                    f"expected={expected[:16]}… stored={row.hash_chain[:16]}…"
                ),
                "chain_head_hash": last_verified_hash,
            }
        prev_hash = row.hash_chain
        last_verified_hash = row.hash_chain

    return {
        "valid": True,
        "rows_checked": rows_checked,
        "first_break_id": None,
        "first_break_reason": None,
        "chain_head_hash": last_verified_hash,
    }


def reset_listener_for_test() -> None:
    """Allow tests to re-attach the listener on a fresh AuditLog class.

    Used only by the test suite; not part of the public surface.
    """
    global _listener_attached
    _listener_attached = False
