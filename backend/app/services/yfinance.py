"""
yfinance integration service
Fallback data source for historical data and quotes
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class YFinanceClient:
    """yfinance wrapper for historical data"""
    
    def __init__(self):
        self.available = self._check_yfinance()
    
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
        start: str,  # YYYY-MM-DD
        end: str,
        interval: str = "1d"  # 1d, 1h, etc.
    ):
        """
        Get historical OHLCV data
        
        Args:
            symbol: Ticker symbol (e.g., 'EURUSD=X' for forex)
            start: Start date
            end: End date
            interval: Data interval
        
        Returns:
            Dataframe with OHLCV data
        """
        if not self.available:
            logger.error("yfinance not available")
            return None
        
        try:
            import yfinance as yf
            df = yf.download(symbol, start=start, end=end, interval=interval)
            return df
        except Exception as e:
            logger.error(f"yfinance download failed: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        if not self.available:
            return None
        
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            price = ticker.info.get("currentPrice")
            return price
        except Exception as e:
            logger.error(f"yfinance price lookup failed: {e}")
            return None

# Global yfinance client instance
yfinance_client = YFinanceClient()
