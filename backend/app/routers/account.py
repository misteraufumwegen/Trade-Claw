"""
Account API endpoints
GET /account - Account information (balance, equity, margin)
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/account")
async def get_account():
    """
    Get account information
    
    Returns:
        Account summary with balance, equity, margin, P&L
    """
    # Mock response - will be replaced with real OANDA data
    return {
        "account_id": "001-001-1234567-001",
        "balance": 100000.00,
        "equity": 100750.00,
        "margin_used": 10000.00,
        "margin_available": 90000.00,
        "margin_rate": 0.05,
        "unrealized_pnl": 750.00,
        "realized_pnl": 0.00,
        "total_pnl": 750.00,
        "currency": "USD",
        "last_transaction_id": "12345",
        "timestamp": "2026-04-23T18:04:00Z",
        "status": "ok"
    }
