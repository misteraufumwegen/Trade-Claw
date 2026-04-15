"""Alpaca stock broker adapter."""

from decimal import Decimal
from typing import Optional, List, Dict, Any

from .broker_interface import BrokerAdapter, Order, Position, Quote


class AlpacaAdapter(BrokerAdapter):
    """
    Adapter for Alpaca Securities (stocks and options).
    
    Status: Implementation ready (PHASE 4 stub)
    Full implementation can be completed in PHASE 5 if Alpaca trading is required.
    """

    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize Alpaca adapter.
        
        Required credentials:
        - api_key: Alpaca API key
        - secret_key: Alpaca secret key
        - base_url: https://api.alpaca.markets or paper trading
        """
        self.api_key = credentials.get("api_key")
        self.secret_key = credentials.get("secret_key")
        self.base_url = credentials.get("base_url", "https://paper-api.alpaca.markets")
        self.session = None
        self._authenticated = False

    async def authenticate(self) -> bool:
        """
        Authenticate with Alpaca API.
        
        Returns:
            True if authentication successful
        """
        try:
            # TODO: Implement Alpaca authentication
            # import alpaca_trade_api as tradeapi
            # self.api = tradeapi.REST(self.api_key, self.secret_key, self.base_url)
            # Test connection
            # account = self.api.get_account()
            # if account:
            #     self._authenticated = True
            #     return True
            # For now, stub returns True
            self._authenticated = True
            return True
        except Exception:
            self._authenticated = False
            return False

    async def get_quote(self, symbol: str, amount: Decimal = None) -> Quote:
        """
        Get current price quote for symbol.
        
        Args:
            symbol: Stock symbol (e.g., AAPL)
            amount: Optional amount for fee calculation
            
        Returns:
            Quote with bid/ask prices
        """
        # TODO: Implement via Alpaca API
        # Use polygon.io for real-time quotes via Alpaca
        raise NotImplementedError("Alpaca quote implementation pending")

    async def submit_order(
        self,
        symbol: str,
        side: str,
        size: Decimal,
        entry: Decimal,
        sl: Decimal,
        tp: Decimal,
    ) -> Order:
        """
        Submit market/limit order with stop loss and take profit.
        
        Note: Alpaca requires separate orders for SL/TP via trailing stops or OCO.
        
        Args:
            symbol: Stock symbol
            side: BUY or SELL
            size: Number of shares
            entry: Limit price (use 0 for market)
            sl: Stop loss price
            tp: Take profit price
            
        Returns:
            Order with order_id and status
        """
        # TODO: Implement order submission
        # self.api.submit_order(
        #     symbol=symbol,
        #     qty=size,
        #     side=side.lower(),
        #     type='limit',
        #     limit_price=entry,
        #     stop_loss=sl,
        #     take_profit=tp,
        # )
        raise NotImplementedError("Alpaca order submission pending")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel open order."""
        # TODO: Implement via self.api.cancel_order(order_id)
        raise NotImplementedError("Alpaca cancel pending")

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        # TODO: Implement via self.api.list_positions()
        raise NotImplementedError("Alpaca positions pending")

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account balance and info."""
        # TODO: Implement via self.api.get_account()
        raise NotImplementedError("Alpaca account info pending")

    async def close(self) -> None:
        """Close broker connection."""
        if self.session:
            await self.session.close()
        self._authenticated = False
