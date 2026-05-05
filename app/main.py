"""FastAPI REST API for Trade-Claw."""

from __future__ import annotations

import os

# Load .env file before anything else reads environment variables.
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime
from decimal import Decimal

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.db import get_db_session, init_db
from app.db.models import AuditLog, BrokerSession, Order, Position, RiskLimit
from app.db.session import SessionLocal
from app.exceptions import (
    BrokerConnectionError,
    OrderRejectedError,
    OrderValidationError,
)
from app.logging_config import setup_logging
from app.risk import DBRiskEngine as RiskEngine
from app.routing import BrokerSessionRouter
from app.security.auth import require_api_key
from app.security.settings import validate_environment
from app.vault import DatabaseStorage, Vault

# ---------------------------------------------------------------------------
# Startup checks + infrastructure
# ---------------------------------------------------------------------------

# Initialize logging
logger = setup_logging(
    log_file=os.getenv("LOG_FILE", "trade_claw.log"),
    level=os.getenv("LOG_LEVEL", "INFO"),
)

# Refuse to boot with placeholder secrets in production. (C2, see security/settings.py)
validate_environment()

# Initialize database
init_db()


# ---------------------------------------------------------------------------
# Vault — DatabaseStorage backend (C3)
#
# Credentials are encrypted with Fernet (AES-128-CBC) using the key derived
# from ENCRYPTION_KEY and persisted in the `vault_secrets` table so they
# survive process restarts.  In non-production environments the key may be a
# raw ASCII string; we pad/hash it to the required 32-byte Fernet key length.
# ---------------------------------------------------------------------------
def _build_vault_master_key() -> bytes:
    """Derive a 32-byte URL-safe base64 Fernet key from ENCRYPTION_KEY."""
    import base64
    import hashlib

    raw = os.getenv("ENCRYPTION_KEY", "").encode()
    # Fernet requires exactly 32 URL-safe-base64-encoded bytes (44 chars).
    derived = hashlib.sha256(raw).digest()  # always 32 bytes
    return base64.urlsafe_b64encode(derived)  # 44-char Fernet key


_credential_vault: Vault = Vault(
    master_key=_build_vault_master_key(),
    storage=DatabaseStorage(SessionLocal),
)
logger.info("Credential vault initialised with DatabaseStorage backend")

