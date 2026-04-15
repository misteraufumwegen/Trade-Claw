"""FastAPI REST API for Trade-Claw."""

import os
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import init_db, get_db_session
from app.db.models import BrokerSession, Order, Position, AuditLog, RiskLimit
from app.risk import RiskEngine, RiskValidationResult
from app.routing import BrokerSessionRouter
from app.logging_config import setup_logging, get_logger

# Initialize logging
logger = setup_logging(
    log_file=os.getenv("LOG_FILE", "trade_claw.log"),
    level=os.getenv("LOG_LEVEL", "INFO"),
)

# Initialize database
init_db()

# Initialize FastAPI app
app = FastAPI(
    title="Trade-Claw API",
    description="Production-ready trading API with multi-broker support",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize broker router
router = BrokerSessionRouter()


# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================


class BrokerSetupRequest(BaseModel):
    """Broker setup request."""
    broker_type: str = Field(..., description="alpaca, oanda, hyperliquid, mock")
    credentials: dict = Field(..., description="Broker credentials (API keys, etc.)")
    user_id: Optional[str] = Field(None, description="User ID (optional)")


class BrokerSetupResponse(BaseModel):
    """Broker setup response."""
    session_id: str
    broker_type: str
    status: str = "ACTIVE"
    created_at: datetime
    message: str


class PriceQuoteRequest(BaseModel):
    """Price quote request."""
    symbol: str
    amount: Optional[Decimal] = None


class PriceQuoteResponse(BaseModel):
    """Price quote response."""
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    liquidity: str = "HIGH"
    estimated_fees: Decimal = Decimal("0")


class OrderSubmitRequest(BaseModel):
    """Order submission request."""
    symbol: str
    side: str = Field(..., description="BUY or SELL")
    size: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal


class OrderSubmitResponse(BaseModel):
    """Order submission response."""
    order_id: str
    status: str
    symbol: str
    side: str
    size: Decimal
    entry_price: Decimal
    created_at: datetime
    message: str
    risk_ratio: Optional[float] = None


class OrderStatusResponse(BaseModel):
    """Order status response."""
    order_id: str
    status: str
    symbol: str
    side: str
    size: Decimal
    filled_size: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    commission: Decimal = Decimal("0")
    pnl: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    created_at: datetime
    filled_at: Optional[datetime] = None


class PositionResponse(BaseModel):
    """Active position response."""
    symbol: str
    side: str
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    pnl_pct: float
    status: str


class PositionListResponse(BaseModel):
    """List of active positions."""
    positions: List[PositionResponse]
    total_unrealized_pnl: Decimal
    total_pnl_pct: float
    drawdown_pct: float
    is_halted: bool


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: int
    action: str
    symbol: Optional[str] = None
    details: str
    severity: str
    timestamp: datetime


class AuditLogExportResponse(BaseModel):
    """Audit log export response."""
    logs: List[AuditLogResponse]
    total_count: int
    format: str = "json"


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "4.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Trade-Claw API",
        "version": "4.0.0",
        "description": "Multi-broker trading API with risk management",
        "docs": "/docs",
    }


# ============================================================================
# BROKER SETUP ENDPOINTS
# ============================================================================


