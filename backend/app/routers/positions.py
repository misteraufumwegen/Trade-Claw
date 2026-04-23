"""
Positions API endpoints
GET /positions - List active positions
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/positions")
async def get_positions():
    """
    Get all active positions
    
    Returns:
        List of position objects with instrument, units, price, P&L
    """
    # Mock response - will be replaced with real OANDA data
    return {
        "positions": [
            {
                "instrument": "EUR_USD",
                "units": 100000,
                "entry_price": 1.0800,
                "current_price": 1.0850,
                "unrealized_pnl": 500.00,
                "percentage_return": 0.46,
                "pip_value": 10.00
            },
            {
                "instrument": "GBP_USD",
                "units": 50000,
                "entry_price": 1.2700,
                "current_price": 1.2750,
                "unrealized_pnl": 250.00,
                "percentage_return": 0.39,
                "pip_value": 5.00
            }
        ],
        "total_unrealized_pnl": 750.00,
        "count": 2,
        "status": "ok"
    }
