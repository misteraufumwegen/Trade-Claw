"""
Trading Bot API - Main Application Entry Point
FastAPI-based REST API for trading bot management and execution.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime

# Import Backtest & Risk modules
from app.backtest import BacktestSimulator
from app.backtest.schemas import BacktestRequest, BacktestResponse, BacktestMetrics
from app.risk import RiskEngine
from app.risk.schemas import RiskVaultData
# Import Correlation module
from app.correlation.engine import CorrelationEngine
from app.correlation.schemas import CorrelationRequest, CorrelationResponse

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Trading Bot API",
    description="REST API for managing and executing trades across multiple brokers",
    version="0.1.0",
)

# CORS configuration
origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Trading Bot API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Trading Bot API shutting down...")


# =====================================================
# Health Check Endpoints
# =====================================================

@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns: 200 if service is healthy.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "trading-bot-api",
            "version": "0.1.0",
        }
    )


@app.get("/api/status", tags=["Health"])
async def status():
    """
    Detailed service status.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "components": {
                "api": "online",
                "database": "checking...",  # TODO: Add actual DB check
                "redis": "checking...",  # TODO: Add actual Redis check
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# =====================================================
# Backtest Endpoints
# =====================================================

backtest_simulator = BacktestSimulator(starting_capital=100.0)

@app.post("/api/backtest", tags=["Backtest"], response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Run on-demand backtest.
    
    Takes a list of trades and simulates them with realistic exit scenarios.
    Returns performance metrics (Win Rate, Profit Factor, ROI, Sharpe Ratio, etc.)
    """
    try:
        # Create fresh simulator instance
        simulator = BacktestSimulator(starting_capital=request.starting_capital)
        
        # Convert request trades to dict format
        trades = [t.dict() for t in request.trades]
        
        # Run backtest
        result = simulator.run_backtest(trades, only_grades=request.only_grades)
        
        # Build response
        metrics = BacktestMetrics(**result['metrics'])
        
        return BacktestResponse(
            success=True,
            timestamp=datetime.utcnow(),
            trades_executed=result['trades_executed'],
            metrics=metrics,
            trades=result['trades'],
            message=f"Backtest complete: {result['trades_executed']} trades executed"
        )
    
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")


@app.get("/api/backtest/status", tags=["Backtest"])
async def backtest_status():
    """
    Get backtest module status.
    """
    return {
        "status": "ready",
        "backtest_engine": "BacktestSimulator v1.0",
        "starting_capital": 100.0,
        "message": "Ready to run on-demand backtests"
    }


# =====================================================
# Correlation Engine Endpoints
# =====================================================

correlation_engine = CorrelationEngine(lookback_days=30)

@app.post("/api/correlation/analyze", tags=["Correlation"], response_model=CorrelationResponse)
async def analyze_correlation(request: CorrelationRequest):
    """
    Analyze correlation between assets.
    
    Computes pairwise correlations and determines trade eligibility.
    
    Request body example:
    {
        "assets": ["GLD", "SLV", "EUR/USD"],
        "threshold": 0.7,
        "lookback_days": 30
    }
    
    Response:
    - correlation_matrix: Dict of all pairwise correlations
    - avg_correlation: Average correlation score
    - trade_eligible: Whether assets are aligned for trading
    - reasoning: Human-readable explanation
    """
    try:
        # Mock price data generation (in production, fetch from historical data API)
        import numpy as np
        np.random.seed(42)  # Deterministic for testing
        
        asset_prices = {}
        for asset in request.assets:
            # Generate realistic mock prices
            prices = np.random.normal(100, 5, 30).tolist()  # 30 days of prices
            asset_prices[asset] = prices
        
        # Analyze correlations
        result = correlation_engine.analyze(
            asset_prices=asset_prices,
            threshold=request.threshold
        )
        
        return CorrelationResponse(**result)
    
    except Exception as e:
        logger.error(f"Correlation analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Correlation error: {str(e)}")


@app.get("/api/correlation/status", tags=["Correlation"])
async def correlation_status():
    """
    Get correlation engine status.
    """
    return {
        "status": "ready",
        "correlation_engine": "CorrelationEngine v1.0",
        "default_lookback_days": 30,
        "message": "Ready to analyze asset correlations"
    }


# =====================================================
# Risk Engine Endpoints
# =====================================================

risk_engine = RiskEngine()

@app.get("/api/risk/status", tags=["Risk"])
async def risk_status():
    """
    Get risk engine status.
    
    Returns:
    - Vault status (position size cap, drawdown limit, stop-loss immutability)
    - Halted status
    - Daily trade count
    """
    try:
        status = risk_engine.get_status()
        return {
            "status": "healthy" if not status['halted'] else "halted",
            "risk_engine": "RiskEngine v1.0",
            "vault_status": status['vault_status'],
            "halted": status['halted'],
            "timestamp": status['timestamp']
        }
    except Exception as e:
        logger.error(f"Risk status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/pre-trade-check", tags=["Risk"])
async def pre_trade_check(data: dict):
    """
    Pre-trade risk validation.
    
    Validates:
    - Position size (max 10% of account)
    - Drawdown (max -15% auto-halt)
    - Daily trade limit (max 10 per day)
    - Halt status
    
    Required fields:
    - symbol: Trading symbol
    - side: buy or sell
    - quantity: Order quantity
    - entry_price: Entry price
    - account_equity: Current account equity
    - stop_loss: Stop loss price
    - take_profit: Take profit price
    """
    try:
        approved, details = risk_engine.pre_trade_check(
            symbol=data.get('symbol'),
            side=data.get('side'),
            quantity=data.get('quantity'),
            entry_price=data.get('entry_price'),
            account_equity=data.get('account_equity'),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit')
        )
        
        return {
            "approved": approved,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Pre-trade check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/execute-trade", tags=["Risk"])
async def execute_trade(data: dict):
    """
    Execute trade with risk registration (stop-loss immutability, position tracking).
    
    Required fields:
    - trade_id: Unique trade identifier
    - symbol: Trading symbol
    - side: buy or sell
    - quantity: Order quantity
    - entry_price: Entry price
    - stop_loss: Stop loss price
    - take_profit: Take profit price
    """
    try:
        success = risk_engine.execute_trade(
            trade_id=data.get('trade_id'),
            symbol=data.get('symbol'),
            side=data.get('side'),
            quantity=data.get('quantity'),
            entry_price=data.get('entry_price'),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit')
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Trade execution failed")
        
        return {
            "success": True,
            "message": f"Trade {data.get('trade_id')} registered with hardened limits",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Trade execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Placeholder Routes (to be implemented)
# =====================================================

@app.get("/api/accounts", tags=["Accounts"])
async def get_accounts():
    """Get all connected broker accounts."""
    return {"accounts": [], "message": "Endpoints coming soon"}


@app.get("/api/positions", tags=["Positions"])
async def get_positions():
    """Get all open positions across all accounts."""
    return {"positions": [], "message": "Endpoints coming soon"}


@app.post("/api/orders", tags=["Orders"])
async def create_order():
    """Place a new order."""
    return {"message": "Order placement coming soon"}


@app.get("/api/orders", tags=["Orders"])
async def get_orders():
    """Get order history."""
    return {"orders": [], "message": "Endpoints coming soon"}


# =====================================================
# Root
# =====================================================

@app.get("/", tags=["Root"])
async def root():
    """API root."""
    return {
        "message": "Trading Bot API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health"
    }


# =====================================================
# Error Handlers
# =====================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
    )
