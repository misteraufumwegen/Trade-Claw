"""
Hyperliquid Broker Adapter
Real DEX/Perpetuals trading with EIP-712 signing.

Supports:
- Spot trading (BTC, ETH, SOL)
- Futures markets
- WebSocket live updates
- Position tracking and cancellation

Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/trading
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from eth_account.messages import encode_structured_data
from eth_account import Account
from web3 import Web3

from .broker_interface import (
    BrokerAdapter,
    Quote,
    Order,
    Position,
    OrderStatus,
    OrderDirection,
    OrderType,
    AuthenticationError,
    OrderRejectedError,
    InvalidOrderError,
    BrokerError,
)


logger = logging.getLogger('HyperliquidAdapter')


class HyperliquidAdapter(BrokerAdapter):
    """
    Hyperliquid DEX adapter with EIP-712 signing.
    
    Authentication:
    - API Key: Hyperliquid account identifier
    - Secret Key: Ethereum private key (for EIP-712 signing)
    
    Configuration:
    - base_url: API endpoint (default: https://api.hyperliquid.xyz)
    - chain_id: Hyperliquid chain (1 = mainnet, 254 = testnet)
    """
    
    BASE_URL = "https://api.hyperliquid.xyz"
    TESTNET_URL = "https://testnet.api.hyperliquid.xyz"
    
    # Supported assets
    SUPPORTED_ASSETS = {
        'BTC': 'Bitcoin',
        'ETH': 'Ethereum',
        'SOL': 'Solana',
        # Add more as needed
    }
    
    def __init__(self, api_key: str, secret_key: str, **kwargs):
        """
        Initialize Hyperliquid adapter.
        
        Args:
            api_key: Hyperliquid API key (wallet address)
            secret_key: Ethereum private key (0x-prefixed hex)
            **kwargs:
                - testnet: bool (default False)
                - chain_id: int (default 1 for mainnet)
                - leverage: float (default 1.0, max 20x)
        """
        super().__init__(api_key=api_key, secret_key=secret_key, **kwargs)
        
        self.base_url = self.TESTNET_URL if kwargs.get('testnet', False) else self.BASE_URL
        self.chain_id = kwargs.get('chain_id', 254 if kwargs.get('testnet') else 1)
        self.leverage = kwargs.get('leverage', 1.0)
        
        # Validate leverage
        if not (1.0 <= self.leverage <= 20.0):
            raise ValueError("Leverage must be between 1.0 and 20.0")
        
        # Initialize Web3 account for signing.
        # IMPORTANT: do NOT include the raw exception text when rethrowing —
        # it can contain the private key (security review C3/H-logging).
        try:
            # Ensure secret_key is properly formatted
            if not secret_key.startswith('0x'):
                secret_key = '0x' + secret_key

            self.account = Account.from_key(secret_key)
            self.wallet_address = self.account.address
            # Log only the wallet address (public), never the key.
            logger.info("Hyperliquid wallet authenticated: %s", self.wallet_address)
        except Exception:
            # Intentionally swallow original exception message — it may contain
            # the private key passed to eth_account.
            raise AuthenticationError("Invalid Hyperliquid private key")

        # Session and state
        self.session: Optional[aiohttp.ClientSession] = None
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}

        # Monotonic, async-safe nonce. Initialised from the wall clock (ms) so
        # that it stays monotonic across process restarts as long as the clock
        # does not go backwards. See security review C6.
        self._nonce_lock = asyncio.Lock()
        self._nonce = int(time.time() * 1000)

    async def _next_nonce(self) -> int:
        """Return a fresh, strictly-increasing nonce. Concurrency-safe."""
        async with self._nonce_lock:
            now_ms = int(time.time() * 1000)
            # Never go backwards — always +1 over the previous value.
            self._nonce = max(self._nonce + 1, now_ms)
            return self._nonce
    
    async def authenticate(self) -> bool:
        """Verify wallet and API access"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection with user state query
            response = await self.session.post(
                f"{self.base_url}/info",
                json={"type": "user", "user": self.wallet_address},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            
            if response.status != 200:
                raise AuthenticationError(f"Failed to authenticate: {response.status}")
            
            data = await response.json()
            logger.info(f"Authenticated with Hyperliquid: {data}")
            self.is_authenticated = True
            return True
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Hyperliquid auth error: {e}")
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get current market quote"""
        if symbol not in self.SUPPORTED_ASSETS:
            raise InvalidOrderError(f"Unsupported asset: {symbol}")
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            response = await self.session.post(
                f"{self.base_url}/info",
                json={"type": "lastPrice", "coin": symbol},
                timeout=aiohttp.ClientTimeout(total=5),
            )
            
            if response.status != 200:
                raise BrokerError(f"Failed to get quote: {response.status}")
            
            data = await response.json()
            price = float(data.get('price', 0))
            
            # Mock bid/ask spread (0.05%)
            spread = price * 0.0005
            
            return Quote(
                symbol=symbol,
                bid=price - spread,
                ask=price + spread,
                bid_size=1000,  # Mock sizes
                ask_size=1000,
                last_price=price,
                timestamp=datetime.utcnow(),
            )
        
        except asyncio.TimeoutError:
            raise BrokerError(f"Timeout getting quote for {symbol}")
        except Exception as e:
            raise BrokerError(f"Error getting quote: {e}")
    
    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get multiple quotes efficiently"""
        return {symbol: await self.get_quote(symbol) for symbol in symbols}
    
    async def submit_order(self, order: Order) -> str:
        """
        Submit order to Hyperliquid with EIP-712 signing.
        
        Process:
        1. Construct order object
        2. EIP-712 hash and sign
        3. Submit signed order
        """
        
        if order.symbol not in self.SUPPORTED_ASSETS:
            raise InvalidOrderError(f"Unsupported asset: {order.symbol}")
        
        try:
            # Construct Hyperliquid order
            hl_order = {
                "coin": order.symbol,
                "side": "A" if order.direction == OrderDirection.BUY else "B",
                "limitPx": float(order.price) if order.price else 0,
                "sz": float(order.quantity),
                "orderType": self._map_order_type(order.order_type),
                "reduce": False,
                "postOnly": {"isPostOnly": False},
            }
            
            # Sign order with EIP-712
            signature = self._sign_order(hl_order)
            
            # Submit signed order
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Atomically reserve a nonce for this request (C6).
            nonce = await self._next_nonce()

            response = await self.session.post(
                f"{self.base_url}/exchange",
                json={
                    "action": "placeOrder",
                    "nonce": nonce,
                    "order": hl_order,
                    "signature": signature,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
            
            if response.status != 200:
                data = await response.json()
                raise OrderRejectedError(f"Order rejected: {data}")
            
            result = await response.json()
            order_id = result.get('id')
            
            if not order_id:
                raise BrokerError("No order ID returned from Hyperliquid")
            
            # Store order locally
            order.order_id = order_id
            order.broker_order_id = order_id
            order.created_at = datetime.utcnow()
            order.status = OrderStatus.ACCEPTED
            self.orders[order_id] = order
            
            logger.info(f"Order submitted: {order_id} {order.direction.value} {order.quantity} {order.symbol}")
            
            return order_id
        
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            raise
    
    def _sign_order(self, order: Dict[str, Any]) -> str:
        """
        Sign order with EIP-712 (Hyperliquid standard).
        
        Hyperliquid uses typed structured data signing.
        """
        
        # EIP-712 domain
        domain = {
            "name": "Hyperliquid",
            "version": "1",
            "chainId": self.chain_id,
        }
        
        # Message types
        types = {
            "Order": [
                {"name": "coin", "type": "string"},
                {"name": "side", "type": "string"},
                {"name": "limitPx", "type": "uint128"},
                {"name": "sz", "type": "uint128"},
                {"name": "orderType", "type": "string"},
                {"name": "reduce", "type": "bool"},
                {"name": "postOnly", "type": "PostOnly"},
            ],
            "PostOnly": [
                {"name": "isPostOnly", "type": "bool"},
            ],
        }
        
        # Message value
        message = order
        
        # Encode and sign
        structured_data = encode_structured_data({
            "types": types,
            "primaryType": "Order",
            "domain": domain,
            "message": message,
        })
        
        signed_message = self.account.sign_message(structured_data)
        signature = signed_message.signature.hex()
        
        logger.debug(f"Order signed: {signature[:20]}...")
        
        return signature
    
    @staticmethod
    def _map_order_type(order_type: OrderType) -> str:
        """Map OrderType to Hyperliquid order type"""
        mapping = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.STOP: "Stop",
            OrderType.STOP_LIMIT: "StopLimit",
        }
        return mapping.get(order_type, "Market")
    
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status from Hyperliquid"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            response = await self.session.post(
                f"{self.base_url}/info",
                json={"type": "openOrders", "user": self.wallet_address},
                timeout=aiohttp.ClientTimeout(total=5),
            )
            
            if response.status != 200:
                raise BrokerError(f"Failed to fetch orders: {response.status}")
            
            data = await response.json()
            orders = data.get('orders', [])
            
            for hl_order in orders:
                if hl_order.get('id') == order_id:
                    # Map Hyperliquid order to our Order format
                    status_map = {
                        'Open': OrderStatus.ACCEPTED,
                        'Filled': OrderStatus.FILLED,
                        'PartialFilled': OrderStatus.PARTIALLY_FILLED,
                        'Cancelled': OrderStatus.CANCELLED,
                        'Rejected': OrderStatus.REJECTED,
                    }
                    
                    order = self.orders.get(order_id)
                    if order:
                        order.status = status_map.get(hl_order.get('status'), OrderStatus.PENDING)
                        order.filled_quantity = float(hl_order.get('filled', 0))
                        order.average_fill_price = float(hl_order.get('avgFillPrice', 0))
                        
                        if order.status == OrderStatus.FILLED:
                            order.filled_at = datetime.utcnow()
                    
                    return order
            
            # Order not found
            if order_id in self.orders:
                return self.orders[order_id]
            
            raise BrokerError(f"Order {order_id} not found")
        
        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        try:
            order = self.orders.get(order_id)
            if not order:
                return False
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Sign cancellation
            cancel_data = {
                "coin": order.symbol,
                "orderId": order_id,
            }
            
            nonce = await self._next_nonce()
            response = await self.session.post(
                f"{self.base_url}/exchange",
                json={
                    "action": "cancelOrder",
                    "nonce": nonce,
                    "order": cancel_data,
                    "signature": self._sign_order(cancel_data),
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
            
            if response.status == 200:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.utcnow()
                logger.info(f"Order {order_id} cancelled")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            response = await self.session.post(
                f"{self.base_url}/info",
                json={"type": "userState", "user": self.wallet_address},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            
            if response.status != 200:
                raise BrokerError(f"Failed to fetch positions: {response.status}")
            
            data = await response.json()
            positions = []
            
            for pos in data.get('assetPositions', []):
                symbol = pos.get('coin')
                if symbol not in self.SUPPORTED_ASSETS:
                    continue
                
                qty = float(pos.get('szi', 0))
                if qty == 0:
                    continue  # No position
                
                avg_price = float(pos.get('entryPrice', 0))
                current_price = float(pos.get('currentPrice', 0))
                
                pnl = (current_price - avg_price) * qty if avg_price > 0 else 0
                pnl_pct = (pnl / (avg_price * qty)) * 100 if avg_price * qty > 0 else 0
                
                position = Position(
                    symbol=symbol,
                    quantity=qty,
                    average_price=avg_price,
                    current_price=current_price,
                    unrealized_pnl=pnl,
                    unrealized_pnl_percent=pnl_pct,
                    side=OrderDirection.BUY if qty > 0 else OrderDirection.SELL,
                    last_updated=datetime.utcnow(),
                )
                positions.append(position)
            
            self.positions = {p.symbol: p for p in positions}
            return positions
        
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get single position"""
        positions = await self.get_positions()
        return next((p for p in positions if p.symbol == symbol), None)
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance and equity"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            response = await self.session.post(
                f"{self.base_url}/info",
                json={"type": "userState", "user": self.wallet_address},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            
            if response.status != 200:
                raise BrokerError(f"Failed to fetch balance: {response.status}")
            
            data = await response.json()
            
            balance = float(data.get('marginSummary', {}).get('accountValue', 0))
            equity = float(data.get('marginSummary', {}).get('totalNtlPos', 0))
            margin_used = float(data.get('marginSummary', {}).get('totalMarginUsed', 0))
            
            return {
                'balance': balance,
                'equity': equity,
                'margin_available': balance - margin_used,
                'margin_used': margin_used,
            }
        
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
    async def stream_prices(self, symbols: List[str], callback) -> None:
        """
        Stream live prices via Hyperliquid WebSocket.
        """
        import websockets
        
        ws_url = "wss://api.hyperliquid.xyz/ws"
        
        try:
            async with websockets.connect(ws_url) as ws:
                # Subscribe to symbols
                for symbol in symbols:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {
                            "type": "l2Book",
                            "coin": symbol,
                        }
                    }))
                
                logger.info(f"Subscribed to prices for {symbols}")
                
                # Listen for updates
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    if data.get('channel') == 'l2Book':
                        symbol = data['data']['coin']
                        bid = float(data['data']['bids'][0][0]) if data['data'].get('bids') else 0
                        ask = float(data['data']['asks'][0][0]) if data['data'].get('asks') else 0
                        
                        quote = Quote(
                            symbol=symbol,
                            bid=bid,
                            ask=ask,
                            bid_size=float(data['data']['bids'][0][1]) if data['data'].get('bids') else 0,
                            ask_size=float(data['data']['asks'][0][1]) if data['data'].get('asks') else 0,
                            last_price=(bid + ask) / 2 if bid and ask else 0,
                            timestamp=datetime.utcnow(),
                        )
                        
                        await callback(symbol, quote)
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close session and cleanup"""
        if self.session:
            await self.session.close()
        logger.info("Hyperliquid adapter disconnected")
