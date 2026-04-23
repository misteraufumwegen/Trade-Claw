"""
Trade-Claw Backend - FastAPI Entry Point
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import quotes, positions, orders, account, backtest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Trade-Claw API",
    description="Real-time Trading Dashboard Backend",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(quotes.router, prefix="/api", tags=["quotes"])
app.include_router(positions.router, prefix="/api", tags=["positions"])
app.include_router(orders.router, prefix="/api", tags=["orders"])
app.include_router(account.router, prefix="/api", tags=["account"])
app.include_router(backtest.router, prefix="/api", tags=["backtest"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "trade-claw-api"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Trade-Claw API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
