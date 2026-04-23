#!/usr/bin/env python
"""
Prepare training data from backtest results.

This script converts raw backtest trade data into a SQLite database
with all 25 features normalized and ready for NN training.

Usage:
    python scripts/prepare_training_data.py \\
        --source backtest_trades.json \\
        --output data/trades.db \\
        --feature-config features_config.json
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data.dataset import FeatureExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_backtest_data(json_path: str) -> list:
    """Load backtest trades from JSON file."""
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        trades = data.get('trades', [])
    else:
        trades = data
    
    logger.info(f"Loaded {len(trades)} trades from {json_path}")
    return trades


def compute_features_from_trade(trade: dict) -> dict:
    """
    Compute features from a raw trade object.
    
    This is a template function. In production, this would compute
    actual features from market data, account state, etc.
    
    For Phase 1 demo, we'll use reasonable defaults based on trade outcome.
    """
    
    # In a real implementation, these would be computed from:
    # - Market data (OHLCV, technical indicators)
    # - Trade setup parameters (entry, SL, TP)
    # - Account state (equity, margin, positions)
    # - Historical data (volatility, trends, correlation)
    
    pnl = trade.get('pnl', 0)
    is_win = pnl > 0
    
    # Demo feature generation (would be replaced with actual computation)
    # Bias features higher if trade won
    base_score = 0.7 if is_win else 0.4
    
    features = {
        'f_structural_level': min(base_score + 0.1, 1.0),
        'f_liquidity_sweep': min(base_score + 0.05, 1.0),
        'f_momentum': min(base_score + 0.08, 1.0),
        'f_volume': min(base_score + 0.07, 1.0),
        'f_risk_reward': 1.0 if trade.get('rrr', 0) >= 3.0 else 0.5,
        'f_macro_alignment': min(base_score + 0.05, 1.0),
        'f_on_chain': 0.8,  # Default neutral
        'f_volatility': 0.6,
        'f_trend_strength': min(base_score + 0.1, 1.0),
        'f_drawdown': max(1.0 - abs(trade.get('drawdown', 0)), 0.0),
        'f_time_since_trade': 1.0,
        'f_correlation_spy': 0.5,
        'f_position_size': 0.9,
        'f_margin_util': 0.5,
        'f_concurrent_trades': 1.0,
        'f_losing_streak': 1.0,
        'f_profit_distance': min(base_score, 1.0),
        'f_mtf_alignment': min(base_score + 0.1, 1.0),
        'f_price_action': min(base_score + 0.05, 1.0),
        'f_confluence': min(base_score + 0.08, 1.0),
    }
    
    # Clamp all values to [0, 1]
    features = {k: max(0.0, min(1.0, v)) for k, v in features.items()}
    
    return features


def determine_outcome(trade: dict) -> int:
    """
    Determine outcome label from trade result.
    
    Per Deniz's design:
    - 0: Loss (pnl < 0)
    - 1: Win (pnl > 0)
    - 2: Breakeven (pnl ≈ 0)
    
    For binary classification, we'll map:
    - 0: Loss
    - 1: Win or Breakeven
    """
    
    pnl = trade.get('pnl', 0)
    
    if pnl < 0:
        return 0  # Loss
    else:
        return 1  # Win or breakeven


def prepare_database(
    json_path: str,
    output_db: str,
    validate_only: bool = False
):
    """
    Prepare training database from backtest JSON.
    
    Args:
        json_path: Path to backtest trades JSON
        output_db: Path to output SQLite database
        validate_only: If True, only validate without creating DB
    """
    
    logger.info("=" * 60)
    logger.info("Preparing Training Data")
    logger.info("=" * 60)
    
    # Load backtest data
    if not Path(json_path).exists():
        logger.error(f"Source file not found: {json_path}")
        raise FileNotFoundError(f"Source file not found: {json_path}")
    
    trades = load_backtest_data(json_path)
    
    if not trades:
        logger.error("No trades found in source file")
        raise ValueError("No trades found in source file")
    
    logger.info(f"Processing {len(trades)} trades...")
    
    # Process trades
    valid_trades = []
    invalid_trades = []
    
    for i, trade in enumerate(trades):
        try:
            # Validate required fields
            required = ['symbol', 'direction', 'entry', 'stop_loss', 'take_profit', 'pnl']
            if not all(k in trade for k in required):
                invalid_trades.append((i, "Missing required fields"))
                continue
            
            # Compute features
            features = compute_features_from_trade(trade)
            
            # Determine outcome
            outcome = determine_outcome(trade)
            
            # Package trade
            processed_trade = {
                'index': i,
                'symbol': trade['symbol'],
                'direction': trade['direction'],
                'entry': trade['entry'],
                'stop_loss': trade['stop_loss'],
                'take_profit': trade['take_profit'],
                'features': features,
                'outcome': outcome,
                'pnl': trade['pnl'],
                'pnl_r': trade.get('pnl_r', 0),
            }
            
            valid_trades.append(processed_trade)
            
        except Exception as e:
            invalid_trades.append((i, str(e)))
    
    logger.info(f"✅ Valid trades: {len(valid_trades)}")
    logger.info(f"⚠️  Invalid trades: {len(invalid_trades)}")
    
    if invalid_trades:
        for idx, reason in invalid_trades[:5]:  # Show first 5
            logger.warning(f"  Trade {idx}: {reason}")
    
    if len(valid_trades) < 10:
        logger.warning(f"Only {len(valid_trades)} valid trades. Minimum 10 recommended.")
    
    if validate_only:
        logger.info("Validation only. Skipping database creation.")
        return
    
    # Create database
    output_path = Path(output_db)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\nCreating database: {output_db}")
    FeatureExtractor.create_database(output_db)
    
    # Insert trades
    for trade_data in valid_trades:
        FeatureExtractor.insert_trade(
            db_path=output_db,
            symbol=trade_data['symbol'],
            direction=trade_data['direction'],
            entry_price=trade_data['entry'],
            stop_loss=trade_data['stop_loss'],
            take_profit=trade_data['take_profit'],
            features=trade_data['features'],
            outcome=trade_data['outcome'],
            pnl_r=trade_data['pnl_r'],
            data_source='backtest'
        )
    
    # Verify
    final_count = FeatureExtractor.get_trade_count(output_db)
    logger.info(f"\n✅ Database created with {final_count} trades")
    logger.info(f"📊 Database saved to: {output_db}")
    
    # Show statistics
    logger.info("\n" + "=" * 60)
    logger.info("Data Statistics")
    logger.info("=" * 60)
    
    import sqlite3
    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()
    
    # Outcome distribution
    cursor.execute("SELECT outcome, COUNT(*) FROM trades_training GROUP BY outcome")
    outcomes = cursor.fetchall()
    
    logger.info("\nOutcome Distribution:")
    for outcome, count in outcomes:
        label = "Loss" if outcome == 0 else "Win"
        pct = 100 * count / final_count
        logger.info(f"  {label:5s}: {count:3d} ({pct:5.1f}%)")
    
    # Feature statistics
    logger.info("\nFeature Statistics (sample):")
    cursor.execute("""
        SELECT 
            AVG(f_structural_level) as avg_structural,
            AVG(f_momentum) as avg_momentum,
            AVG(f_volume) as avg_volume
        FROM trades_training
    """)
    stats = cursor.fetchone()
    if stats:
        logger.info(f"  Avg Structural: {stats[0]:.3f}")
        logger.info(f"  Avg Momentum:   {stats[1]:.3f}")
        logger.info(f"  Avg Volume:     {stats[2]:.3f}")
    
    conn.close()
    
    logger.info("\n✅ Preparation complete! Ready for training.")
    logger.info(f"\nNext: python src/train.py --db-path {output_db}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare training data from backtest')
    parser.add_argument('--source', type=str, required=True,
                       help='Path to backtest trades JSON')
    parser.add_argument('--output', type=str, default='data/trades.db',
                       help='Output SQLite database path')
    parser.add_argument('--validate-only', action='store_true',
                       help='Validate data without creating database')
    
    args = parser.parse_args()
    
    try:
        prepare_database(
            json_path=args.source,
            output_db=args.output,
            validate_only=args.validate_only
        )
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
