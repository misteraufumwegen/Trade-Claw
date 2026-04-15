"""
Audit Log
Security audit trail for all orders, sessions, and risk events.
Implements Milan's security requirements.

Logged events:
- Order submissions/fills/cancellations
- Session creation/closure
- Risk limit violations
- Credential changes
- Emergency halts
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib


logger = logging.getLogger('AuditLog')


@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: datetime
    action: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    order_id: Optional[str] = None
    broker: Optional[str] = None
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = "INFO"  # INFO, WARNING, CRITICAL
    
    def to_dict(self) -> Dict:
        """Convert to dict for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON"""
        return json.dumps(self.to_dict())


class AuditLog:
    """
    Audit logging system.
    
    Features:
    - Log to file (append-only, immutable)
    - In-memory cache for recent events
    - Severity filtering
    - User/session/order tracking
    - Integrity verification (hash chain)
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_memory_events: int = 1000,
    ):
        """
        Initialize audit log.
        
        Args:
            log_dir: Directory for audit files (default: ~/.openclaw/audit)
            max_memory_events: Keep last N events in memory
        """
        
        self.log_dir = log_dir or Path.home() / '.openclaw' / 'audit'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_memory = max_memory_events
        self.memory_events: List[AuditEntry] = []
        
        # Hash chain for integrity
        self.last_hash = "0"
        
        # Current session log file
        self.log_file = self._get_log_file()
        
        logger.info(f"AuditLog initialized: {self.log_file}")
    
    def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        order_id: Optional[str] = None,
        broker: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict] = None,
        severity: str = "INFO",
    ) -> AuditEntry:
        """
        Log an event.
        
        Args:
            action: Event type (e.g., "ORDER_SUBMITTED", "SESSION_CREATED", "RISK_LIMIT_EXCEEDED")
            user_id: User identifier
            session_id: Session identifier
            order_id: Order identifier
            broker: Broker name
            reason: Reason for action
            details: Additional context
            severity: INFO, WARNING, CRITICAL
        
        Returns:
            AuditEntry (for reference)
        """
        
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            action=action,
            user_id=user_id,
            session_id=session_id,
            order_id=order_id,
            broker=broker,
            reason=reason,
            details=details or {},
            severity=severity,
        )
        
        # Store in memory (circular buffer)
        self.memory_events.append(entry)
        if len(self.memory_events) > self.max_memory:
            self.memory_events.pop(0)
        
        # Write to file
        self._write_entry(entry)
        
        # Log via Python logger
        log_level = {
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "CRITICAL": logging.CRITICAL,
        }.get(severity, logging.INFO)
        
        logger.log(
            log_level,
            f"{action} | user={user_id} session={session_id} order={order_id} | {reason}",
        )
        
        return entry
    
    def _write_entry(self, entry: AuditEntry):
        """Write entry to log file (append-only)"""
        try:
            # Update hash chain
            entry_data = entry.to_dict()
            entry_json = json.dumps(entry_data, sort_keys=True)
            
            # Hash this entry + last hash (prevents tampering)
            integrity_hash = hashlib.sha256(
                f"{self.last_hash}{entry_json}".encode()
            ).hexdigest()
            entry_data['_hash'] = integrity_hash
            
            # Write to file
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry_data) + '\n')
            
            self.last_hash = integrity_hash
        
        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")
    
    def get_recent(self, limit: int = 100, severity: Optional[str] = None) -> List[AuditEntry]:
        """Get recent audit events from memory"""
        events = self.memory_events[-limit:]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return events
    
    def get_for_user(self, user_id: str, limit: int = 100) -> List[AuditEntry]:
        """Get audit events for a specific user"""
        return [
            e for e in self.memory_events[-limit:]
            if e.user_id == user_id
        ]
    
    def get_for_order(self, order_id: str) -> List[AuditEntry]:
        """Get all events for an order"""
        return [
            e for e in self.memory_events
            if e.order_id == order_id
        ]
    
    def get_for_session(self, session_id: str) -> List[AuditEntry]:
        """Get all events for a session"""
        return [
            e for e in self.memory_events
            if e.session_id == session_id
        ]
    
    def get_by_action(self, action: str, limit: int = 100) -> List[AuditEntry]:
        """Get events by action type"""
        return [
            e for e in self.memory_events[-limit:]
            if e.action == action
        ]
    
    def get_critical_events(self, limit: int = 50) -> List[AuditEntry]:
        """Get critical severity events"""
        return [
            e for e in self.memory_events[-limit:]
            if e.severity == "CRITICAL"
        ]
    
    def export(self, filepath: Path, user_id: Optional[str] = None):
        """Export audit trail to file"""
        try:
            events = self.get_for_user(user_id) if user_id else self.memory_events
            
            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "event_count": len(events),
                "events": [e.to_dict() for e in events],
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Audit trail exported to {filepath}")
        
        except Exception as e:
            logger.error(f"Failed to export audit trail: {e}")
    
    def _get_log_file(self) -> Path:
        """Get current log file (daily rotation)"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{today}.jsonl"


class AuditSummary:
    """Generate audit summaries for compliance/review"""
    
    @staticmethod
    def summary_by_action(audit_log: AuditLog, hours: int = 24) -> Dict[str, int]:
        """Count events by action in last N hours"""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        events = [
            e for e in audit_log.memory_events
            if e.timestamp >= cutoff
        ]
        
        summary = {}
        for event in events:
            summary[event.action] = summary.get(event.action, 0) + 1
        
        return summary
    
    @staticmethod
    def summary_by_user(audit_log: AuditLog) -> Dict[str, int]:
        """Count events by user"""
        summary = {}
        for event in audit_log.memory_events:
            if event.user_id:
                summary[event.user_id] = summary.get(event.user_id, 0) + 1
        return summary
    
    @staticmethod
    def summary_by_severity(audit_log: AuditLog) -> Dict[str, int]:
        """Count events by severity"""
        summary = {}
        for event in audit_log.memory_events:
            summary[event.severity] = summary.get(event.severity, 0) + 1
        return summary
    
    @staticmethod
    def compliance_report(audit_log: AuditLog, user_id: str) -> Dict[str, Any]:
        """Generate compliance report for user"""
        events = audit_log.get_for_user(user_id)
        
        return {
            "user_id": user_id,
            "period": f"{events[0].timestamp.isoformat() if events else 'N/A'} - {datetime.utcnow().isoformat()}",
            "total_events": len(events),
            "orders_submitted": len([e for e in events if e.action == "ORDER_SUBMITTED"]),
            "orders_filled": len([e for e in events if e.action == "ORDER_FILLED"]),
            "orders_cancelled": len([e for e in events if e.action == "ORDER_CANCELLED"]),
            "risk_violations": len([e for e in events if "RISK" in e.action]),
            "critical_events": len([e for e in events if e.severity == "CRITICAL"]),
            "events": [e.to_dict() for e in events],
        }
