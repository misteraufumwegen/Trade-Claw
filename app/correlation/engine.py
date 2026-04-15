"""
Correlation Engine - Flexible multi-asset correlation analyzer
Computes correlations between arbitrary assets and scores trade eligibility
"""

import logging
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CorrelationEngine:
    """Flexible correlation analyzer for multi-asset portfolios"""
    
    def __init__(self, lookback_days: int = 30):
        """
        Initialize Correlation Engine
        
        Args:
            lookback_days: Default lookback period for correlation calculation
        """
        self.lookback_days = lookback_days
        self.correlation_cache: Dict[Tuple, float] = {}
    
    def analyze(
        self,
        asset_prices: Dict[str, List[float]],
        threshold: float = 0.7,
    ) -> Dict:
        """
        Analyze correlation between assets
        
        Args:
            asset_prices: Dict of {asset: [prices]} (time-aligned)
            threshold: Correlation threshold for trade eligibility (0-1)
        
        Returns:
            Dict with correlation matrix, scores, and trade eligibility
        """
        if not asset_prices or len(asset_prices) < 2:
            return {
                "error": "Need at least 2 assets",
                "trade_eligible": False
            }
        
        assets = list(asset_prices.keys())
        n = len(assets)
        
        # Build correlation matrix
        correlation_matrix = {}
        correlations = []
        
        for i in range(n):
            for j in range(i + 1, n):
                asset_a = assets[i]
                asset_b = assets[j]
                
                # Calculate correlation
                prices_a = np.array(asset_prices[asset_a])
                prices_b = np.array(asset_prices[asset_b])
                
                if len(prices_a) != len(prices_b):
                    logger.warning(f"Price length mismatch: {asset_a} vs {asset_b}")
                    correlation = 0.0
                else:
                    # Compute Pearson correlation
                    correlation = float(np.corrcoef(prices_a, prices_b)[0, 1])
                    if np.isnan(correlation):
                        correlation = 0.0
                
                key = f"{asset_a}_vs_{asset_b}"
                correlation_matrix[key] = round(correlation, 4)
                correlations.append(correlation)
        
        # Score correlations
        high_corr = sum(1 for c in correlations if c > threshold)
        low_corr = sum(1 for c in correlations if c < -threshold)
        
        avg_correlation = float(np.mean(correlations)) if correlations else 0.0
        
        # Trade eligibility: avg correlation > threshold
        trade_eligible = avg_correlation > threshold
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": assets,
            "correlation_matrix": correlation_matrix,
            "avg_correlation": round(avg_correlation, 4),
            "high_correlation_pairs": high_corr,
            "low_correlation_pairs": low_corr,
            "threshold": threshold,
            "trade_eligible": trade_eligible,
            "reasoning": self._generate_reasoning(
                avg_correlation, threshold, high_corr, low_corr
            )
        }
    
    def _generate_reasoning(
        self,
        avg_corr: float,
        threshold: float,
        high_pairs: int,
        low_pairs: int
    ) -> str:
        """Generate human-readable reasoning for correlation score"""
        if avg_corr > threshold:
            return f"Assets are aligned (avg {avg_corr:.2f} > {threshold}). Trade eligible."
        elif avg_corr > threshold - 0.2:
            return f"Assets moderately aligned (avg {avg_corr:.2f}). Caution advised."
        else:
            return f"Assets diverging (avg {avg_corr:.2f} < {threshold}). Skip trade."
    
    def score_trade_correlation(self, correlations: List[float]) -> Dict:
        """
        Score a specific trade based on asset correlations
        
        Args:
            correlations: List of correlation values for trade assets
        
        Returns:
            Dict with score (0-100) and recommendation
        """
        if not correlations:
            return {"score": 0, "recommendation": "SKIP", "reason": "No correlations"}
        
        avg = np.mean(correlations)
        
        # Score: (correlation + 1) / 2 * 100 (maps -1..1 to 0..100)
        score = round(((avg + 1) / 2) * 100, 1)
        
        if score >= 70:
            recommendation = "STRONG_BUY"
        elif score >= 50:
            recommendation = "BUY"
        elif score >= 30:
            recommendation = "NEUTRAL"
        else:
            recommendation = "SKIP"
        
        return {
            "score": score,
            "avg_correlation": round(avg, 4),
            "recommendation": recommendation,
        }
