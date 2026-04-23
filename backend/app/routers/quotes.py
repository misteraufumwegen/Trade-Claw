"""
Quotes API endpoints
GET /quotes - Real-time quotes
"""
import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.services.oanda import oanda_client
from app.services.yfinance import yfinance_client
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/quotes")
async def get_quotes(
    instruments: str = Query("EUR_USD,GBP_USD,USD_JPY", description="Comma-separated instrument codes"),
    source: Optional[str] = Query("auto", description="Data source: auto, oanda, or yfinance")
):
    """
    Get real-time quotes for specified instruments
    
    Args:
        instruments: Comma-separated list of instrument codes (e.g., EUR_USD,GBP_USD)
        source: Data source (auto, oanda, or yfinance)
    
    Returns:
        List of quote objects with bid/ask prices
    """
    try:
        instrument_list = [i.strip() for i in instruments.split(",")]
        
        # Determine which data source to use
        if source == "auto":
            # Try OANDA first, fallback to yfinance
            result = await oanda_client.get_quotes(instrument_list)
            if result["status"] == "ok":
                return result
            
            # Fallback to yfinance
            if settings.FALLBACK_TO_YFINANCE:
                logger.info("OANDA unavailable, falling back to yfinance")
                result = await yfinance_client.get_quotes(instrument_list)
                if result["status"] == "ok":
                    return result
            
            raise HTTPException(status_code=503, detail="No data source available")
        
        elif source == "oanda":
            result = await oanda_client.get_quotes(instrument_list)
            if result["status"] != "ok":
                raise HTTPException(status_code=502, detail="OANDA request failed")
            return result
        
        elif source == "yfinance":
            result = await yfinance_client.get_quotes(instrument_list)
            if result["status"] != "ok":
                raise HTTPException(status_code=502, detail="yfinance request failed")
            return result
        
        else:
            raise HTTPException(status_code=400, detail="Invalid source. Use: auto, oanda, or yfinance")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quote request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quote request failed: {str(e)}")
