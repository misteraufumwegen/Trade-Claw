"""
Account API endpoints
GET /account - Account information (balance, equity, margin)
"""
import logging
from fastapi import APIRouter, HTTPException
from app.services.oanda import oanda_client

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/account")
async def get_account():
    """
    Get account information
    
    Returns:
        Account summary with balance, equity, margin, P&L
    """
    try:
        account = await oanda_client.get_account()
        
        # Add calculated fields if missing
        if "status" not in account:
            account["status"] = "ok"
        
        if "timestamp" not in account:
            from datetime import datetime
            account["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        return account
    
    except Exception as e:
        logger.error(f"Account request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Account request failed: {str(e)}")