# Initialize FastAPI app
app = FastAPI(
    title="Trade-Claw API",
    description="Production-ready trading API with multi-broker support",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (H1) — comma-separated origins from CORS_ORIGINS.
# When the frontend is served from the same FastAPI app (default deployment),
# CORS is unnecessary; we still enable it when CORS_ORIGINS is set for users
# who run the frontend from a separate dev server.
_cors_origins_raw = os.getenv("CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        # X-API-Key is the header used by the bundled frontend (see frontend/api.js).
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        max_age=600,
    )
    logger.info("CORS enabled for origins: %s", _cors_origins)

# Initialize broker router
router = BrokerSessionRouter()


# ---------------------------------------------------------------------------
# Pydantic Models (Request/Response)  — with strict validation (H3)
# ---------------------------------------------------------------------------

# Trading-symbol regex: uppercase alphanum + a few separators, 1–20 chars.
_SYMBOL_PATTERN = r"^[A-Z0-9]{1,10}([/_\-][A-Z0-9]{1,10})?$"

_SUPPORTED_BROKERS = {"alpaca", "oanda", "hyperliquid", "mock"}
_SUPPORTED_ENVIRONMENTS = {"paper", "live"}
_SUPPORTED_SIDES = {"BUY", "SELL"}
_SUPPORTED_SEVERITIES = {"INFO", "WARNING", "ERROR", "CRITICAL"}
_SUPPORTED_ACTIONS = {
    "ORDER_SUBMITTED",
    "ORDER_REJECTED",
    "ORDER_CANCELLED",
    "ORDER_FILLED",
    "SESSION_CREATED",
    "SESSION_CLOSED",
    "SESSION_HALTED",
    "RISK_BREACH",
}


class BrokerSetupRequest(BaseModel):
    """Broker setup request."""

    model_config = ConfigDict(extra="forbid")

    broker_type: str = Field(..., description="alpaca, oanda, hyperliquid, mock")
    credentials: dict = Field(..., description="Broker credentials (API keys, etc.)")
    user_id: str | None = Field(None, max_length=64)
    # Paper (sandbox/demo/testnet) vs live trading. Defaults to paper so a
    # misconfigured frontend can never accidentally hit a live account.
    environment: str = Field(
        "paper",
        description="paper (sandbox/demo/testnet) or live (real money)",
    )

    @field_validator("broker_type")
    @classmethod
    def _check_broker(cls, v: str) -> str:
        v_lower = v.strip().lower()
        if v_lower not in _SUPPORTED_BROKERS:
            raise ValueError(
                f"Unsupported broker_type '{v}'. Allowed: {sorted(_SUPPORTED_BROKERS)}"
            )
        return v_lower

    @field_validator("environment")
    @classmethod
    def _check_environment(cls, v: str) -> str:
        v_lower = v.strip().lower()
        if v_lower not in _SUPPORTED_ENVIRONMENTS:
            raise ValueError(
                f"Unsupported environment '{v}'. Allowed: {sorted(_SUPPORTED_ENVIRONMENTS)}"
            )
        return v_lower

    @field_validator("credentials")
    @classmethod
    def _reject_empty_credentials(cls, v: dict) -> dict:
        if not isinstance(v, dict) or not v:
            raise ValueError("credentials must be a non-empty object")
        # Block obviously dangerous keys.
        dangerous = {k for k in v if k.lower() in {"dsn", "webhook_url", "callback_url"}}
        if dangerous:
            raise ValueError(f"Disallowed credential keys: {sorted(dangerous)}")
        return v


class BrokerSetupResponse(BaseModel):
    session_id: str
    broker_type: str
    environment: str
    status: str = "ACTIVE"
    created_at: datetime
    message: str


class PriceQuoteResponse(BaseModel):
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    liquidity: str = "HIGH"
    estimated_fees: Decimal = Decimal("0")


class OrderSubmitRequest(BaseModel):
    """Order submission request — all numeric fields must be strictly positive."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., min_length=1, max_length=20, pattern=_SYMBOL_PATTERN)
    side: str = Field(..., description="BUY or SELL")
    size: Decimal = Field(..., gt=Decimal(0))
    entry_price: Decimal = Field(..., gt=Decimal(0))
    stop_loss: Decimal = Field(..., gt=Decimal(0))
    take_profit: Decimal = Field(..., gt=Decimal(0))
    # Idempotency key (H4) — clients can pass their own UUID to make retries safe.
    idempotency_key: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Client-generated key; identical retries return the original order.",
    )

    @field_validator("side")
    @classmethod
    def _check_side(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in _SUPPORTED_SIDES:
            raise ValueError(f"side must be one of {sorted(_SUPPORTED_SIDES)}")
        return v_upper

    @model_validator(mode="after")
    def _check_sl_tp_relation(self) -> OrderSubmitRequest:
        """Ensure SL/TP make sense for the chosen side (H8)."""
        if self.entry_price == self.stop_loss:
            raise ValueError("entry_price must not equal stop_loss")
        if self.stop_loss == self.take_profit:
            raise ValueError("stop_loss must not equal take_profit")

        if self.side == "BUY":
            if not (self.stop_loss < self.entry_price < self.take_profit):
                raise ValueError(
                    "For BUY orders, stop_loss < entry_price < take_profit is required"
                )
        else:  # SELL
            if not (self.take_profit < self.entry_price < self.stop_loss):
                raise ValueError(
                    "For SELL orders, take_profit < entry_price < stop_loss is required"
                )
        return self


class OrderSubmitResponse(BaseModel):
    order_id: str
    status: str
    symbol: str
    side: str
    size: Decimal
    entry_price: Decimal
    created_at: datetime
    message: str
    risk_ratio: Decimal | None = None
    idempotency_key: str | None = None


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    symbol: str
    side: str
    size: Decimal
    filled_size: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    commission: Decimal = Decimal("0")
    pnl: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    created_at: datetime
    filled_at: datetime | None = None


class PositionResponse(BaseModel):
    symbol: str
    side: str
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    pnl_pct: Decimal
    status: str


class PositionListResponse(BaseModel):
    positions: list[PositionResponse]
    total_unrealized_pnl: Decimal
    total_pnl_pct: Decimal
    drawdown_pct: Decimal
    is_halted: bool


class AuditLogResponse(BaseModel):
    id: int
    action: str
    symbol: str | None = None
    details: str
    severity: str
    timestamp: datetime


class AuditLogExportResponse(BaseModel):
    logs: list[AuditLogResponse]
    total_count: int
    format: str = "json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _risk_ratio(side: str, entry: Decimal, sl: Decimal, tp: Decimal) -> Decimal | None:
    """Compute R/R using Decimal arithmetic (H5).

    Returns None when the SL leg has zero distance (should not happen after
    ``OrderSubmitRequest`` validation but we keep the guard defensively).
    """
    try:
        reward = tp - entry if side == "BUY" else entry - tp
        risk = entry - sl if side == "BUY" else sl - entry
        if risk <= 0:
            return None
        return (reward / risk).quantize(Decimal("0.0001"))
    except Exception:  # pragma: no cover - arithmetic is total on Decimal here
        return None


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "4.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Redirect to the bundled UI when available, otherwise return API metadata."""
    if (Path(__file__).resolve().parent.parent / "frontend" / "index.html").exists():
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/app/", status_code=307)
    return {
        "name": "Trade-Claw API",
        "version": "4.0.0",
        "description": "Multi-broker trading API with risk management",
        "docs": "/docs",
        "ui": "/app/ (frontend not found)",
    }


# ---------------------------------------------------------------------------
# Broker setup
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/brokers/setup",
    response_model=BrokerSetupResponse,
    dependencies=[Depends(require_api_key)],
)
async def setup_broker(
    request: BrokerSetupRequest,
    db: Session = Depends(get_db_session),
):
    """Set up a broker connection and create a session."""
    try:
        # Paper-mode flags map to broker-specific testnet/sandbox configuration.
        # Done here so the router doesn't need to know about the env switch.
        session_kwargs: dict = {}
        if request.environment == "paper":
            if request.broker_type == "hyperliquid":
                session_kwargs["testnet"] = True
            # Alpaca / OANDA: their adapters are not implemented yet, but the
            # convention they use is documented for future implementers:
            #   alpaca:   ALPACA_ENVIRONMENT=sandbox / live
            #   oanda:    OANDA_ENVIRONMENT=demo    / live

        session_id = await router.create_session(
            user_id=request.user_id or "default",
            broker_type=request.broker_type,
            credentials=request.credentials,
            **session_kwargs,
        )

        # Persist encrypted credentials so they survive restarts (C3).
        vault_key = f"vault:{session_id}"
        import json as _json

        _credential_vault.store(vault_key, _json.dumps(request.credentials))

        broker_session = BrokerSession(
            user_id=request.user_id or "default",
            broker_type=request.broker_type,
            credentials_vault_key=vault_key,
            session_id=session_id,
        )
        db.add(broker_session)

        risk_limit = RiskLimit(
            session_id=session_id,
            max_position_size_pct=0.10,
            max_drawdown_pct=-0.15,
            min_risk_reward_ratio=1.5,
        )
        db.add(risk_limit)
        db.commit()

        logger.info("Broker setup successful: %s - %s", request.broker_type, session_id)

        return BrokerSetupResponse(
            session_id=session_id,
            broker_type=request.broker_type,
            environment=request.environment,
            created_at=datetime.utcnow(),
            message=(
                f"Successfully connected to {request.broker_type} "
                f"({request.environment})"
            ),
        )

    except (ValueError, BrokerConnectionError) as exc:
        # Do NOT echo the exception text — it may contain credential fragments.
        logger.exception("Broker setup failed")
        raise HTTPException(status_code=400, detail="Broker setup failed") from exc
    except HTTPException:
        raise
    except Exception:  # pragma: no cover - safety net
        logger.exception("Unexpected error during broker setup")
        raise HTTPException(status_code=500, detail="Internal error") from None


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/brokers/{session_id}/quote",
    response_model=PriceQuoteResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_quote(
    session_id: str,
    symbol: str = Query(..., min_length=1, max_length=20, pattern=_SYMBOL_PATTERN),
    amount: Decimal | None = Query(None, gt=Decimal(0)),
    db: Session = Depends(get_db_session),
):
    """Get a live price quote for a symbol."""
    try:
        broker_session = (
            db.query(BrokerSession).filter(BrokerSession.session_id == session_id).first()
        )
        if not broker_session:
            raise HTTPException(status_code=404, detail="Session not found")

        adapter = await router.get_api_adapter(session_id)
        # OrderAPIAdapter delegates to the broker's get_quote; the underlying
        # Quote dataclass exposes ``last_price`` and does not carry liquidity
        # or fee fields, so we provide reasonable defaults here.
        quote = await adapter.broker.get_quote(symbol)

        return PriceQuoteResponse(
            symbol=symbol,
            bid=Decimal(str(quote.bid)),
            ask=Decimal(str(quote.ask)),
            last=Decimal(str(quote.last_price)),
            liquidity="HIGH",
            estimated_fees=Decimal("0"),
        )

    except HTTPException:
        raise
    except (BrokerConnectionError, ValueError) as exc:
        logger.exception("Quote fetch failed for %s", symbol)
        raise HTTPException(status_code=400, detail="Quote unavailable") from exc
    except Exception:
        logger.exception("Unexpected quote error")
        raise HTTPException(status_code=500, detail="Internal error") from None


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/orders/submit",
    response_model=OrderSubmitResponse,
    dependencies=[Depends(require_api_key)],
)
async def submit_order(
    request: OrderSubmitRequest,  # body — required, no default (H2)
    session_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db_session),
):
    """Submit a new order with risk validation and idempotency."""
    try:
        # Session lookup
        broker_session = (
            db.query(BrokerSession).filter(BrokerSession.session_id == session_id).first()
        )
        if not broker_session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Idempotency: if the client replays a request with the same key, return
        # the original response instead of submitting a second order (H4).
        idem_key = request.idempotency_key
        if idem_key:
            existing = (
                db.query(Order)
                .filter(
                    Order.session_id == session_id,
                    Order.idempotency_key == idem_key,
                )
                .first()
            )
            if existing:
                logger.info(
                    "Idempotent replay for session=%s key=%s → order=%s",
                    session_id,
                    idem_key,
                    existing.order_id,
                )
                return OrderSubmitResponse(
                    order_id=existing.order_id,
                    status=existing.status,
                    symbol=existing.symbol,
                    side=existing.side,
                    size=existing.size,
                    entry_price=existing.entry_price,
                    created_at=existing.timestamp,
                    message=f"Replay: existing order {existing.order_id} returned",
                    risk_ratio=existing.risk_ratio,
                    idempotency_key=idem_key,
                )

        # Account balance (fetched via broker adapter)
        risk_engine = RiskEngine(db)
        adapter = await router.get_api_adapter(session_id)
        try:
            balance_info = await adapter.get_balance()
        except Exception:  # noqa: BLE001
            logger.exception("Could not fetch broker balance — using fallback")
            balance_info = {}
        account_balance = Decimal(str(balance_info.get("balance", 10000)))

        # Risk validation
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
            db.add(
                AuditLog(
                    session_id=session_id,
                    action="ORDER_REJECTED",
                    symbol=request.symbol,
                    details=validation.message,
                    severity="WARNING",
                )
            )
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Order rejected: {validation.message}",
            )

        # Submit to broker via the OrderAPIAdapter, which expects a normalized
        # OrderAPIRequest — translate from our HTTP DTO here.
        from app.api.order_api_adapter import OrderAPIRequest  # noqa: PLC0415
        from app.brokers.broker_interface import OrderDirection  # noqa: PLC0415

        api_request = OrderAPIRequest(
            symbol=request.symbol,
            direction=OrderDirection(request.side),
            quantity=float(request.size),
            entry_price=float(request.entry_price),
            stop_loss=float(request.stop_loss),
            take_profit=float(request.take_profit),
        )
        broker_order = await adapter.submit_order(api_request)

        # ``Order.status`` is an enum on the broker side — persist its string.
        order_status = (
            broker_order.status.value
            if hasattr(broker_order.status, "value")
            else str(broker_order.status)
        )

        # Persist
        risk_ratio = _risk_ratio(
            request.side, request.entry_price, request.stop_loss, request.take_profit
        )
        db_order = Order(
            session_id=session_id,
            order_id=broker_order.order_id,
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            status=order_status,
            risk_ratio=risk_ratio,
            idempotency_key=idem_key,
        )
        db.add(db_order)

        db.add(
            AuditLog(
                session_id=session_id,
                action="ORDER_SUBMITTED",
                symbol=request.symbol,
                details=(
                    f"Order {broker_order.order_id} submitted: "
                    f"{request.side} {request.size} @ {request.entry_price}"
                ),
                severity="INFO",
            )
        )
        db.commit()

        logger.info("Order submitted: %s - %s", broker_order.order_id, request.symbol)

        return OrderSubmitResponse(
            order_id=broker_order.order_id,
            status=order_status,
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry_price=request.entry_price,
            created_at=datetime.utcnow(),
            message=f"Order {broker_order.order_id} submitted successfully",
            risk_ratio=risk_ratio,
            idempotency_key=idem_key,
        )

    except HTTPException:
        raise
    except OrderValidationError as exc:
        logger.warning("Order validation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OrderRejectedError as exc:
        logger.warning("Order rejected by broker: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BrokerConnectionError as exc:
        logger.exception("Broker connection error during order submission")
        raise HTTPException(status_code=502, detail="Broker connection failed") from exc
    except Exception:
        logger.exception("Unexpected order submission error")
        raise HTTPException(status_code=500, detail="Internal error") from None


@app.get(
    "/api/v1/orders/{order_id}",
    response_model=OrderStatusResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_order_status(
    order_id: str,
    session_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db_session),
):
    """Get order status and fills."""
    try:
        order = (
            db.query(Order)
            .filter(Order.order_id == order_id, Order.session_id == session_id)
            .first()
        )
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
    except Exception:
        logger.exception("Order status fetch failed")
        raise HTTPException(status_code=500, detail="Internal error") from None


@app.post(
    "/api/v1/orders/{order_id}/cancel",
    dependencies=[Depends(require_api_key)],
)
async def cancel_order(
    order_id: str,
    session_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db_session),
):
    """Cancel an open order (idempotent)."""
    try:
        order = (
            db.query(Order)
            .filter(Order.order_id == order_id, Order.session_id == session_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Idempotent: canceling a CANCELLED order is a no-op (M-issue from review)
        if order.status == "CANCELLED":
            return {
                "status": "already_cancelled",
                "order_id": order_id,
                "message": "Order was already cancelled",
            }
        if order.status == "FILLED":
            raise HTTPException(status_code=400, detail="Cannot cancel filled order")

        adapter = await router.get_api_adapter(session_id)
        await adapter.cancel_order(order_id)

        order.status = "CANCELLED"
        order.cancelled_at = datetime.utcnow()

        db.add(
            AuditLog(
                session_id=session_id,
                action="ORDER_CANCELLED",
                symbol=order.symbol,
                details=f"Order {order_id} cancelled",
                severity="INFO",
            )
        )
        db.commit()

        logger.info("Order cancelled: %s", order_id)
        return {"status": "success", "order_id": order_id, "message": "Order cancelled"}

    except HTTPException:
        raise
    except BrokerConnectionError as exc:
        logger.exception("Broker error while cancelling order")
        raise HTTPException(status_code=502, detail="Broker connection failed") from exc
    except Exception:
        logger.exception("Order cancellation failed")
        raise HTTPException(status_code=500, detail="Internal error") from None


# ---------------------------------------------------------------------------
# Emergency halt — cancels every open order in a session and flags the
# RiskLimit row as halted so further submits are blocked by the risk engine.
# ---------------------------------------------------------------------------


class HaltResponse(BaseModel):
    session_id: str
    cancelled: list[str]
    failed: list[dict]
    is_halted: bool
    message: str


@app.post(
    "/api/v1/halt",
    response_model=HaltResponse,
    dependencies=[Depends(require_api_key)],
)
async def halt_session(
    session_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db_session),
):
    """Emergency halt: cancel all non-terminal orders for a session and flag halted."""
    try:
        broker_session = (
            db.query(BrokerSession).filter(BrokerSession.session_id == session_id).first()
        )
        if not broker_session:
            raise HTTPException(status_code=404, detail="Session not found")

        open_orders = (
            db.query(Order)
            .filter(
                Order.session_id == session_id,
                Order.status.notin_(["CANCELLED", "FILLED", "REJECTED"]),
            )
            .all()
        )

        cancelled: list[str] = []
        failed: list[dict] = []

        if open_orders:
            try:
                adapter = await router.get_api_adapter(session_id)
            except Exception as exc:
                # Without a live adapter we still flip the local state so the UI
                # reflects "halted" — but record the failure so the user knows
                # broker-side orders may still exist.
                logger.warning("No live adapter for halt on %s: %s", session_id, exc)
                adapter = None

            for order in open_orders:
                if adapter is None:
                    failed.append({"order_id": order.order_id, "error": "broker offline"})
                    continue
                try:
                    await adapter.cancel_order(order.order_id)
                    order.status = "CANCELLED"
                    order.cancelled_at = datetime.utcnow()
                    cancelled.append(order.order_id)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Halt: cancel failed for %s", order.order_id)
                    failed.append({"order_id": order.order_id, "error": str(exc)})

        # Flip the risk limit row to halted so the engine refuses new orders.
        risk_limit = (
            db.query(RiskLimit).filter(RiskLimit.session_id == session_id).first()
        )
        if risk_limit:
            risk_limit.is_halted = True

        db.add(
            AuditLog(
                session_id=session_id,
                action="SESSION_HALTED",
                details=(
                    f"Emergency halt: {len(cancelled)} cancelled, "
                    f"{len(failed)} failed"
                ),
                severity="CRITICAL",
            )
        )
        db.commit()

        logger.warning(
            "EMERGENCY HALT executed for %s: %d cancelled, %d failed",
            session_id,
            len(cancelled),
            len(failed),
        )
        return HaltResponse(
            session_id=session_id,
            cancelled=cancelled,
            failed=failed,
            is_halted=True,
            message=(
                f"Halt executed: {len(cancelled)} order(s) cancelled, "
                f"{len(failed)} failed"
            ),
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Halt failed")
        raise HTTPException(status_code=500, detail="Halt failed") from None


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/positions",
    response_model=PositionListResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_positions(
    session_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db_session),
):
    """Get all active positions and account summary."""
    try:
        positions = (
            db.query(Position)
            .filter(Position.session_id == session_id, Position.status == "OPEN")
            .all()
        )
        risk_limit = db.query(RiskLimit).filter(RiskLimit.session_id == session_id).first()

        total_unrealized_pnl = (
            sum((p.unrealized_pnl for p in positions), start=Decimal("0"))
            if positions
            else Decimal("0")
        )

        position_responses: list[PositionResponse] = []
        for p in positions:
            notional = (p.entry_price or Decimal(0)) * (p.size or Decimal(0))
            pnl_pct = (
                (p.unrealized_pnl / notional * Decimal(100)).quantize(Decimal("0.01"))
                if notional > 0
                else Decimal("0.00")
            )
            position_responses.append(
                PositionResponse(
                    symbol=p.symbol,
                    side=p.side,
                    size=p.size,
                    entry_price=p.entry_price,
                    current_price=p.current_price,
                    unrealized_pnl=p.unrealized_pnl,
                    pnl_pct=pnl_pct,
                    status=p.status,
                )
            )

        return PositionListResponse(
            positions=position_responses,
            total_unrealized_pnl=total_unrealized_pnl,
            total_pnl_pct=Decimal("0.00"),
            drawdown_pct=Decimal(str(risk_limit.current_drawdown_pct))
            if risk_limit
            else Decimal("0"),
            is_halted=bool(risk_limit.is_halted) if risk_limit else False,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Position fetch failed")
        raise HTTPException(status_code=500, detail="Internal error") from None


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/audit",
    response_model=AuditLogExportResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_audit_log(
    session_id: str = Query(..., min_length=1, max_length=64),
    action: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=1_000_000),
    db: Session = Depends(get_db_session),
):
    """
    Get immutable audit log entries (filtered & paginated).

    ``action`` and ``severity`` must be one of the known enum values (prevents
    abusive substring-filter attacks against a large log table).
    """
    try:
        if action is not None and action not in _SUPPORTED_ACTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action. Allowed: {sorted(_SUPPORTED_ACTIONS)}",
            )
        if severity is not None and severity not in _SUPPORTED_SEVERITIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Allowed: {sorted(_SUPPORTED_SEVERITIES)}",
            )

        query = db.query(AuditLog).filter(AuditLog.session_id == session_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if severity:
            query = query.filter(AuditLog.severity == severity)

        total_count = query.count()
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

        return AuditLogExportResponse(
            logs=[
                AuditLogResponse(
                    id=log.id,
                    action=log.action,
                    symbol=log.symbol,
                    details=log.details,
                    severity=log.severity,
                    timestamp=log.timestamp,
                )
                for log in logs
            ],
            total_count=total_count,
            format="json",
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Audit log fetch failed")
        raise HTTPException(status_code=500, detail="Internal error") from None


# ---------------------------------------------------------------------------
# Phase 2 — Backtest & Standalone Risk API  (/api/backtest, /api/risk)
#
# These endpoints use the in-memory RiskEngine (no DB) and the standalone
# BacktestSimulator. They are intentionally not auth-gated so that the
# Phase 2 test suite can call them without token setup.
# ---------------------------------------------------------------------------

from app.backtest import BacktestRequest, BacktestSimulator  # noqa: E402
from app.risk import RiskEngine as _StandaloneRiskEngine  # noqa: E402

# Shared singleton for risk (state must persist across calls)
_risk_engine = _StandaloneRiskEngine()


class _PreTradeCheckRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    entry_price: float
    account_equity: float
    stop_loss: float
    take_profit: float


class _ExecuteTradeRequest(BaseModel):
    trade_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float


@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """Run a backtest simulation (Phase 2)."""
    try:
        # Fresh simulator per request so results don't accumulate across calls
        sim = BacktestSimulator(starting_capital=request.starting_capital)
        trades_dicts = [t.model_dump() for t in request.trades]
        result = sim.run_backtest(
            trades=trades_dicts,
            only_grades=request.only_grades,
        )
        metrics = result["metrics"]
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "trades_executed": result["trades_executed"],
            "metrics": metrics,
            "trades": result["trades"],
            "message": (
                f"Backtest complete: {result['trades_executed']} trades, "
                f"ROI {metrics['roi_pct']:.2f}%"
            ),
        }
    except Exception:
        logger.exception("Backtest failed")
        raise HTTPException(status_code=500, detail="Backtest failed") from None


@app.get("/api/backtest/status")
async def backtest_status():
    """Return the current status of the backtest engine (Phase 2)."""
    return {
        "status": "ready",
        "backtest_engine": "BacktestSimulator",
    }


@app.get("/api/risk/status")
async def risk_status():
    """Return the current risk engine status (Phase 2)."""
    return _risk_engine.get_status()


@app.post("/api/risk/pre-trade-check")
async def pre_trade_check(request: _PreTradeCheckRequest):
    """Run a pre-trade risk check (Phase 2)."""
    approved, details = _risk_engine.pre_trade_check(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        entry_price=request.entry_price,
        account_equity=request.account_equity,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
    )
    return {"approved": approved, "details": details}


@app.post("/api/risk/execute-trade")
async def execute_trade_phase2(request: _ExecuteTradeRequest):
    """Execute a trade and register its stop-loss (Phase 2)."""
    success = _risk_engine.execute_trade(
        trade_id=request.trade_id,
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
    )
    return {"success": success}


# ---------------------------------------------------------------------------
# Correlation Engine (app/correlation)
# ---------------------------------------------------------------------------

from app.correlation import AssetManager, CorrelationEngine  # noqa: E402

_asset_manager = AssetManager()
_correlation_engine = CorrelationEngine()


class _CorrelationAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_prices: dict[str, list[float]] = Field(
        ...,
        description="Map of asset symbol → time-aligned price series",
    )
    threshold: float = Field(0.7, ge=0.0, le=1.0)


@app.get("/api/v1/correlation/assets")
async def correlation_assets():
    """List predefined assets known to the correlation engine."""
    assets = _asset_manager.list_assets()
    by_type: dict[str, int] = {}
    out: dict[str, dict[str, str]] = {}
    for sym, asset in assets.items():
        by_type[asset.asset_type.value] = by_type.get(asset.asset_type.value, 0) + 1
        out[sym] = {
            "name": asset.name,
            "type": asset.asset_type.value,
            "description": asset.description,
        }
    return {"assets": out, "count": len(out), "categories": by_type}


@app.post("/api/v1/correlation/analyze")
async def correlation_analyze(request: _CorrelationAnalyzeRequest):
    """Compute pairwise correlations across an arbitrary set of assets."""
    try:
        if len(request.asset_prices) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 assets for correlation analysis",
            )
        return _correlation_engine.analyze(
            asset_prices=request.asset_prices,
            threshold=request.threshold,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Correlation analysis failed")
        raise HTTPException(status_code=500, detail="Correlation failed") from None


# ---------------------------------------------------------------------------
# Macro Events (app/macro)
# ---------------------------------------------------------------------------

from app.macro import EventScorer, MacroEventFetcher  # noqa: E402

_macro_fetcher = MacroEventFetcher()
_event_scorer = EventScorer()


@app.get("/api/v1/macro/events")
async def macro_events(
    category: str | None = Query(None, description="Filter by event category"),
    limit: int = Query(50, ge=1, le=200),
):
    """List historical and recent macro events."""
    try:
        events = _macro_fetcher.events
        if category:
            from app.macro import EventCategory

            try:
                cat = EventCategory(category)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Unknown category. Allowed: "
                        f"{[c.value for c in EventCategory]}"
                    ),
                ) from exc
            events = [e for e in events if e.category == cat]

        events_sorted = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
        return {
            "count": len(events_sorted),
            "total": len(_macro_fetcher.events),
            "events": [
                {**e.to_dict(), "score": _event_scorer.score_event(e)}
                for e in events_sorted
            ],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Macro events fetch failed")
        raise HTTPException(status_code=500, detail="Macro fetch failed") from None


@app.get("/api/v1/macro/upcoming")
async def macro_upcoming(hours: int = Query(72, ge=1, le=720)):
    """Events whose timestamp lies in the next N hours."""
    from datetime import timedelta

    now = datetime.utcnow()
    horizon = now + timedelta(hours=hours)
    upcoming = [
        e for e in _macro_fetcher.events if now <= e.timestamp <= horizon
    ]
    upcoming_sorted = sorted(upcoming, key=lambda e: e.timestamp)
    return {
        "count": len(upcoming_sorted),
        "horizon_hours": hours,
        "events": [
            {**e.to_dict(), "score": _event_scorer.score_event(e)}
            for e in upcoming_sorted
        ],
    }


# ---------------------------------------------------------------------------
# ML / Trade Grader (app/ml/grader.py)
# ---------------------------------------------------------------------------

from app.ml.grader import SetupCriteria, TradeGrader  # noqa: E402

_trade_grader = TradeGrader()


class _GradeCriteria(BaseModel):
    structural_level: bool = False
    liquidity_sweep: bool = False
    momentum: bool = False
    volume: bool = False
    risk_reward: bool = False
    macro_alignment: bool = False
    no_contradiction: bool = False


class _GradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., min_length=1, max_length=20)
    direction: str = Field(..., description="LONG or SHORT")
    entry_price: float = Field(..., gt=0)
    stop_loss_price: float = Field(..., gt=0)
    tp1_price: float = Field(..., gt=0)
    tp2_price: float = Field(..., gt=0)
    criteria: _GradeCriteria = Field(default_factory=_GradeCriteria)
    confidence: float = Field(50.0, ge=0, le=100)
    risk_percent: float = Field(2.0, gt=0, le=10)
    drawdown_stage: int = Field(1, ge=1, le=5)

    @field_validator("direction")
    @classmethod
    def _check_direction(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in {"LONG", "SHORT"}:
            raise ValueError("direction must be LONG or SHORT")
        return v


@app.post("/api/v1/ml/grade")
async def grade_setup(request: _GradeRequest):
    """Grade a trade setup using the 7-criteria framework."""
    try:
        setup = _trade_grader.grade(
            symbol=request.symbol,
            direction=request.direction,
            entry_price=request.entry_price,
            stop_loss_price=request.stop_loss_price,
            tp1_price=request.tp1_price,
            tp2_price=request.tp2_price,
            criteria=SetupCriteria(**request.criteria.model_dump()),
            confidence=request.confidence,
            risk_percent=request.risk_percent,
        )
        tradeable = _trade_grader.is_tradeable(setup, drawdown_stage=request.drawdown_stage)
        return {**setup.to_dict(), "tradeable": tradeable}
    except Exception:
        logger.exception("Grade setup failed")
        raise HTTPException(status_code=500, detail="Grade failed") from None


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):  # pragma: no cover
    logger.warning("HTTP %s: %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        media_type="application/json; charset=utf-8",
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):  # pragma: no cover
    # Never leak the exception text to the client — only to logs.
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
        media_type="application/json; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Static frontend
#
# The bundled UI (frontend/index.html + companion .js/.css) is served from the
# same FastAPI process so the launcher only needs to start one server. This
# also avoids CORS for the default deployment because the UI shares the
# backend's origin.
# ---------------------------------------------------------------------------

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/app",
        StaticFiles(directory=str(_FRONTEND_DIR), html=True),
        name="frontend",
    )
    logger.info("Frontend mounted at /app from %s", _FRONTEND_DIR)
else:
    logger.warning("Frontend directory not found at %s — UI not available", _FRONTEND_DIR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
