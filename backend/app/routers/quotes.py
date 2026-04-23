"""
Quotes API endpoints
GET /quotes - Real-time quotes
"""
from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter()

@router.get("/quotes")
async def get_quotes(
    instruments: str = Query("EUR_USD,GBP_USD,USD_JPY"),
    source: Optional[str] = Query("oanda")
):
    """
    Get real-time quotes for specified instruments
    
    Args:
        instruments: Comma-separated list of instrument codes (e.g., EUR_USD)
        source: Data source (oanda or yfinance)
    
    Returns:
        List of quote objects with bid/ask prices
    """
    # Mock response - will be replaced with real OANDA/yfinance data
    return {
        "instruments": instruments.split(","),
        "quotes": [
            {
                "instrument": "EUR_USD",
                "bid": 1.0850,
                "ask": 1.0851,
                "time": "2026-04-23T18:04:00Z",
                "source": source
            },
            {
                "instrument": "GBP_USD",
                "bid": 1.2750,
                "ask": 1.2751,
                "time": "2026-04-23T18:04:00Z",
                "source": source
            }
        ],
        "status": "ok"
    }
