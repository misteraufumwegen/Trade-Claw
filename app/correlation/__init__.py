"""
Correlation Engine - Asset Correlation Analysis
Flexible, multi-asset correlation scoring for trading decisions
"""

from .assets import AssetManager
from .engine import CorrelationEngine
from .schemas import CorrelationRequest, CorrelationResponse

__all__ = [
    "CorrelationEngine",
    "AssetManager",
    "CorrelationRequest",
    "CorrelationResponse",
]
