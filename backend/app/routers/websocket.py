"""
WebSocket router for live quote streaming
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.oanda import OANDAClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, instrument: str):
        await websocket.accept()
        if instrument not in self.active_connections:
            self.active_connections[instrument] = []
        self.active_connections[instrument].append(websocket)
        logger.info(f"WebSocket connected for {instrument}")

    def disconnect(self, websocket: WebSocket, instrument: str):
        if instrument in self.active_connections:
            self.active_connections[instrument].remove(websocket)
            if not self.active_connections[instrument]:
                del self.active_connections[instrument]
        logger.info(f"WebSocket disconnected for {instrument}")

    async def broadcast(self, instrument: str, message: dict):
        if instrument in self.active_connections:
            disconnected = []
            for connection in self.active_connections[instrument]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for connection in disconnected:
                self.disconnect(connection, instrument)

manager = ConnectionManager()

@router.websocket("/ws/quotes")
async def websocket_quotes(websocket: WebSocket):
    """WebSocket endpoint for live quote streaming"""
    instrument = None
    try:
        # Accept the connection
        initial_message = await websocket.receive_json()
        action = initial_message.get("action")
        instrument = initial_message.get("instrument")

        if action == "subscribe" and instrument:
            await manager.connect(websocket, instrument)
            
            # Send confirmation
            await websocket.send_json({
                "type": "subscription",
                "status": "connected",
                "instrument": instrument
            })

            # For now, send mock quote updates
            # In production, this would stream real data from OANDA
            mock_quotes = {
                "EUR_USD": {"bid": 1.0850, "ask": 1.0852, "change_percent": 0.15},
                "GBP_USD": {"bid": 1.2650, "ask": 1.2652, "change_percent": -0.10},
                "SPY": {"bid": 445.20, "ask": 445.22, "change_percent": 0.25},
            }

            while True:
                try:
                    # Listen for client messages (subscribe/unsubscribe)
                    message = await websocket.receive_json()
                    action = message.get("action")
                    new_instrument = message.get("instrument")

                    if action == "unsubscribe":
                        manager.disconnect(websocket, instrument)
                        instrument = None
                        await websocket.send_json({
                            "type": "subscription",
                            "status": "disconnected",
                            "instrument": new_instrument
                        })
                        break
                    elif action == "subscribe" and new_instrument:
                        if instrument:
                            manager.disconnect(websocket, instrument)
                        instrument = new_instrument
                        await manager.connect(websocket, instrument)
                        await websocket.send_json({
                            "type": "subscription",
                            "status": "connected",
                            "instrument": instrument
                        })
                except Exception as e:
                    logger.error(f"Error in WebSocket communication: {e}")
                    break

    except WebSocketDisconnect:
        if instrument:
            manager.disconnect(websocket, instrument)
            logger.info(f"Client disconnected from {instrument}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if instrument:
            manager.disconnect(websocket, instrument)
