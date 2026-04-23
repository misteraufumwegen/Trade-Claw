"""
SQLAlchemy ORM models for database persistence
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Enum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.core.database import Base

class OrderStatus(str, enum.Enum):
    """Order status enum"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(str, enum.Enum):
    """Order type enum"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class OrderModel(Base):
    """Order database model"""
    __tablename__ = "orders"
    
    id = Column(String(50), primary_key=True)
    instrument = Column(String(20), nullable=False, index=True)
    units = Column(Integer, nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, index=True)
    price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    filled_price = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    external_id = Column(String(50), unique=True, nullable=True)  # OANDA order ID
    
    def __repr__(self):
        return f"<Order {self.id} {self.instrument} {self.units} units>"

class PositionModel(Base):
    """Position database model"""
    __tablename__ = "positions"
    
    id = Column(String(50), primary_key=True)
    instrument = Column(String(20), nullable=False, unique=True, index=True)
    units = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    percentage_return = Column(Float, nullable=False)
    pip_value = Column(Float, nullable=False)
    opened_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)
    external_id = Column(String(50), unique=True, nullable=True)  # OANDA position ID
    
    def __repr__(self):
        return f"<Position {self.instrument} {self.units} units>"

class BacktestModel(Base):
    """Backtest database model"""
    __tablename__ = "backtests"
    
    id = Column(String(50), primary_key=True)
    instrument = Column(String(20), nullable=False, index=True)
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    strategy = Column(String(50), nullable=False)
    initial_balance = Column(Float, nullable=False)
    risk_per_trade = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, index=True)
    statistics_json = Column(Text, nullable=True)  # JSON string of statistics
    trades_json = Column(Text, nullable=True)  # JSON string of trades
    equity_curve_json = Column(Text, nullable=True)  # JSON string of equity curve
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Backtest {self.id} {self.instrument}>"
