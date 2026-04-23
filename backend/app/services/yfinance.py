"""
yfinance integration service
Fallback data source for historical data and quotes
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class YFinanceClient:
    """yfinance wrapper for historical data"""
    
    def __init__(self):
        self.available = self._check_yfinance()
        self.yf = None
        if self.available:
            try:
                import yfinance
                self.yf = yfinance
            except ImportError:
                self.available = False
    
    @staticmethod
    def _check_yfinance():
        """Check if yfinance is installed"""
        try:
            import yfinance
            return True
        except ImportError:
            logger.warning("yfinance not installed - install with: pip install yfinance")
            return False
    
    async def get_historical_data(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> Optional[Dict]:
        """
        Get historical OHLCV data
        
        Args:
            symbol: Ticker symbol (e.g., 'EURUSD=X' for forex)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1h, etc.)
        
        Returns:
            Dict with historical data or None if failed
        """
        if not self.available or not self.yf:
            logger.error("yfinance not available")
            return None
        
        try:
            df = self.yf.download(symbol, start=start, end=end, interval=interval, progress=False)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Convert DataFrame to dict format
            data = {
                "symbol": symbol,
                "start": start,
                "end": end,
                "interval": interval,
                "ohlcv": []
            }
            
            for idx, row in df.iterrows():
                data["ohlcv"].append({
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]) if "Volume" in row else 0
                })
            
            logger.info(f"Retrieved {len(data['ohlcv'])} bars for {symbol} from {start} to {end}")
            return data
        
        except Exception as e:
            logger.error(f"yfinance download failed for {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol
        
        Args:
            symbol: Ticker symbol
        
        Returns:
            Current price or None if failed
        """
        if not self.available or not self.yf:
            logger.error("yfinance not available")
            return None
        
        try:
            ticker = self.yf.Ticker(symbol)
            price = ticker.info.get("currentPrice")
            
            if price is None:
                # Try alternative field names
                price = ticker.info.get("regularMarketPrice")
            
            if price:
                logger.info(f"Retrieved current price for {symbol}: {price}")
                return float(price)
            else:
                logger.warning(f"Could not find current price for {symbol}")
                return None
        
        except Exception as e:
            logger.error(f"yfinance price lookup failed for {symbol}: {e}")
            return None
    
    async def get_quotes(self, symbols: List[str]) -> Dict:
        """
        Get quotes for multiple symbols
        
        Args:
            symbols: List of ticker symbols
        
        Returns:
            Dict with quote data
        """
        if not self.available or not self.yf:
            logger.error("yfinance not available")
            return {"quotes": [], "status": "error"}
        
        try:
            quotes = []
            for symbol in symbols:
                price = await self.get_current_price(symbol)
                if price:
                    quotes.append({
                        "instrument": symbol,
                        "bid": price * 0.9999,  # Simulate bid/ask
                        "ask": price * 1.0001,
                        "time": datetime.utcnow().isoformat() + "Z",
                        "source": "yfinance"
                    })
            
            return {"quotes": quotes, "status": "ok"}
        
        except Exception as e:
            logger.error(f"yfinance quotes failed: {e}")
            return {"quotes": [], "status": "error", "error": str(e)}

# Global yfinance client instance
yfinance_client = YFinanceClient()