@app.post("/api/v1/brokers/setup", response_model=BrokerSetupResponse)
async def setup_broker(
    request: BrokerSetupRequest,
    db: Session = Depends(get_db_session),
):
    """
    Setup broker connection and create session.
    
    This endpoint:
    1. Validates broker type
    2. Authenticates credentials
    3. Creates broker session
    4. Initializes risk limits
    5. Returns session ID for future requests
    """
    try:
        # Create broker session via router
        session_id = await router.create_session(
            user_id=request.user_id or "default",
            broker_type=request.broker_type,
            credentials=request.credentials,
        )

        # Store in database
        broker_session = BrokerSession(
            user_id=request.user_id or "default",
            broker_type=request.broker_type,
            credentials_vault_key=f"vault:{session_id}",
            session_id=session_id,
        )
        db.add(broker_session)

        # Initialize risk limits
        risk_limit = RiskLimit(
            session_id=session_id,
            max_position_size_pct=0.10,  # 10%
            max_drawdown_pct=-0.15,  # -15%
            min_risk_reward_ratio=1.5,
        )
        db.add(risk_limit)
        db.commit()

        logger.info(f"Broker setup successful: {request.broker_type} - {session_id}")

        return BrokerSetupResponse(
            session_id=session_id,
            broker_type=request.broker_type,
            created_at=datetime.utcnow(),
            message=f"Successfully connected to {request.broker_type}",
        )

    except Exception as e:
        logger.error(f"Broker setup failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# QUOTE ENDPOINTS
# ============================================================================


@app.get("/api/v1/brokers/{session_id}/quote", response_model=PriceQuoteResponse)
async def get_quote(
    session_id: str,
    symbol: str = Query(...),
    amount: Optional[Decimal] = None,
    db: Session = Depends(get_db_session),
):
    """
    Get price quote for symbol.
    
    Args:
        session_id: Broker session ID
        symbol: Trading symbol (e.g., BTC/USD)
        amount: Optional amount for liquidity check
    
    Returns:
        Current bid/ask/last prices
    """
    try:
        # Fetch broker session
        broker_session = db.query(BrokerSession).filter(
            BrokerSession.session_id == session_id
        ).first()

        if not broker_session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get adapter
        adapter = await router.get_api_adapter(session_id)

        # Get quote
        quote = await adapter.get_quote(symbol, amount or Decimal(1))

        return PriceQuoteResponse(
            symbol=symbol,
            bid=quote.bid,
            ask=quote.ask,
            last=quote.last,
            liquidity=quote.liquidity,
            estimated_fees=quote.estimated_fees or Decimal("0"),
        )

    except Exception as e:
        logger.error(f"Quote fetch failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================


@app.post("/api/v1/orders/submit", response_model=OrderSubmitResponse)
async def submit_order(
    session_id: str = Query(...),
    request: OrderSubmitRequest = None,
    db: Session = Depends(get_db_session),
):
    """
    Submit a new order with risk validation.
    
    Performs:
    1. Risk engine validation
    2. Position size checks
    3. R/R ratio validation
    4. Drawdown limit check
    5. Order submission to broker
    6. Audit logging
    """
    try:
        # Fetch broker session
        broker_session = db.query(BrokerSession).filter(
            BrokerSession.session_id == session_id
        ).first()

        if not broker_session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get risk engine
        risk_engine = RiskEngine(db)

        # Get account balance (simplified)
        adapter = await router.get_api_adapter(session_id)
        account_info = await adapter.get_account_info()
        account_balance = Decimal(str(account_info.get("balance", 10000)))

        # Validate order
        validation = risk_engine.validate_order(
            session_id=session_id,
            account_balance=account_balance,
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )

        if not validation.approved:
            # Log rejection
            audit_log = AuditLog(
                session_id=session_id,
                action="ORDER_REJECTED",
                symbol=request.symbol,
                details=validation.message,
                severity="WARNING",
            )
            db.add(audit_log)
            db.commit()

            raise HTTPException(
                status_code=400,
                detail=f"Order rejected: {validation.message}",
            )

        # Submit to broker
        order = await adapter.submit_order(
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry=request.entry_price,
            sl=request.stop_loss,
            tp=request.take_profit,
        )

        # Store in database
        db_order = Order(
            session_id=session_id,
            order_id=order.order_id,
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            status=order.status,
            risk_ratio=(request.take_profit - request.entry_price) / (request.entry_price - request.stop_loss)
            if request.entry_price != request.stop_loss
            else None,
        )
        db.add(db_order)

        # Audit log
        audit_log = AuditLog(
            session_id=session_id,
            action="ORDER_SUBMITTED",
            symbol=request.symbol,
            details=f"Order {order.order_id} submitted: {request.side} {request.size} @ {request.entry_price}",
            severity="INFO",
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Order submitted: {order.order_id} - {request.symbol}")

        return OrderSubmitResponse(
            order_id=order.order_id,
            status=order.status,
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry_price=request.entry_price,
            created_at=datetime.utcnow(),
            message=f"Order {order.order_id} submitted successfully",
            risk_ratio=db_order.risk_ratio,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order submission failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/orders/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str,
    session_id: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Get order status and fills."""
    try:
        # Fetch from database
        order = db.query(Order).filter(
            Order.order_id == order_id,
            Order.session_id == session_id,
        ).first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return OrderStatusResponse(
            order_id=order.order_id,
            status=order.status,
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            filled_size=order.filled_size,
            avg_fill_price=order.avg_fill_price,
            entry_price=order.entry_price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            commission=order.commission,
            pnl=order.pnl,
            unrealized_pnl=order.unrealized_pnl,
            created_at=order.timestamp,
            filled_at=order.filled_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order status fetch failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    session_id: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Cancel an open order."""
    try:
        # Fetch order
        order = db.query(Order).filter(
            Order.order_id == order_id,
            Order.session_id == session_id,
        ).first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status == "FILLED":
            raise HTTPException(status_code=400, detail="Cannot cancel filled order")

        # Cancel via broker
        adapter = await router.get_api_adapter(session_id)
        await adapter.cancel_order(order_id)

        # Update database
        order.status = "CANCELLED"
        order.cancelled_at = datetime.utcnow()

        # Audit log
        audit_log = AuditLog(
            session_id=session_id,
            action="ORDER_CANCELLED",
            symbol=order.symbol,
            details=f"Order {order_id} cancelled",
            severity="INFO",
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Order cancelled: {order_id}")

        return {"status": "success", "order_id": order_id, "message": "Order cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order cancellation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# POSITION ENDPOINTS
# ============================================================================


@app.get("/api/v1/positions", response_model=PositionListResponse)
async def get_positions(
    session_id: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Get all active positions and account summary."""
    try:
        # Fetch positions
        positions = db.query(Position).filter(
            Position.session_id == session_id,
            Position.status == "OPEN",
        ).all()

        # Fetch risk limits
        risk_limit = db.query(RiskLimit).filter(
            RiskLimit.session_id == session_id
        ).first()

        # Calculate totals
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions) if positions else Decimal("0")
        total_pnl_pct = 0.0

        position_responses = [
            PositionResponse(
                symbol=p.symbol,
                side=p.side,
                size=p.size,
                entry_price=p.entry_price,
                current_price=p.current_price,
                unrealized_pnl=p.unrealized_pnl,
                pnl_pct=float((p.unrealized_pnl / (p.entry_price * p.size) * 100)) if p.entry_price * p.size > 0 else 0,
                status=p.status,
            )
            for p in positions
        ]

        return PositionListResponse(
            positions=position_responses,
            total_unrealized_pnl=total_unrealized_pnl,
            total_pnl_pct=total_pnl_pct,
            drawdown_pct=risk_limit.current_drawdown_pct if risk_limit else 0.0,
            is_halted=risk_limit.is_halted if risk_limit else False,
        )

    except Exception as e:
        logger.error(f"Position fetch failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# AUDIT ENDPOINTS
# ============================================================================


@app.get("/api/v1/audit", response_model=AuditLogExportResponse)
async def get_audit_log(
    session_id: str = Query(...),
    action: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """
    Get immutable audit log.
    
    Supports filtering by:
    - action: ORDER_SUBMITTED, ORDER_FILLED, etc.
    - severity: INFO, WARNING, ERROR, CRITICAL
    - limit/offset: Pagination
    """
    try:
        # Build query
        query = db.query(AuditLog).filter(AuditLog.session_id == session_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if severity:
            query = query.filter(AuditLog.severity == severity)

        # Get total count
        total_count = query.count()

        # Get paginated results
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

        log_responses = [
            AuditLogResponse(
                id=log.id,
                action=log.action,
                symbol=log.symbol,
                details=log.details,
                severity=log.severity,
                timestamp=log.timestamp,
            )
            for log in logs
        ]

        return AuditLogExportResponse(
            logs=log_responses,
            total_count=total_count,
            format="json",
        )

    except Exception as e:
        logger.error(f"Audit log fetch failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
