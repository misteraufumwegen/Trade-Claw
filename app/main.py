"""FastAPI REST API for Trade-Claw."""

from __future__ import annotations

import json
import os

# Load .env file before anything else reads environment variables.
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.db import get_db_session, init_db
from app.db.models import AuditLog, BrokerSession, Order, Position, RiskLimit, TradeOutcome
from app.db.session import SessionLocal
from app.exceptions import (
    BrokerConnectionError,
    OrderRejectedError,
    OrderValidationError,
)
from app.logging_config import setup_logging
from app.ml import (
    classify_outcome,
    extract_features,
    model_status,
    score_features,
)
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


# ---------------------------------------------------------------------------
# Lifespan — runs the outcome-resolver background poller.
#
# Every ``OUTCOME_POLL_SECONDS`` seconds the poller walks open TradeOutcome
# rows, asks the corresponding broker session for the current order state
# (and any settlement metadata the mock broker writes via
# ``_simulate_settlement``), and resolves the row when a closed_price is
# available. This is what turns a Mock-Broker fill into a WIN/LOSS row in
# the ML training data without manual intervention.
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402


async def _macro_poller(
    gdelt_interval: float,
    gdacs_interval: float,
    min_confirmations: int,
    confirmation_window_minutes: int,
    enable_gdelt: bool,
    enable_gdacs: bool,
) -> None:
    """Poll GDELT (news) and GDACS (disasters) on independent timers.

    Runs two child loops via ``asyncio.gather``. Each loop wraps its iteration
    in a broad try/except so a transient API failure does not kill the loop.
    """
    from app.macro import GdacsClient, GdeltClient  # noqa: PLC0415

    gdelt_client = GdeltClient() if enable_gdelt else None
    gdacs_client = GdacsClient() if enable_gdacs else None

    async def _gdelt_loop() -> None:
        if gdelt_client is None:
            return
        while True:
            try:
                stats = await _macro_fetcher.poll_live_events(
                    gdelt_client=gdelt_client,
                    gdacs_client=None,
                    min_confirmations=min_confirmations,
                    confirmation_window_minutes=confirmation_window_minutes,
                )
                if stats.get("gdelt_new"):
                    logger.info("Macro GDELT added %s new events", stats["gdelt_new"])
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("GDELT poll iteration failed")
            await asyncio.sleep(gdelt_interval)

    async def _gdacs_loop() -> None:
        if gdacs_client is None:
            return
        while True:
            try:
                stats = await _macro_fetcher.poll_live_events(
                    gdelt_client=None,
                    gdacs_client=gdacs_client,
                )
                if stats.get("gdacs_new"):
                    logger.info("Macro GDACS added %s new events", stats["gdacs_new"])
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("GDACS poll iteration failed")
            await asyncio.sleep(gdacs_interval)

    await asyncio.gather(_gdelt_loop(), _gdacs_loop())


