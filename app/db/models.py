"""SQLAlchemy models for Trade-Claw database."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class BrokerSession(Base):
    """Manages broker authentication sessions per user."""

    __tablename__ = "broker_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)
    broker_type = Column(String(50), nullable=False)  # alpaca, oanda, hyperliquid, mock
    credentials_vault_key = Column(String(255), nullable=False)  # Reference to encrypted vault
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_id = Column(String(255), unique=True, index=True, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="broker_session", cascade="all, delete-orphan")
    positions = relationship(
        "Position", back_populates="broker_session", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="broker_session", cascade="all, delete-orphan"
    )
    risk_limits = relationship(
        "RiskLimit", back_populates="broker_session", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_user_broker", "user_id", "broker_type"),)


class Order(Base):
    """Immutable trade order records."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(255), ForeignKey("broker_sessions.session_id"), nullable=False, index=True
    )
    order_id = Column(String(255), unique=True, index=True, nullable=False)  # Broker's order ID
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY or SELL
    size = Column(Numeric(18, 8), nullable=False)
    entry_price = Column(Numeric(18, 8), nullable=False)
    stop_loss = Column(Numeric(18, 8), nullable=False)
    take_profit = Column(Numeric(18, 8), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, FILLED, REJECTED, CANCELLED
    filled_size = Column(Numeric(18, 8), default=0)
    avg_fill_price = Column(Numeric(18, 8), nullable=True)
    commission = Column(Numeric(18, 8), default=0)
    pnl = Column(Numeric(18, 8), nullable=True)  # Realized P&L
    unrealized_pnl = Column(Numeric(18, 8), nullable=True)  # Current unrealized P&L
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    risk_ratio = Column(Numeric(18, 8), nullable=True)  # R/R ratio validation (Decimal, H5)
    # Client-supplied idempotency key (H4).
    # UNIQUE per session, so identical retries return the same order.
    idempotency_key = Column(String(128), nullable=True, index=True)

    # Relationships
    broker_session = relationship("BrokerSession", back_populates="orders")

    __table_args__ = (
        Index("idx_session_symbol_timestamp", "session_id", "symbol", "timestamp"),
        Index(
            "uq_orders_session_idempotency_key",
            "session_id",
            "idempotency_key",
            unique=True,
            # `postgresql_where` excludes NULLs so old orders without a key
            # don't collide. For SQLite we just live with index-over-NULL.
            postgresql_where=Column("idempotency_key").isnot(None),
        ),
    )


class Position(Base):
    """Active trading positions."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(255), ForeignKey("broker_sessions.session_id"), nullable=False, index=True
    )
    symbol = Column(String(20), nullable=False, index=True)
    entry_price = Column(Numeric(18, 8), nullable=False)
    current_price = Column(Numeric(18, 8), nullable=False)
    size = Column(Numeric(18, 8), nullable=False)
    side = Column(String(10), nullable=False)  # LONG or SHORT
    unrealized_pnl = Column(Numeric(18, 8), nullable=False, default=0)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED, LIQUIDATED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    broker_session = relationship("BrokerSession", back_populates="positions")

    __table_args__ = (Index("idx_session_symbol_status", "session_id", "symbol", "status"),)


class AuditLog(Base):
    """Immutable append-only audit trail (from PHASE 3)."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(255), ForeignKey("broker_sessions.session_id"), nullable=False, index=True
    )
    action = Column(
        String(50), nullable=False
    )  # ORDER_SUBMITTED, ORDER_FILLED, POSITION_CLOSED, etc.
    symbol = Column(String(20), nullable=True)
    details = Column(Text, nullable=False)  # JSON payload
    hash_chain = Column(String(512), nullable=True)  # SHA-256 hash for integrity
    severity = Column(String(20), default="INFO")  # INFO, WARNING, ERROR, CRITICAL
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    broker_session = relationship("BrokerSession", back_populates="audit_logs")

    __table_args__ = (Index("idx_session_action_timestamp", "session_id", "action", "timestamp"),)


class RiskLimit(Base):
    """Per-user risk configuration and limits."""

    __tablename__ = "risk_limits"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(255), ForeignKey("broker_sessions.session_id"), nullable=False, unique=True
    )
    max_position_size_pct = Column(Float, default=0.10)  # 10% of account
    max_drawdown_pct = Column(Float, default=-0.15)  # -15% hard stop
    max_daily_loss_pct = Column(Float, default=-0.20)  # -20% per day
    min_risk_reward_ratio = Column(Float, default=1.5)  # 1.5:1 minimum
    sl_immutable = Column(Boolean, default=True)  # Cannot move stop loss after order
    halt_on_breach = Column(Boolean, default=True)  # Halt all orders on drawdown breach
    current_drawdown_pct = Column(Float, default=0.0)
    current_daily_loss_pct = Column(Float, default=0.0)
    is_halted = Column(Boolean, default=False)  # Halt flag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    broker_session = relationship("BrokerSession", back_populates="risk_limits")

    __table_args__ = (Index("idx_session_halt_status", "session_id", "is_halted"),)


class VaultSecret(Base):
    """Encrypted credential vault storage (C3).

    The column ``ciphertext`` holds Fernet ciphertext — never plaintext.
    Access is mediated through ``app.vault.Vault``.
    """

    __tablename__ = "vault_secrets"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    ciphertext = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
