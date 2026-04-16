"""
Asset Manager - Predefined and custom asset definitions
Manages asset metadata, data sources, and validation
"""

import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class AssetType(StrEnum):
    """Asset classification"""

    COMMODITY = "commodity"  # Gold, Silver, Oil, etc.
    FOREX = "forex"  # EUR/USD, GBP/USD, etc.
    CRYPTO = "crypto"  # BTC, ETH, etc.
    STOCK = "stock"  # SPY, QQQ, etc.
    INDEX = "index"  # Market indices


class Asset:
    """Asset definition"""

    def __init__(
        self,
        symbol: str,
        name: str,
        asset_type: AssetType,
        source: str = "yfinance",
        description: str = "",
    ):
        self.symbol = symbol
        self.name = name
        self.asset_type = asset_type
        self.source = source
        self.description = description

    def __repr__(self) -> str:
        return f"Asset({self.symbol}, {self.asset_type.value})"


class AssetManager:
    """Manages available and custom assets"""

    # Predefined assets
    PREDEFINED_ASSETS = {
        # Commodities
        "GLD": Asset("GLD", "Gold ETF", AssetType.COMMODITY, description="SPDR Gold Shares"),
        "SLV": Asset("SLV", "Silver ETF", AssetType.COMMODITY, description="iShares Silver Trust"),
        "USO": Asset("USO", "Oil ETF", AssetType.COMMODITY, description="US Oil Fund"),
        # Forex (as indices)
        "EUR/USD": Asset("EURUSD=X", "Euro/USD", AssetType.FOREX, description="EUR to USD"),
        "GBP/USD": Asset("GBPUSD=X", "Pound/USD", AssetType.FOREX, description="GBP to USD"),
        "USD/JPY": Asset("USDJPY=X", "USD/Yen", AssetType.FOREX, description="USD to JPY"),
        "AUD/USD": Asset("AUDUSD=X", "Aussie/USD", AssetType.FOREX, description="AUD to USD"),
        # Crypto
        "BTC": Asset("BTC-USD", "Bitcoin", AssetType.CRYPTO, description="Bitcoin in USD"),
        "ETH": Asset("ETH-USD", "Ethereum", AssetType.CRYPTO, description="Ethereum in USD"),
        "XRP": Asset("XRP-USD", "Ripple", AssetType.CRYPTO, description="XRP in USD"),
        # Stocks / Indices
        "SPY": Asset("SPY", "S&P 500", AssetType.STOCK, description="SPDR S&P 500 ETF"),
        "QQQ": Asset("QQQ", "Nasdaq 100", AssetType.STOCK, description="Invesco QQQ ETF"),
        "IWM": Asset("IWM", "Russell 2000", AssetType.STOCK, description="iShares Russell 2000"),
        "VIX": Asset("^VIX", "Volatility Index", AssetType.INDEX, description="S&P 500 Volatility"),
    }

    def __init__(self):
        """Initialize Asset Manager"""
        self.custom_assets: dict[str, Asset] = {}

    def get_asset(self, symbol: str) -> Asset | None:
        """
        Get asset by symbol

        Args:
            symbol: Asset symbol (e.g., "GLD", "EUR/USD", "BTC")

        Returns:
            Asset object or None if not found
        """
        # Check predefined first
        if symbol in self.PREDEFINED_ASSETS:
            return self.PREDEFINED_ASSETS[symbol]

        # Check custom
        if symbol in self.custom_assets:
            return self.custom_assets[symbol]

        return None

    def list_assets(self) -> dict[str, Asset]:
        """List all available assets"""
        return {**self.PREDEFINED_ASSETS, **self.custom_assets}

    def list_by_type(self, asset_type: AssetType) -> list[Asset]:
        """List assets by type"""
        all_assets = self.list_assets()
        return [a for a in all_assets.values() if a.asset_type == asset_type]

    def add_custom_asset(self, asset: Asset) -> bool:
        """
        Add custom asset

        Args:
            asset: Asset object

        Returns:
            True if added, False if already exists
        """
        if asset.symbol in self.PREDEFINED_ASSETS or asset.symbol in self.custom_assets:
            logger.warning(f"Asset {asset.symbol} already exists")
            return False

        self.custom_assets[asset.symbol] = asset
        logger.info(f"Added custom asset: {asset.symbol}")
        return True

    def validate_assets(self, symbols: list[str]) -> tuple[bool, str]:
        """
        Validate asset list

        Args:
            symbols: List of asset symbols

        Returns:
            (is_valid, error_message)
        """
        if not symbols:
            return False, "Asset list is empty"

        if len(symbols) < 2:
            return False, "Need at least 2 assets for correlation"

        if len(symbols) > 10:
            return False, "Maximum 10 assets per correlation analysis"

        missing = []
        for symbol in symbols:
            if not self.get_asset(symbol):
                missing.append(symbol)

        if missing:
            return False, f"Unknown assets: {', '.join(missing)}"

        # Check for duplicates
        if len(symbols) != len(set(symbols)):
            return False, "Duplicate assets in list"

        return True, ""