async def _outcome_poller(interval_seconds: float = 2.0) -> None:
    """Walk open TradeOutcome rows and resolve them when the broker has closed
    the position. Survives transient errors so a single bad row doesn't kill
    the whole loop."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            db = SessionLocal()
            try:
                open_rows = (
                    db.query(TradeOutcome).filter(TradeOutcome.outcome.is_(None)).limit(50).all()
                )
                for row in open_rows:
                    session = router.sessions.get(row.session_id)
                    if session is None or session.broker is None:
                        continue
                    broker_order = getattr(session.broker, "orders", {}).get(row.order_id)
                    if broker_order is None:
                        continue
                    meta = broker_order.metadata or {}
                    closed_price = meta.get("closed_price")
                    if closed_price is None:
                        continue
                    _resolve_outcome(
                        db,
                        row.order_id,
                        status="FILLED",
                        closed_price=float(closed_price),
                    )
                    db.add(
                        AuditLog(
                            session_id=row.session_id,
                            action="ORDER_FILLED",
                            symbol=row.symbol,
                            details=(
                                f"Auto-resolved: {meta.get('settlement_label', 'CLOSED')} "
                                f"@ {closed_price}"
                            ),
                            severity="INFO",
                        )
                    )
                db.commit()
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception:  # noqa: BLE001
            logger.exception("Outcome poller iteration failed")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Reload user-defined brokers from DB into the registry before any
    # request is served, so they're indistinguishable from built-ins from
    # the API perspective.
    try:
        from app.brokers.dynamic_loader import reload_from_db  # noqa: PLC0415

        db = SessionLocal()
        try:
            reload_from_db(db)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.exception("Custom-broker reload at startup failed")

    poll_seconds = float(os.getenv("OUTCOME_POLL_SECONDS", "2"))
    task = asyncio.create_task(_outcome_poller(poll_seconds))
    logger.info("Outcome poller started (every %ss)", poll_seconds)

    macro_task = None
    enable_gdelt = os.getenv("MACRO_GDELT_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
    enable_gdacs = os.getenv("MACRO_GDACS_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
    if enable_gdelt or enable_gdacs:
        macro_task = asyncio.create_task(
            _macro_poller(
                gdelt_interval=float(os.getenv("MACRO_GDELT_POLL_SECONDS", "90")),
                gdacs_interval=float(os.getenv("MACRO_GDACS_POLL_SECONDS", "300")),
                min_confirmations=int(os.getenv("MACRO_GDELT_MIN_DOMAINS", "2")),
                confirmation_window_minutes=int(os.getenv("MACRO_GDELT_WINDOW_MINUTES", "60")),
                enable_gdelt=enable_gdelt,
                enable_gdacs=enable_gdacs,
            )
        )
        logger.info(
            "Macro poller started (GDELT=%s, GDACS=%s)",
            enable_gdelt,
            enable_gdacs,
        )

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        if macro_task is not None:
            macro_task.cancel()
            try:
                await macro_task
            except asyncio.CancelledError:
                pass


# Initialize FastAPI app
app = FastAPI(
    title="Trade-Claw API",
    description="Production-ready trading API with multi-broker support",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
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

# Broker types come from the plugin registry — the validator below queries
# it dynamically so any user-supplied plugin in app/brokers/plugins/ becomes
# immediately accept-list-able without code changes here.
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
        from app.brokers.registry import REGISTRY  # noqa: PLC0415

        v_lower = v.strip().lower()
        if REGISTRY.get(v_lower) is None:
            raise ValueError(
                f"Unsupported broker_type '{v}'. "
                f"Known: {REGISTRY.known_types()} — drop a plugin into "
                f"app/brokers/plugins/ to register more."
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
    # Optional pre-trade context the ML gate uses for feature extraction.
    # The TradingView webhook fills these; the manual UI may leave them empty.
    grading_criteria: dict[str, bool] | None = Field(
        None,
        description="Boolean flags for the 7-criteria framework (structural_level, "
        "liquidity_sweep, momentum, volume, risk_reward, macro_alignment, "
        "no_contradiction). Used as ML feature inputs.",
    )
    macro_aligned: bool | None = Field(
        None,
        description="Macro environment matches trade direction (overrides "
        "grading_criteria.macro_alignment when both supplied).",
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
    ml_score: float | None = Field(
        None, description="ML probability-of-success at submit time (None when no model loaded)."
    )


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


def _resolve_outcome(
    db: Session,
    order_id: str,
    *,
    status: str,
    closed_price: float | None,
) -> None:
    """Update the trade_outcomes row for ``order_id`` with the final label.

    Idempotent: a second call with a different status will overwrite the
    earlier label (useful when CANCELLED is later replaced by FILLED).
    """
    row = db.query(TradeOutcome).filter(TradeOutcome.order_id == order_id).first()
    if row is None:
        return  # No snapshot — nothing to resolve.
    label, pnl = classify_outcome(
        side=row.side,
        entry_price=float(row.entry_price),
        stop_loss=float(row.stop_loss),
        take_profit=float(row.take_profit),
        closed_price=closed_price,
        status=status,
    )
    row.outcome = label
    row.pnl = Decimal(str(round(pnl, 8)))
    row.closed_price = Decimal(str(closed_price)) if closed_price is not None else None
    row.closed_at = datetime.utcnow()


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
    # Path.exists() is sync; we computed _FRONTEND_DIR at module load time,
    # so checking once at request scope is fine. Wrap in noqa to silence
    # async-purity warning for this trivial check.
    index_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"  # noqa: ASYNC240
    if index_path.exists():  # noqa: ASYNC240
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


@app.get("/api/v1/brokers/types")
async def list_broker_types():
    """Enumerate every broker the plugin registry can instantiate.

    The frontend uses this to populate the dropdown and credential template;
    plugins that drop into ``app/brokers/plugins/`` show up automatically.
    """
    from app.brokers.registry import REGISTRY  # noqa: PLC0415

    entries = REGISTRY.list()
    return {
        "count": len(entries),
        "brokers": [e.to_public_dict() for e in entries],
    }


# ---------------------------------------------------------------------------
# Custom broker definitions — UI can create/list/delete entries that get
# materialised into the registry by the dynamic loader.
# ---------------------------------------------------------------------------


@app.get("/api/v1/brokers/ccxt-exchanges")
async def ccxt_exchanges():
    """Return every exchange CCXT supports — for the 'add CCXT broker' UI."""
    try:
        import ccxt  # noqa: PLC0415
    except ImportError:
        return {"installed": False, "exchanges": []}
    return {"installed": True, "exchanges": list(ccxt.exchanges)}


@app.get("/api/v1/brokers/rest-template")
async def rest_template():
    """Return an example Generic-REST config for the UI."""
    from app.brokers.generic_rest_adapter import GenericRestConfig  # noqa: PLC0415

    return {"example": GenericRestConfig.example()}


class _CcxtDefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: str = Field(..., min_length=1, max_length=64)
    label: str | None = Field(None, max_length=120)
    description: str | None = ""
    tags: list[str] | None = None
    paper_supported: bool = True
    live_supported: bool = True


class _RestDefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    broker_type: str = Field(..., min_length=3, max_length=120, pattern=r"^[a-z0-9][a-z0-9._:-]+$")
    label: str = Field(..., min_length=1, max_length=120)
    description: str | None = ""
    tags: list[str] | None = None
    paper_supported: bool = True
    live_supported: bool = True
    config: dict = Field(..., description="GenericRestAdapter config")
    credentials: list[dict] | None = None


@app.post(
    "/api/v1/brokers/defs/ccxt",
    dependencies=[Depends(require_api_key)],
)
async def add_ccxt_def(
    request: _CcxtDefRequest,
    db: Session = Depends(get_db_session),
):
    """Persist a new CCXT-based broker and hot-register it."""
    try:
        import ccxt  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(status_code=400, detail="ccxt is not installed on this host") from exc
    if request.exchange not in ccxt.exchanges:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown CCXT exchange '{request.exchange}'. "
            f"See GET /api/v1/brokers/ccxt-exchanges for the list.",
        )
    from app.brokers.dynamic_loader import reload_from_db  # noqa: PLC0415
    from app.db.models import CustomBrokerDef  # noqa: PLC0415

    broker_type = f"ccxt:{request.exchange}"
    existing = db.query(CustomBrokerDef).filter(CustomBrokerDef.broker_type == broker_type).first()
    label = request.label or f"{request.exchange.title()} (via CCXT)"
    payload_json = json_dumps_safe({"exchange": request.exchange})
    if existing:
        existing.label = label
        existing.description = request.description or ""
        existing.tags_csv = ",".join(request.tags or [])
        existing.paper_supported = request.paper_supported
        existing.live_supported = request.live_supported
        existing.config_json = payload_json
        existing.enabled = True
    else:
        db.add(
            CustomBrokerDef(
                broker_type=broker_type,
                kind="ccxt",
                label=label,
                description=request.description or "",
                tags_csv=",".join(request.tags or []),
                paper_supported=request.paper_supported,
                live_supported=request.live_supported,
                config_json=payload_json,
                enabled=True,
            )
        )
    db.commit()
    reload_from_db(db)
    return {"broker_type": broker_type, "registered": True}


@app.post(
    "/api/v1/brokers/defs/rest",
    dependencies=[Depends(require_api_key)],
)
async def add_rest_def(
    request: _RestDefRequest,
    db: Session = Depends(get_db_session),
):
    """Persist a new Generic-REST broker and hot-register it."""
    from app.brokers.dynamic_loader import reload_from_db  # noqa: PLC0415
    from app.brokers.generic_rest_adapter import GenericRestConfig  # noqa: PLC0415
    from app.db.models import CustomBrokerDef  # noqa: PLC0415

    try:
        GenericRestConfig(request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid REST config: {exc}") from exc

    payload = {"rest_config": request.config, "credentials": request.credentials or []}
    payload_json = json_dumps_safe(payload)
    existing = (
        db.query(CustomBrokerDef).filter(CustomBrokerDef.broker_type == request.broker_type).first()
    )
    if existing:
        existing.kind = "rest"
        existing.label = request.label
        existing.description = request.description or ""
        existing.tags_csv = ",".join(request.tags or [])
        existing.paper_supported = request.paper_supported
        existing.live_supported = request.live_supported
        existing.config_json = payload_json
        existing.enabled = True
    else:
        db.add(
            CustomBrokerDef(
                broker_type=request.broker_type,
                kind="rest",
                label=request.label,
                description=request.description or "",
                tags_csv=",".join(request.tags or []),
                paper_supported=request.paper_supported,
                live_supported=request.live_supported,
                config_json=payload_json,
                enabled=True,
            )
        )
    db.commit()
    reload_from_db(db)
    return {"broker_type": request.broker_type, "registered": True}


@app.get(
    "/api/v1/brokers/defs",
    dependencies=[Depends(require_api_key)],
)
async def list_broker_defs(db: Session = Depends(get_db_session)):
    from app.db.models import CustomBrokerDef  # noqa: PLC0415

    rows = db.query(CustomBrokerDef).order_by(CustomBrokerDef.created_at.desc()).all()
    out = []
    for r in rows:
        try:
            cfg = json.loads(r.config_json or "{}")
        except json.JSONDecodeError:
            cfg = {"_invalid": True}
        out.append(
            {
                "id": r.id,
                "broker_type": r.broker_type,
                "kind": r.kind,
                "label": r.label,
                "description": r.description,
                "tags": [t for t in (r.tags_csv or "").split(",") if t],
                "paper_supported": r.paper_supported,
                "live_supported": r.live_supported,
                "enabled": r.enabled,
                "config": cfg,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
        )
    return {"defs": out}


@app.delete(
    "/api/v1/brokers/defs/{broker_type}",
    dependencies=[Depends(require_api_key)],
)
async def delete_broker_def(
    broker_type: str,
    db: Session = Depends(get_db_session),
):
    from app.brokers.dynamic_loader import reload_from_db  # noqa: PLC0415
    from app.db.models import CustomBrokerDef  # noqa: PLC0415

    row = db.query(CustomBrokerDef).filter(CustomBrokerDef.broker_type == broker_type).first()
    if not row:
        raise HTTPException(status_code=404, detail="Definition not found")
    db.delete(row)
    db.commit()
    reload_from_db(db)
    return {"deleted": broker_type}


class _TestRestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: dict
    credentials: dict
    paper: bool = True


@app.post(
    "/api/v1/brokers/defs/test-rest",
    dependencies=[Depends(require_api_key)],
)
async def test_rest_def(request: _TestRestRequest):
    """Try to authenticate against a Generic-REST config without persisting it.

    Lets the UI surface real error messages from the broker before the user
    clicks "Save".
    """
    from app.brokers.generic_rest_adapter import (  # noqa: PLC0415
        GenericRestAdapter,
        GenericRestConfig,
    )

    try:
        GenericRestConfig(request.config)
    except ValueError as exc:
        return {"ok": False, "stage": "config_validation", "error": str(exc)}
    adapter = GenericRestAdapter(
        config=request.config,
        credentials=request.credentials,
        paper=request.paper,
    )
    try:
        await adapter.authenticate()
        balance: dict = {}
        try:
            balance = await adapter.get_account_balance()
        except Exception as exc:  # noqa: BLE001
            # Auth succeeded but balance read failed — still return ok=True
            # so the user knows credentials are accepted; surface the detail.
            logger.info("Test-REST balance failed (auth ok): %s", exc)
        return {"ok": True, "balance": balance}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "authenticate", "error": str(exc)}
    finally:
        await adapter.disconnect()


def json_dumps_safe(payload: dict) -> str:
    """Defensive JSON dump that strips any non-serialisable values."""
    return json.dumps(payload, default=str)


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
            message=(f"Successfully connected to {request.broker_type} ({request.environment})"),
        )

    except (ValueError, BrokerConnectionError) as exc:
        # Do NOT echo the exception text — it may contain credential fragments.
        logger.exception("Broker setup failed")
        raise HTTPException(status_code=400, detail="Broker setup failed") from exc
    except HTTPException:
        raise
    except Exception as exc:
        # Authentication / network errors from broker plugins land here too;
        # treat them as 400 (user error: wrong creds / wrong endpoint) rather
        # than 500 (server bug). The exception text is *not* leaked since the
        # plugin classes are responsible for redacting their own messages.
        cls = type(exc).__name__
        if "Auth" in cls or "Network" in cls or "Timeout" in cls or "Connection" in cls:
            logger.exception("Broker auth/network error during setup")
            raise HTTPException(status_code=400, detail=f"Broker setup failed ({cls})") from exc
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
                    ml_score=None,
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

        # --------------------------------------------------------------
        # ML Gate (Phase 1) — extract features and (optionally) score.
        #
        # Behaviour matrix:
        #   ML_GATE_MODE=off      → always pass-through, score recorded only
        #   ML_GATE_MODE=advisory → recommend reject below threshold but allow
        #   ML_GATE_MODE=enforce  → block submit when score < ML_THRESHOLD
        #
        # When no model is loaded yet (cold-start), every mode pass-throughs;
        # we only record the *absence* of a score for later analysis.
        # --------------------------------------------------------------
        existing_open = (
            db.query(Position)
            .filter(Position.session_id == session_id, Position.status == "OPEN")
            .count()
        )
        recent_losses = (
            db.query(TradeOutcome)
            .filter(
                TradeOutcome.session_id == session_id,
                TradeOutcome.outcome == "LOSS",
            )
            .order_by(TradeOutcome.closed_at.desc())
            .limit(3)
            .count()
        )
        rl_row = db.query(RiskLimit).filter(RiskLimit.session_id == session_id).first()
        drawdown_pct = float(rl_row.current_drawdown_pct) if rl_row else 0.0

        feature_snapshot = extract_features(
            side=request.side,
            entry_price=float(request.entry_price),
            stop_loss=float(request.stop_loss),
            take_profit=float(request.take_profit),
            size=float(request.size),
            account_balance=float(account_balance),
            grading_criteria=request.grading_criteria,
            drawdown_pct=drawdown_pct,
            open_position_count=existing_open,
            losing_streak=recent_losses,
            macro_aligned=request.macro_aligned,
        )
        ml_score = score_features(feature_snapshot)
        ml_threshold = float(os.getenv("ML_THRESHOLD", "0.5"))
        ml_mode = os.getenv("ML_GATE_MODE", "advisory").lower()

        if ml_score is not None and ml_mode == "enforce" and ml_score < ml_threshold:
            db.add(
                AuditLog(
                    session_id=session_id,
                    action="ORDER_REJECTED",
                    symbol=request.symbol,
                    details=(f"ML gate rejected: score {ml_score:.3f} < {ml_threshold}"),
                    severity="WARNING",
                )
            )
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Order rejected by ML gate (score {ml_score:.3f} < {ml_threshold})",
            )

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

        # Phase 0: persist a frozen feature snapshot for ML training.
        outcome_row = TradeOutcome(
            session_id=session_id,
            order_id=broker_order.order_id,
            symbol=request.symbol,
            side=request.side,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            size=request.size,
            ml_score_at_submit=ml_score,
            **{k: v for k, v in feature_snapshot.as_dict().items() if k.startswith("f_")},
        )
        db.add(outcome_row)

        db.add(
            AuditLog(
                session_id=session_id,
                action="ORDER_SUBMITTED",
                symbol=request.symbol,
                details=(
                    f"Order {broker_order.order_id} submitted: "
                    f"{request.side} {request.size} @ {request.entry_price}"
                    + (f" · ml_score={ml_score:.3f}" if ml_score is not None else "")
                ),
                severity="INFO",
            )
        )
        db.commit()

        logger.info(
            "Order submitted: %s - %s (ml_score=%s)",
            broker_order.order_id,
            request.symbol,
            f"{ml_score:.3f}" if ml_score is not None else "n/a",
        )

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
            ml_score=ml_score,
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

        # Phase 0: resolve the trade-outcome row for ML training data.
        _resolve_outcome(db, order_id, status="CANCELLED", closed_price=None)

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
# Manual outcome resolution — used when the broker closes a position outside
# this API (SL/TP hit, broker UI, etc.) so the ML training data stays in
# sync. The endpoint is idempotent.
# ---------------------------------------------------------------------------


class CloseTradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    closed_price: Decimal = Field(..., gt=Decimal(0))
    status: str = Field("FILLED", description="FILLED, CANCELLED, or REJECTED")


@app.post(
    "/api/v1/orders/{order_id}/close",
    dependencies=[Depends(require_api_key)],
)
async def close_order(
    order_id: str,
    request: CloseTradeRequest,
    session_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db_session),
):
    """Close an order with a known fill price; resolves the ML outcome row."""
    try:
        order = (
            db.query(Order)
            .filter(Order.order_id == order_id, Order.session_id == session_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order.status = request.status.upper()
        order.filled_at = datetime.utcnow()
        order.avg_fill_price = request.closed_price

        _resolve_outcome(
            db,
            order_id,
            status=request.status.upper(),
            closed_price=float(request.closed_price),
        )

        outcome_row = db.query(TradeOutcome).filter(TradeOutcome.order_id == order_id).first()
        db.add(
            AuditLog(
                session_id=session_id,
                action="ORDER_FILLED" if request.status.upper() == "FILLED" else "ORDER_CANCELLED",
                symbol=order.symbol,
                details=(
                    f"Order {order_id} closed @ {request.closed_price} "
                    f"({outcome_row.outcome if outcome_row else 'n/a'})"
                ),
                severity="INFO",
            )
        )
        db.commit()
        return {
            "order_id": order_id,
            "status": order.status,
            "outcome": outcome_row.outcome if outcome_row else None,
            "pnl": float(outcome_row.pnl) if outcome_row and outcome_row.pnl is not None else None,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Close-order failed")
        raise HTTPException(status_code=500, detail="Close failed") from None


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
                    _resolve_outcome(db, order.order_id, status="CANCELLED", closed_price=None)
                    cancelled.append(order.order_id)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Halt: cancel failed for %s", order.order_id)
                    failed.append({"order_id": order.order_id, "error": str(exc)})

        # Flip the risk limit row to halted so the engine refuses new orders.
        risk_limit = db.query(RiskLimit).filter(RiskLimit.session_id == session_id).first()
        if risk_limit:
            risk_limit.is_halted = True

        db.add(
            AuditLog(
                session_id=session_id,
                action="SESSION_HALTED",
                details=(f"Emergency halt: {len(cancelled)} cancelled, {len(failed)} failed"),
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
            message=(f"Halt executed: {len(cancelled)} order(s) cancelled, {len(failed)} failed"),
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
                    detail=(f"Unknown category. Allowed: {[c.value for c in EventCategory]}"),
                ) from exc
            events = [e for e in events if e.category == cat]

        events_sorted = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
        return {
            "count": len(events_sorted),
            "total": len(_macro_fetcher.events),
            "events": [
                {**e.to_dict(), "score": _event_scorer.score_event(e)} for e in events_sorted
            ],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Macro events fetch failed")
        raise HTTPException(status_code=500, detail="Macro fetch failed") from None


@app.get("/api/v1/macro/sources")
async def macro_sources():
    """List which live providers feed the macro store and what the cadence is."""
    enable_gdelt = os.getenv("MACRO_GDELT_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
    enable_gdacs = os.getenv("MACRO_GDACS_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
    from app.macro import DEFAULT_PACKS  # noqa: PLC0415

    return {
        "providers": {
            "gdelt": {
                "enabled": enable_gdelt,
                "poll_seconds": float(os.getenv("MACRO_GDELT_POLL_SECONDS", "90")),
                "min_domains": int(os.getenv("MACRO_GDELT_MIN_DOMAINS", "2")),
                "window_minutes": int(os.getenv("MACRO_GDELT_WINDOW_MINUTES", "60")),
                "packs": [
                    {"name": p.name, "description": p.description, "query": p.gdelt_query}
                    for p in DEFAULT_PACKS
                ],
            },
            "gdacs": {
                "enabled": enable_gdacs,
                "poll_seconds": float(os.getenv("MACRO_GDACS_POLL_SECONDS", "300")),
                "alert_levels": ["Red", "Orange"],
            },
        },
        "store": {
            "total_events": len(_macro_fetcher.events),
            "by_source": {
                src: sum(1 for e in _macro_fetcher.events if e.source == src)
                for src in {e.source for e in _macro_fetcher.events}
            },
        },
    }


@app.get("/api/v1/macro/upcoming")
async def macro_upcoming(hours: int = Query(72, ge=1, le=720)):
    """Events whose timestamp lies in the next N hours."""
    from datetime import timedelta

    now = datetime.utcnow()
    horizon = now + timedelta(hours=hours)
    upcoming = [e for e in _macro_fetcher.events if now <= e.timestamp <= horizon]
    upcoming_sorted = sorted(upcoming, key=lambda e: e.timestamp)
    return {
        "count": len(upcoming_sorted),
        "horizon_hours": hours,
        "events": [{**e.to_dict(), "score": _event_scorer.score_event(e)} for e in upcoming_sorted],
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
# ML model lifecycle (Phase 1 + 2)
# ---------------------------------------------------------------------------


class _ScoreRequest(BaseModel):
    """Score a feature vector or a set of grading criteria."""

    model_config = ConfigDict(extra="forbid")

    side: str = Field(..., description="BUY or SELL")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    size: float = Field(..., gt=0)
    account_balance: float | None = Field(None, gt=0)
    grading_criteria: dict[str, bool] | None = None
    drawdown_pct: float | None = None
    open_position_count: int | None = None
    losing_streak: int | None = None
    macro_aligned: bool | None = None
    correlation_score: float | None = None
    volatility_pct: float | None = None


@app.get("/api/v1/ml/status")
async def ml_status():
    """Diagnostic: which checkpoint is loaded, what the gate mode is."""
    return {
        **model_status(),
        "gate_mode": os.getenv("ML_GATE_MODE", "advisory"),
        "threshold": float(os.getenv("ML_THRESHOLD", "0.5")),
    }


@app.post("/api/v1/ml/score")
async def ml_score(request: _ScoreRequest):
    """Return ML probability-of-success for an explicit setup."""
    snap = extract_features(
        side=request.side,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        size=request.size,
        account_balance=request.account_balance,
        grading_criteria=request.grading_criteria,
        drawdown_pct=request.drawdown_pct,
        open_position_count=request.open_position_count,
        losing_streak=request.losing_streak,
        macro_aligned=request.macro_aligned,
        correlation_score=request.correlation_score,
        volatility_pct=request.volatility_pct,
    )
    score = score_features(snap)
    return {
        "score": score,
        "features": snap.as_dict(),
        "model_loaded": score is not None,
    }


@app.post(
    "/api/v1/ml/retrain",
    dependencies=[Depends(require_api_key)],
)
async def ml_retrain(
    epochs: int = Query(200, ge=10, le=2000),
    learning_rate: float = Query(1e-3, gt=0, le=1.0),
    activate: bool = Query(True),
    db: Session = Depends(get_db_session),
):
    """Train the SetupQualityScorer on accumulated trade outcomes."""
    from app.ml.trainer import train_from_outcomes  # noqa: PLC0415

    try:
        result = train_from_outcomes(
            db,
            epochs=epochs,
            learning_rate=learning_rate,
            activate=activate,
        )
        return result.__dict__
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Retrain failed")
        raise HTTPException(status_code=500, detail="Retrain failed") from None


@app.get(
    "/api/v1/ml/checkpoints",
    dependencies=[Depends(require_api_key)],
)
async def ml_checkpoints():
    from app.ml.trainer import list_checkpoints  # noqa: PLC0415

    return {"checkpoints": list_checkpoints()}


@app.post(
    "/api/v1/ml/checkpoints/{name}/activate",
    dependencies=[Depends(require_api_key)],
)
async def ml_activate_checkpoint(name: str):
    from app.ml.trainer import activate_checkpoint  # noqa: PLC0415

    if not activate_checkpoint(name):
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {name}")
    return {"activated": name, **model_status()}


class _BootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbols: list[str] | None = Field(
        None,
        description="yfinance symbols (default: forex/crypto/metals universe)",
    )
    period: str = Field("2y", description="yfinance lookback period (e.g. 1y, 2y, 5y)")
    epochs: int = Field(200, ge=10, le=2000)
    learning_rate: float = Field(1e-3, gt=0, le=1.0)
    activate: bool = True


# ---------------------------------------------------------------------------
# Autopilot — TradingView webhook + state controls
# ---------------------------------------------------------------------------


from app.autopilot import (  # noqa: E402
    TradingViewSignal,
)
from app.autopilot import (
    get_state as _ap_get_state,
)
from app.autopilot import (
    record as _ap_record,
)
from app.autopilot import (
    set_state as _ap_set_state,
)
from app.autopilot import (
    verify_secret as _ap_verify_secret,
)


class _AutopilotConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str | None = Field(None, description="off | dry_run | live")
    session_id: str | None = Field(None, max_length=64)
    threshold: float | None = Field(None, ge=0.0, le=1.0)
    require_grade: list[str] | None = None


@app.get(
    "/api/v1/autopilot",
    dependencies=[Depends(require_api_key)],
)
async def autopilot_status():
    return _ap_get_state()


@app.post(
    "/api/v1/autopilot",
    dependencies=[Depends(require_api_key)],
)
async def autopilot_configure(request: _AutopilotConfigRequest):
    try:
        return _ap_set_state(
            mode=request.mode,
            session_id=request.session_id,
            threshold=request.threshold,
            require_grade=request.require_grade,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/webhook/tradingview/{secret}")
async def tradingview_webhook(
    secret: str,
    payload: dict,
    db: Session = Depends(get_db_session),
):
    """Receive a TradingView Pine alert and (optionally) auto-place an order.

    The shared secret lives in the URL because Pine alerts can't easily set
    headers. Use a long, randomly-generated value in ``TV_WEBHOOK_SECRET``.

    Behaviour: parse → grader → ML score → risk-engine validation → submit.
    The autopilot mode (off / dry_run / live) decides whether to actually
    submit. ``dry_run`` is your debugging mode.
    """
    if not _ap_verify_secret(secret):
        # Don't leak whether the secret was missing or wrong.
        raise HTTPException(status_code=401, detail="Unauthorized")

    state = _ap_get_state()
    decision: dict = {
        "received_at": datetime.utcnow().isoformat(),
        "mode": state["mode"],
        "decision": "ignored",
        "reasons": [],
    }

    if state["mode"] == "off":
        decision["decision"] = "ignored"
        decision["reasons"].append("autopilot is off")
        _ap_record(decision)
        return decision

    try:
        signal = TradingViewSignal.from_payload(payload)
    except ValueError as exc:
        decision["decision"] = "rejected"
        decision["reasons"].append(f"payload: {exc}")
        _ap_record(decision)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision["signal"] = {
        "symbol": signal.symbol,
        "side": signal.side,
        "entry": signal.entry,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "size": signal.size,
    }

    session_id = state["session_id"]
    if not session_id:
        decision["decision"] = "rejected"
        decision["reasons"].append("autopilot session_id not configured")
        _ap_record(decision)
        return decision

    broker_session = db.query(BrokerSession).filter(BrokerSession.session_id == session_id).first()
    if not broker_session:
        decision["decision"] = "rejected"
        decision["reasons"].append("configured session not found")
        _ap_record(decision)
        return decision

    # Grade the setup with the existing 7-criteria grader so we can apply
    # the require_grade filter. We default missing criteria to True for the
    # evidence-based ones (TV alert claims it found them) and let the engine
    # enforce R/R + macro alignment from the payload.
    crits = signal.grading_criteria or {}
    setup = _trade_grader.grade(
        symbol=signal.symbol,
        direction="LONG" if signal.side == "BUY" else "SHORT",
        entry_price=signal.entry,
        stop_loss_price=signal.stop_loss,
        tp1_price=(signal.entry + (signal.take_profit - signal.entry) * 2 / 3),
        tp2_price=signal.take_profit,
        criteria=SetupCriteria(
            structural_level=bool(crits.get("structural_level", True)),
            liquidity_sweep=bool(crits.get("liquidity_sweep", True)),
            momentum=bool(crits.get("momentum", True)),
            volume=bool(crits.get("volume", True)),
            risk_reward=False,  # validated by grader
            macro_alignment=bool(crits.get("macro_alignment", signal.macro_aligned or False)),
            no_contradiction=bool(crits.get("no_contradiction", True)),
        ),
        confidence=signal.confidence or 70.0,
    )
    decision["grade"] = setup.grade
    decision["score_7"] = setup.setup_score

    if setup.grade not in state["require_grade"]:
        decision["decision"] = "rejected"
        decision["reasons"].append(f"grade {setup.grade} not in {state['require_grade']}")
        _ap_record(decision)
        return decision

    # Position size: use TV's value if present, otherwise default 2% risk
    # against the broker's reported balance.
    if signal.size is not None and signal.size > 0:
        size = signal.size
    else:
        try:
            adapter = await router.get_api_adapter(session_id)
            balance = await adapter.get_balance()
            balance_value = float(balance.get("balance", 10000))
        except Exception:  # noqa: BLE001
            balance_value = 10000.0
        risk_distance = abs(signal.entry - signal.stop_loss)
        size = (balance_value * 0.02 / risk_distance) if risk_distance else 0.0
    decision["size"] = size

    if size <= 0:
        decision["decision"] = "rejected"
        decision["reasons"].append("computed position size is zero")
        _ap_record(decision)
        return decision

    if state["mode"] == "dry_run":
        decision["decision"] = "approved_dry_run"
        decision["reasons"].append("dry_run mode — order NOT submitted")
        _ap_record(decision)
        return decision

    # Live: forward to the existing submit pipeline so the same risk + ML
    # gates run as for a manual click.
    submit_request = OrderSubmitRequest(
        symbol=signal.symbol,
        side=signal.side,
        size=Decimal(str(size)),
        entry_price=Decimal(str(signal.entry)),
        stop_loss=Decimal(str(signal.stop_loss)),
        take_profit=Decimal(str(signal.take_profit)),
        idempotency_key=f"tv-{int(datetime.utcnow().timestamp() * 1000)}",
        grading_criteria=crits or None,
        macro_aligned=signal.macro_aligned,
    )
    try:
        result = await submit_order(submit_request, session_id=session_id, db=db)
    except HTTPException as exc:
        decision["decision"] = "rejected"
        decision["reasons"].append(f"submit refused: {exc.detail}")
        _ap_record(decision)
        return decision

    decision["decision"] = "submitted"
    decision["order_id"] = result.order_id
    decision["ml_score"] = result.ml_score
    _ap_record(decision)
    return decision


class _MlBacktestRequest(BaseModel):
    """Replay synthetic setups (yfinance-derived) through the active model.

    Use this to *out-of-sample test* the active checkpoint before flipping
    the gate to ``enforce`` or arming the autopilot. The simulator uses a
    fixed 1:3 R/R, 2% per-trade risk, sequentially compounded equity.
    """

    model_config = ConfigDict(extra="forbid")

    symbols: list[str] | None = None
    period: str = Field("2y", description="yfinance lookback window")
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    starting_capital: float = Field(10000.0, gt=0)
    risk_per_trade_pct: float = Field(0.02, gt=0, le=0.1)
    rr: float = Field(3.0, ge=1.0, le=10.0)


@app.post(
    "/api/v1/ml/backtest",
    dependencies=[Depends(require_api_key)],
)
async def ml_backtest(request: _MlBacktestRequest):
    """Simulate trading the active ML model on synthetic setups."""
    from app.ml.bootstrap import DEFAULT_SYMBOLS, build_synthetic_dataset  # noqa: PLC0415
    from app.ml.service import (  # noqa: PLC0415
        FEATURE_NAMES,
        FeatureSnapshot,
        score_features,
    )

    syms = list(request.symbols) if request.symbols else list(DEFAULT_SYMBOLS)
    X, y, processed = build_synthetic_dataset(syms, period=request.period)
    if not X:
        raise HTTPException(
            status_code=400,
            detail="No samples generated — check internet / yfinance access.",
        )

    equity = float(request.starting_capital)
    equity_curve = [equity]
    risk_amount = equity * request.risk_per_trade_pct
    wins = losses = skipped_lowscore = skipped_no_model = 0
    score_distribution: list[float] = []

    for features, label in zip(X, y, strict=False):
        snap = FeatureSnapshot(**dict(zip(FEATURE_NAMES, features, strict=False)))
        score = score_features(snap)
        if score is None:
            skipped_no_model += 1
            equity_curve.append(equity)
            continue
        score_distribution.append(score)
        if score < request.threshold:
            skipped_lowscore += 1
            equity_curve.append(equity)
            continue
        # Approved trade — apply outcome
        if label >= 0.5:
            equity += risk_amount * request.rr
            wins += 1
        else:
            equity -= risk_amount
            losses += 1
        # Re-anchor risk to compounded equity so we don't go negative on
        # a deep drawdown.
        risk_amount = max(equity * request.risk_per_trade_pct, 0.0)
        equity_curve.append(equity)

    trades_taken = wins + losses
    win_rate = (wins / trades_taken) if trades_taken else 0.0
    expectancy_r = ((wins * request.rr) - losses) / trades_taken if trades_taken else 0.0
    return {
        "starting_capital": float(request.starting_capital),
        "ending_capital": equity,
        "roi_pct": (equity - request.starting_capital) / request.starting_capital * 100,
        "trades_taken": trades_taken,
        "trades_skipped": skipped_lowscore + skipped_no_model,
        "skipped_lowscore": skipped_lowscore,
        "skipped_no_model": skipped_no_model,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "expectancy_r": expectancy_r,
        "rr": request.rr,
        "threshold": request.threshold,
        "symbols_processed": processed,
        "samples": len(X),
        "equity_curve": equity_curve,
        "score_distribution": score_distribution,
    }


class _WalkForwardRequest(BaseModel):
    """Walk-forward validation: train on the chronologically-earlier slice,
    test on the later slice that the model has never seen.

    This is the only honest answer to "is my ML model actually any good?"
    — in-sample accuracy is meaningless on a model trained and evaluated on
    the same data.
    """

    model_config = ConfigDict(extra="forbid")

    symbols: list[str] | None = None
    period: str = Field("3y")
    train_fraction: float = Field(0.7, ge=0.3, le=0.9)
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    starting_capital: float = Field(10000.0, gt=0)
    risk_per_trade_pct: float = Field(0.02, gt=0, le=0.1)
    rr: float = Field(3.0, ge=1.0, le=10.0)
    epochs: int = Field(200, ge=10, le=2000)
    learning_rate: float = Field(1e-3, gt=0, le=1.0)


@app.post(
    "/api/v1/ml/walkforward",
    dependencies=[Depends(require_api_key)],
)
async def ml_walkforward(request: _WalkForwardRequest):
    """Train an isolated model on the in-sample window, test on out-of-sample."""
    from app.ml.bootstrap import DEFAULT_SYMBOLS, build_synthetic_dataset  # noqa: PLC0415

    try:
        import torch  # noqa: PLC0415
        import torch.nn as nn  # noqa: PLC0415

        from ml_bot_phase1.src.models.setup_scorer import SetupQualityScorer  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"PyTorch not available: {exc}",
        ) from exc

    syms = list(request.symbols) if request.symbols else list(DEFAULT_SYMBOLS)
    X, y, processed = build_synthetic_dataset(syms, period=request.period)
    if len(X) < 30:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Need ≥ 30 samples for a meaningful walk-forward (got {len(X)}). "
                "Try a longer period or more symbols."
            ),
        )

    split_at = int(len(X) * request.train_fraction)
    X_train, y_train = X[:split_at], y[:split_at]
    X_test, y_test = X[split_at:], y[split_at:]
    if not X_test or not X_train:
        raise HTTPException(status_code=400, detail="Empty train or test split")

    train_wins = int(sum(y_train))
    train_losses = len(y_train) - train_wins
    if train_wins == 0 or train_losses == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Train split has only one class (wins={train_wins}, "
                f"losses={train_losses}); pick a longer period or different symbols."
            ),
        )

    # Train on the in-sample window only — never touch X_test.
    Xt = torch.tensor(X_train, dtype=torch.float32)
    yt = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    pos_weight = torch.tensor([train_losses / max(train_wins, 1)], dtype=torch.float32)
    criterion = nn.BCELoss()
    model = SetupQualityScorer(input_size=Xt.shape[1], device="cpu")
    optim = torch.optim.Adam(model.parameters(), lr=request.learning_rate)

    train_loss = train_acc = 0.0
    model.train()
    for _ in range(request.epochs):
        optim.zero_grad()
        preds = model(Xt)
        weights = torch.where(yt > 0.5, pos_weight, torch.ones_like(yt))
        loss = (criterion(preds, yt) * weights).mean()
        loss.backward()
        optim.step()
        train_loss = float(loss.item())
        with torch.no_grad():
            train_acc = float(((preds >= 0.5).float() == yt).float().mean().item())

    # Score every test sample exactly once with the frozen model.
    model.eval()
    with torch.no_grad():
        test_scores = model(torch.tensor(X_test, dtype=torch.float32)).squeeze(-1).tolist()

    # Replay both windows so the user can see the difference visually.
    def _simulate(X_slice, y_slice, scores):
        equity = float(request.starting_capital)
        curve = [equity]
        risk_amount = equity * request.risk_per_trade_pct
        wins = losses = skipped = 0
        for label, score in zip(y_slice, scores, strict=False):
            if score < request.threshold:
                skipped += 1
                curve.append(equity)
                continue
            if label >= 0.5:
                equity += risk_amount * request.rr
                wins += 1
            else:
                equity -= risk_amount
                losses += 1
            risk_amount = max(equity * request.risk_per_trade_pct, 0.0)
            curve.append(equity)
        trades = wins + losses
        return {
            "trades_taken": trades,
            "trades_skipped": skipped,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / trades) if trades else 0.0,
            "ending_capital": equity,
            "roi_pct": (equity - request.starting_capital) / request.starting_capital * 100,
            "expectancy_r": (((wins * request.rr) - losses) / trades) if trades else 0.0,
            "equity_curve": curve,
        }

    with torch.no_grad():
        train_scores = model(torch.tensor(X_train, dtype=torch.float32)).squeeze(-1).tolist()

    in_sample = _simulate(X_train, y_train, train_scores)
    out_sample = _simulate(X_test, y_test, test_scores)

    return {
        "samples": {
            "total": len(X),
            "train": len(X_train),
            "test": len(X_test),
            "split_at_index": split_at,
        },
        "training": {
            "wins": train_wins,
            "losses": train_losses,
            "epochs": request.epochs,
            "final_loss": train_loss,
            "final_accuracy": train_acc,
        },
        "in_sample": in_sample,
        "out_of_sample": out_sample,
        "honest_verdict": _walkforward_verdict(in_sample, out_sample),
        "threshold": request.threshold,
        "rr": request.rr,
        "symbols_processed": processed,
        "score_distribution": {
            "train": train_scores,
            "test": test_scores,
        },
    }


def _walkforward_verdict(in_sample: dict, out_sample: dict) -> str:
    """Plain-language verdict so users don't have to interpret the metrics."""
    in_roi = in_sample["roi_pct"]
    out_roi = out_sample["roi_pct"]
    out_trades = out_sample["trades_taken"]
    if out_trades == 0:
        return (
            "OUT-OF-SAMPLE took no trades — the model rejected every test setup. "
            "Lower the threshold or retrain with more diverse data."
        )
    if out_roi <= 0:
        return (
            f"OVERFIT: in-sample ROI {in_roi:+.1f}% but out-of-sample {out_roi:+.1f}%. "
            "Do NOT enable the live ML gate with this checkpoint."
        )
    if in_roi > 0 and out_roi >= in_roi * 0.4:
        return (
            f"PROMISING: in-sample {in_roi:+.1f}% / out-of-sample {out_roi:+.1f}% "
            f"({out_sample['win_rate'] * 100:.0f}% win rate). Still validate live with small size."
        )
    return (
        f"WEAK SIGNAL: in {in_roi:+.1f}% / out {out_roi:+.1f}%. "
        "Some predictive power but not robust — needs more data."
    )


