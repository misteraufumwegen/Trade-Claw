"""
Correlation Request/Response Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CorrelationRequest(BaseModel):
    """Request to analyze correlation between assets"""

    assets: list[str] = Field(
        ...,
        description="List of asset symbols (e.g., ['GLD', 'SLV', 'EUR/USD'])",
        min_length=2,
        max_length=10,
    )
    threshold: float = Field(
        default=0.7,
        description="Correlation threshold (0-1). Values above = aligned.",
        ge=0.0,
        le=1.0,
    )
    lookback_days: int = Field(
        default=30, description="Days of historical data for correlation calculation", ge=5, le=365
    )


class CorrelationMatrix(BaseModel):
    """Correlation values between all asset pairs"""

    pairs: dict[str, float] = Field(
        ..., description="Correlation scores (format: 'ASSET1_vs_ASSET2': 0.85)"
    )
    avg_correlation: float = Field(..., description="Average correlation across all pairs")
    high_correlation_pairs: int = Field(..., description="Number of asset pairs above threshold")
    low_correlation_pairs: int = Field(
        ..., description="Number of asset pairs below negative threshold"
    )


class CorrelationResponse(BaseModel):
    """Response with correlation analysis results"""

    timestamp: datetime = Field(..., description="Analysis timestamp")
    assets: list[str] = Field(..., description="Analyzed assets")
    correlation_matrix: dict[str, float] = Field(..., description="All pairwise correlations")
    avg_correlation: float = Field(..., description="Average correlation")
    threshold: float = Field(..., description="Applied threshold")
    trade_eligible: bool = Field(..., description="Is trade eligible based on correlation?")
    reasoning: str = Field(..., description="Human-readable explanation")


class TradeCorrelationScore(BaseModel):
    """Score for a specific trade based on correlations"""

    score: float = Field(..., description="Correlation score (0-100)", ge=0.0, le=100.0)
    avg_correlation: float = Field(..., description="Average correlation")
    recommendation: str = Field(
        ..., description="Trade recommendation (STRONG_BUY, BUY, NEUTRAL, SKIP)"
    )


class AvailableAssetsResponse(BaseModel):
    """List of available assets"""

    assets: dict[str, str] = Field(..., description="Symbol -> Name mapping")
    count: int = Field(..., description="Total number of assets")
    categories: dict[str, int] = Field(
        ..., description="Asset count by type (commodity, forex, crypto, stock, index)"
    )
