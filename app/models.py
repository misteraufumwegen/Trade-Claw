"""
SQLAlchemy Models for Trading Bot Database

Models:
- User: Broker user account
- CredentialsVault: Encrypted API keys/tokens
- Trade: Executed trades (orders)
- AuditLog: System events and activity log
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class OrderStatus(PyEnum):
    """Order status enumeration."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(PyEnum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class BrokerType(PyEnum):
    """Broker type enumeration."""

    ALPACA = "alpaca"
    OANDA = "oanda"


class User(Base):
    """User/Broker account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    broker = Column(String(50), nullable=False)  # alpaca, oanda, etc.
    account_id = Column(String(255), nullable=False)
    is_sandbox = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    credentials = relationship(
        "CredentialsVault", back_populates="user", cascade="all, delete-orphan"
    )
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
    )


class CredentialsVault(Base):
    """Encrypted API credentials."""

    __tablename__ = "credentials_vault"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key_name = Column(String(255), nullable=False)  # e.g., "api_key", "secret_key", "token"
    encrypted_value = Column(Text, nullable=False)
    broker = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="credentials")

    __table_args__ = (
        Index("idx_credentials_user_id", "user_id"),
        Index("idx_credentials_key_name", "key_name"),
        Index("idx_credentials_broker", "broker"),
    )


class Trade(Base):
    """Executed trade/order record."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(String(255), unique=True, index=True, nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    broker = Column(String(50), nullable=False)
    order_type = Column(String(50), nullable=False)  # market, limit, stop, stop_limit
    side = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # For limit orders
    stop_price = Column(Float, nullable=True)  # For stop orders
    filled_quantity = Column(Float, default=0.0)
    filled_price = Column(Float, nullable=True)  # Avg fill price
    status = Column(String(50), nullable=False)  # pending, filled, cancelled, rejected
    commission = Column(Float, default=0.0)
    profit_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    filled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="trades")

    __table_args__ = (
        Index("idx_trades_user_id", "user_id"),
        Index("idx_trades_order_id", "order_id"),
        Index("idx_trades_symbol", "symbol"),
        Index("idx_trades_status", "status"),
        Index("idx_trades_created_at", "created_at"),
    )


class AuditLog(Base):
    """System audit log."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=False)  # user, trade, credentials
    resource_id = Column(String(255), nullable=True)
    changes = Column(Text, nullable=True)  # JSON string of changes
    status = Column(String(50), nullable=False)  # success, failure
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource_type", "resource_type"),
        Index("idx_audit_created_at", "created_at"),
    )
