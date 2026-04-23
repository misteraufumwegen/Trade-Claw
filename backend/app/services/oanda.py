"""
OANDA API integration service
Handles real-time quotes, order execution, account management
"""
import logging
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class OANDAClient:
    """OANDA v20 API client wrapper"""
    
    def __init__(self):
        self.api_key = settings.OANDA_API_KEY
        self.account_id = settings.OANDA_ACCOUNT_ID
        self.environment = settings.OANDA_ENV
        self.base_url = f"https://api-{self.environment}.oanda.com/v3"
        self.is_configured = bool(self.api_key and self.account_id)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if not self.is_configured:
            logger.warning("OANDA client not configured (missing API_KEY or ACCOUNT_ID) - using mock data")
    
    async def get_quotes(self, instruments: List[str]):
        """
        Get real-time quotes for instruments
        
        Args:
            instruments: List of instrument codes (e.g., ['EUR_USD', 'GBP_USD'])
        
        Returns:
            Dict with quote data
        """
        if not self.is_configured:
            logger.debug("OANDA not configured - returning mock quotes")
            return self._mock_quotes(instruments)
        
        try:
            async with httpx.AsyncClient() as client:
                params = {"instruments": ",".join(instruments)}
                response = await client.get(
                    f"{self.base_url}/accounts/{self.account_id}/pricing",
                    headers=self.headers,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                quotes = []
                for price in data.get("prices", []):
                    quotes.append({
                        "instrument": price["instrument"],
                        "bid": float(price["bids"][0]["price"]),
                        "ask": float(price["asks"][0]["price"]),
                        "time": price["time"],
                        "source": "oanda"
                    })
                
                logger.info(f"Retrieved {len(quotes)} quotes from OANDA")
                return {"quotes": quotes, "status": "ok"}
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OANDA API error ({e.response.status_code}): {e.response.text}")
            return self._mock_quotes(instruments)
        except Exception as e:
            logger.error(f"OANDA quote request failed: {e}")
            return self._mock_quotes(instruments)
    
    async def get_positions(self):
        """Get all active positions"""
        if not self.is_configured:
            logger.debug("OANDA not configured - returning mock positions")
            return self._mock_positions()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/accounts/{self.account_id}/positions",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                positions = []
                for pos in data.get("positions", []):
                    if pos.get("long", {}).get("units", 0) != 0 or pos.get("short", {}).get("units", 0) != 0:
                        units = int(pos["long"]["units"]) if pos["long"]["units"] else int(pos["short"]["units"])
                        positions.append({
                            "instrument": pos["instrument"],
                            "units": units,
                            "entry_price": float(pos["long"]["averagePrice"]) if pos["long"]["averagePrice"] else float(pos["short"]["averagePrice"]),
                            "current_price": 0.0,
                            "unrealized_pnl": float(pos["long"]["unrealizedPL"]) if pos["long"]["unrealizedPL"] else float(pos["short"]["unrealizedPL"]),
                            "percentage_return": 0.0,
                            "pip_value": 10.0
                        })
                
                logger.info(f"Retrieved {len(positions)} positions from OANDA")
                return {"positions": positions, "status": "ok"}
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OANDA API error ({e.response.status_code}): {e.response.text}")
            return self._mock_positions()
        except Exception as e:
            logger.error(f"OANDA positions request failed: {e}")
            return self._mock_positions()
    
    async def get_orders(self):
        """Get all open orders"""
        if not self.is_configured:
            logger.debug("OANDA not configured - returning mock orders")
            return self._mock_orders()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/accounts/{self.account_id}/orders",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                orders = []
                for order in data.get("orders", []):
                    orders.append({
                        "order_id": order["id"],
                        "instrument": order.get("instrument", ""),
                        "units": int(order.get("units", 0)),
                        "order_type": order["type"],
                        "status": order["state"],
                        "price": float(order.get("priceBound", 0)) if order.get("priceBound") else None,
                        "created_at": order["createTime"]
                    })
                
                logger.info(f"Retrieved {len(orders)} orders from OANDA")
                return {"orders": orders, "status": "ok"}
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OANDA API error ({e.response.status_code}): {e.response.text}")
            return self._mock_orders()
        except Exception as e:
            logger.error(f"OANDA orders request failed: {e}")
            return self._mock_orders()
    
    async def place_order(self, order_data: Dict):
        """Place a new order"""
        if not self.is_configured:
            logger.debug("OANDA not configured - returning mock order")
            return {
                "order_id": "MOCK_" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "instrument": order_data.get("instrument"),
                "units": order_data.get("units"),
                "status": "PENDING"
            }
        
        try:
            oanda_order = {
                "order": {
                    "units": order_data["units"],
                    "instrument": order_data["instrument"],
                    "type": order_data.get("order_type", "MARKET")
                }
            }
            
            if order_data.get("order_type") == "LIMIT" and order_data.get("price"):
                oanda_order["order"]["priceBound"] = order_data["price"]
            
            if order_data.get("stop_loss"):
                oanda_order["order"]["stopLossOnFill"] = {
                    "price": order_data["stop_loss"]
                }
            
            if order_data.get("take_profit"):
                oanda_order["order"]["takeProfitOnFill"] = {
                    "price": order_data["take_profit"]
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/accounts/{self.account_id}/orders",
                    headers=self.headers,
                    json=oanda_order,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Order placed successfully: {data['orderFillTransaction']['id']}")
                return {
                    "order_id": data["orderFillTransaction"]["id"],
                    "instrument": order_data["instrument"],
                    "units": order_data["units"],
                    "status": "FILLED"
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OANDA order placement failed ({e.response.status_code}): {e.response.text}")
            return {
                "order_id": None,
                "error": f"Order placement failed: {e.response.text}",
                "status": "FAILED"
            }
        except Exception as e:
            logger.error(f"OANDA order placement error: {e}")
            return {
                "order_id": None,
                "error": str(e),
                "status": "FAILED"
            }
    
    async def cancel_order(self, order_id: str):
        """Cancel an open order"""
        if not self.is_configured:
            return {"order_id": order_id, "status": "CANCELLED"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/accounts/{self.account_id}/orders/{order_id}/cancel",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                
                logger.info(f"Order cancelled: {order_id}")
                return {
                    "order_id": order_id,
                    "status": "CANCELLED"
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OANDA cancel failed ({e.response.status_code}): {e.response.text}")
            return {
                "order_id": order_id,
                "error": f"Cancellation failed: {e.response.text}",
                "status": "FAILED"
            }
        except Exception as e:
            logger.error(f"OANDA cancel error: {e}")
            return {
                "order_id": order_id,
                "error": str(e),
                "status": "FAILED"
            }
    
    async def get_account(self):
        """Get account information"""
        if not self.is_configured:
            logger.debug("OANDA not configured - returning mock account")
            return self._mock_account()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/accounts/{self.account_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()["account"]
                
                account_info = {
                    "account_id": data["id"],
                    "balance": float(data["balance"]),
                    "equity": float(data["equity"]),
                    "margin_used": float(data["marginUsed"]),
                    "margin_available": float(data["marginAvailable"]),
                    "margin_rate": float(data["marginRate"]),
                    "unrealized_pnl": float(data["unrealizedPL"]),
                    "realized_pnl": 0.0,
                    "total_pnl": float(data["unrealizedPL"]),
                    "currency": data["currency"],
                    "timestamp": data["lastTransactionID"]
                }
                
                logger.info(f"Retrieved account info: balance={account_info['balance']}")
                return account_info
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OANDA account request failed ({e.response.status_code}): {e.response.text}")
            return self._mock_account()
        except Exception as e:
            logger.error(f"OANDA account request failed: {e}")
            return self._mock_account()
    
    @staticmethod
    def _mock_quotes(instruments: List[str]):
        """Mock quote data for testing"""
        mock_prices = {
            "EUR_USD": (1.0850, 1.0851),
            "GBP_USD": (1.2750, 1.2751),
            "USD_JPY": (150.50, 150.51),
            "AUD_USD": (0.6850, 0.6851),
            "USD_CAD": (1.3650, 1.3651),
        }
        
        quotes = []
        for inst in instruments:
            if inst in mock_prices:
                bid, ask = mock_prices[inst]
            else:
                bid, ask = 1.0, 1.001
            
            quotes.append({
                "instrument": inst,
                "bid": bid,
                "ask": ask,
                "time": datetime.utcnow().isoformat() + "Z",
                "source": "mock"
            })
        
        return {"quotes": quotes, "status": "ok"}
    
    @staticmethod
    def _mock_positions():
        """Mock position data"""
        return {
            "positions": [
                {
                    "instrument": "EUR_USD",
                    "units": 100000,
                    "entry_price": 1.0800,
                    "current_price": 1.0850,
                    "unrealized_pnl": 500.0,
                    "percentage_return": 0.46,
                    "pip_value": 10.0
                }
            ],
            "status": "ok"
        }
    
    @staticmethod
    def _mock_orders():
        """Mock order data"""
        return {
            "orders": [
                {
                    "order_id": "MOCK_001",
                    "instrument": "EUR_USD",
                    "units": 100000,
                    "order_type": "MARKET",
                    "status": "PENDING",
                    "price": None,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }
            ],
            "status": "ok"
        }
    
    @staticmethod
    def _mock_account():
        """Mock account data"""
        return {
            "account_id": "001-001-1234567-001",
            "balance": 100000.0,
            "equity": 100500.0,
            "margin_used": 10000.0,
            "margin_available": 90000.0,
            "margin_rate": 0.05,
            "unrealized_pnl": 500.0,
            "realized_pnl": 0.0,
            "total_pnl": 500.0,
            "currency": "USD",
            "timestamp": "12345"
        }

# Global OANDA client instance
oanda_client = OANDAClient()
