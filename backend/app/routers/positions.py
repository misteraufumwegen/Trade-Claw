"""
Positions API endpoints
GET /positions - List active positions
"""
import logging
from fastapi import APIRouter, HTTPException
from app.services.oanda import oanda_client
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/positions")
async def get_positions():
    """
    Get all active positions
    
    Returns:
        List of position objects with instrument, units, price, P&L
    """
    try:
        # Get positions from OANDA
        positions_result = await oanda_client.get_positions()
        
        if positions_result.get("status") != "ok":
            logger.error("Failed to retrieve positions from OANDA")
            raise HTTPException(status_code=502, detail="Failed to retrieve positions")
        
        positions = positions_result.get("positions", [])
        
        # Get current quotes to calculate P&L
        if positions:
            instrument_list = [p["instrument"] for p in positions]
            quotes_result = await oanda_client.get_quotes(instrument_list)
            
            if quotes_result.get("status") == "ok":
                quote_map = {q["instrument"]: q for q in quotes_result.get("quotes", [])}
                
                # Update positions with current prices
                for pos in positions:
                    if pos["instrument"] in quote_map:
                        current_price = (quote_map[pos["instrument"]]["bid"] + quote_map[pos["instrument"]]["ask"]) / 2
                        pos["current_price"] = current_price
                        
                        # Recalculate P&L
                        pip_value = pos.get("pip_value", 10.0)
                        entry_price = pos["entry_price"]
                        units = pos["units"]
                        
                        pnl = (current_price - entry_price) * units / 0.0001 * pip_value * 0.0001
                        pos["unrealized_pnl"] = pnl
                        
                        if entry_price > 0:
                            pos["percentage_return"] = ((current_price - entry_price) / entry_price) * 100
        
        # Calculate totals
        total_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)
        
        return {
            "positions": positions,
            "total_unrealized_pnl": total_pnl,
            "count": len(positions),
            "status": "ok"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Position request failed: {str(e)}")