@app.post(
    "/api/v1/ml/bootstrap",
    dependencies=[Depends(require_api_key)],
)
async def ml_bootstrap(
    request: _BootstrapRequest,
    db: Session = Depends(get_db_session),
):
    """Phase 3: build a synthetic training set from yfinance OHLCV and train.

    Use this when ``trade_outcomes`` doesn't yet have enough live data — the
    resulting model is a *prior*, not a fortune-teller. Live retrain on real
    outcomes is what makes it useful over time.
    """
    from app.ml.bootstrap import bootstrap  # noqa: PLC0415

    try:
        return bootstrap(
            db,
            symbols=request.symbols,
            period=request.period,
            epochs=request.epochs,
            learning_rate=request.learning_rate,
            activate=request.activate,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Bootstrap failed")
        raise HTTPException(status_code=500, detail="Bootstrap failed") from None


@app.get(
    "/api/v1/ml/outcomes",
    dependencies=[Depends(require_api_key)],
)
async def ml_outcomes(
    session_id: str | None = Query(None, max_length=64),
    outcome: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=1_000_000),
    db: Session = Depends(get_db_session),
):
    """List trade outcomes for inspection / export."""
    q = db.query(TradeOutcome)
    if session_id:
        q = q.filter(TradeOutcome.session_id == session_id)
    if outcome:
        q = q.filter(TradeOutcome.outcome == outcome.upper())
    total = q.count()
    rows = q.order_by(TradeOutcome.created_at.desc()).offset(offset).limit(limit).all()

    from sqlalchemy import func as _sa_func  # noqa: PLC0415

    summary_counts = dict(
        db.query(TradeOutcome.outcome, _sa_func.count(TradeOutcome.id))
        .group_by(TradeOutcome.outcome)
        .all()
    )

    return {
        "total": total,
        "summary": summary_counts,
        "items": [
            {
                "id": r.id,
                "order_id": r.order_id,
                "session_id": r.session_id,
                "symbol": r.symbol,
                "side": r.side,
                "entry_price": float(r.entry_price),
                "stop_loss": float(r.stop_loss),
                "take_profit": float(r.take_profit),
                "size": float(r.size),
                "ml_score_at_submit": r.ml_score_at_submit,
                "outcome": r.outcome,
                "pnl": float(r.pnl) if r.pnl is not None else None,
                "closed_price": float(r.closed_price) if r.closed_price is not None else None,
                "created_at": r.created_at.isoformat(),
                "closed_at": r.closed_at.isoformat() if r.closed_at else None,
                "features": {
                    name: getattr(r, name)
                    for name in (
                        "f_structural_level",
                        "f_liquidity_sweep",
                        "f_momentum",
                        "f_volume",
                        "f_risk_reward",
                        "f_macro_alignment",
                        "f_on_chain",
                        "f_volatility",
                        "f_trend_strength",
                        "f_drawdown",
                        "f_time_since_trade",
                        "f_correlation_spy",
                        "f_position_size",
                        "f_margin_util",
                        "f_concurrent_trades",
                        "f_losing_streak",
                        "f_profit_distance",
                        "f_mtf_alignment",
                        "f_price_action",
                        "f_confluence",
                    )
                },
            }
            for r in rows
        ],
    }


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
