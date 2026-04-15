"""
Correlation Engine - Asset Correlation Analysis
Flexible, multi-asset correlation scoring for trading decisions
"""

from .engine import CorrelationEngine
from .assets import AssetManager
from .schemas import CorrelationRequest, CorrelationResponse

__all__ = [
    "CorrelationEngine",
    "AssetManager", 
    "CorrelationRequest",
    "CorrelationResponse",
]
