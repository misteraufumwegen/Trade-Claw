"""
Orders API endpoints
POST /orders - Place order
GET /orders - List orders
POST /orders/{id}/cancel - Cancel order
"""
import logging
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.services.oanda import oanda_client

logger = logging.getLogger(__name__)

router = APIRouter()

class OrderRequest(BaseModel):
    """Order request schema"""
    instrument: str
    units: int
    order_type: str = "MARKET"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@router.post("/orders")
async def place_order(order: OrderRequest):
    """
    Place a new order
    
    Args:
        order: Order details (instrument, units, type, etc.)
    
    Returns:
        Order confirmation with order ID and status
    """
    try:
        # Validate inputs
        if order.units == 0:
            raise HTTPException(status_code=400, detail="Units cannot be zero")
        
        if order.order_type not in ["MARKET", "LIMIT", "STOP"]:
            raise HTTPException(status_code=400, detail="Invalid order type")
        
        if order.order_type == "LIMIT" and not order.price:
            raise HTTPException(status_code=400, detail="LIMIT orders require a price")
        
        # Place order via OANDA
        order_data = {
            "instrument": order.instrument,
            "units": order.units,
            "order_type": order.order_type,
            "price": order.price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit
        }
        
        result = await oanda_client.place_order(order_data)
        
        if result.get("status") == "FAILED":
            logger.error(f"Order placement failed: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error", "Order placement failed"))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order placement error: {e}")
        raise HTTPException(status_code=500, detail=f"Order placement error: {str(e)}")

@router.get("/orders")
async def get_orders(
    status: Optional[str] = None,
    instrument: Optional[str] = None
):
    """
    List all orders with optional filtering
    
    Args:
        status: Filter by status (PENDING, FILLED, CANCELLED)
        instrument: Filter by instrument
    
    Returns:
        List of orders
    """
    try:
        result = await oanda_client.get_orders()
        
        if result.get("status") != "ok":
            logger.error("Failed to retrieve orders")
            raise HTTPException(status_code=502, detail="Failed to retrieve orders")
        
        orders = result.get("orders", [])
        
        # Apply filters
        if status:
            orders = [o for o in orders if o.get("status") == status]
        
        if instrument:
            orders = [o for o in orders if o.get("instrument") == instrument]
        
        return {
            "orders": orders,
            "count": len(orders),
            "status": "ok"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Orders request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Orders request failed: {str(e)}")

@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str = Path(..., description="Order ID to cancel")):
    """
    Cancel an open order
    
    Args:
        order_id: ID of order to cancel
    
    Returns:
        Cancellation confirmation
    """
    try:
        if not order_id:
            raise HTTPException(status_code=400, detail="Order ID is required")
        
        result = await oanda_client.cancel_order(order_id)
        
        if result.get("status") == "FAILED":
            logger.error(f"Cancel failed for order {order_id}: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error", "Cancel failed"))
        
        return {
            "order_id": order_id,
            "status": "CANCELLED",
            "cancelled_at": datetime.utcnow().isoformat() + "Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel order error: {e}")
        raise HTTPException(status_code=500, detail=f"Cancel order error: {str(e)}")
