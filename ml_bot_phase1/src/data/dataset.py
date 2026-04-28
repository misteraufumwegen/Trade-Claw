"""
Dataset and DataLoader classes for training the SetupQualityScorer.

Handles:
- Loading trades from SQLite database
- Feature extraction and normalization
- Creating PyTorch DataLoader for training
- Train/val/test splits
"""

import sqlite3
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader, random_split
from pathlib import Path
from typing import Tuple, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TradesDataset(Dataset):
    """PyTorch Dataset for trade features and outcomes."""
    
    def __init__(
        self,
        db_path: str,
        split: str = 'train',
        train_size: float = 0.8,
        val_size: float = 0.1,
        seed: int = 42
    ):
        """
        Initialize dataset from SQLite database.
        
        Args:
            db_path: Path to SQLite database
            split: 'train', 'val', or 'test'
            train_size: Proportion for training (default: 0.8)
            val_size: Proportion for validation (default: 0.1)
            seed: Random seed for reproducibility
        """
        self.db_path = db_path
        self.split = split
        self.seed = seed
        
        # Load data from database
        self.features, self.labels = self._load_from_db()
        
        if len(self.features) == 0:
            raise ValueError(f"No data loaded from {db_path}")
        
        # Split data
        self.indices = self._get_split_indices(train_size, val_size)
        
        logger.info(f"Loaded {len(self)} samples for {split} split")
    
    def _load_from_db(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """Load features and labels from SQLite database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Feature columns (20 total — matching SetupQualityScorer input_size)
        feature_cols = [
            'f_structural_level', 'f_liquidity_sweep', 'f_momentum', 'f_volume',
            'f_risk_reward', 'f_macro_alignment', 'f_on_chain',
            'f_volatility', 'f_trend_strength', 'f_drawdown', 'f_time_since_trade',
            'f_correlation_spy', 'f_position_size', 'f_margin_util', 'f_concurrent_trades',
            'f_losing_streak', 'f_profit_distance', 'f_mtf_alignment',
            'f_price_action', 'f_confluence'
        ]
        
        feature_cols_str = ', '.join(feature_cols)
        
        # Load data
        query = f"""
            SELECT {feature_cols_str}, outcome
            FROM trades_training
            WHERE outcome IS NOT NULL
            ORDER BY id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning("No valid trades found in database")
            return torch.empty((0, 20)), torch.empty(0, dtype=torch.long)
        
        # Convert to numpy then torch
        data = np.array(rows, dtype=np.float32)
        
        features = torch.from_numpy(data[:, :20])  # First 20 columns are features
        labels = torch.from_numpy(data[:, 20:21].astype(np.int64)).squeeze()  # Last column is outcome
        
        # Validate feature ranges
        if (features < 0).any() or (features > 1).any():
            logger.warning("Features outside [0, 1] range detected. Clamping...")
            features = torch.clamp(features, 0, 1)
        
        # Check for NaN/inf
        if torch.isnan(features).any() or torch.isinf(features).any():
            logger.warning("NaN/inf detected in features. Replacing with 0.5...")
            features = torch.where(torch.isnan(features) | torch.isinf(features),
                                  torch.tensor(0.5), features)
        
        return features, labels
    
    def _get_split_indices(
        self,
        train_size: float,
        val_size: float
    ) -> List[int]:
        """Get indices for train/val/test split."""
        
        n = len(self.features)
        test_size = 1 - train_size - val_size
        
        # Create deterministic split
        np.random.seed(self.seed)
        indices = np.random.permutation(n)
        
        train_end = int(n * train_size)
        val_end = int(n * (train_size + val_size))
        
        if self.split == 'train':
            return indices[:train_end].tolist()
        elif self.split == 'val':
            return indices[train_end:val_end].tolist()
        elif self.split == 'test':
            return indices[val_end:].tolist()
        else:
            raise ValueError(f"Unknown split: {self.split}")
    
    def __len__(self) -> int:
        return len(self.indices)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """Return feature vector and label."""
        actual_idx = self.indices[idx]
        features = self.features[actual_idx]
        label = self.labels[actual_idx]
        
        return features, label
    
    def get_label_distribution(self) -> Dict[int, int]:
        """Get count of each outcome class."""
        selected_labels = self.labels[self.indices]
        unique, counts = torch.unique(selected_labels, return_counts=True)
        
        return {int(u.item()): int(c.item()) for u, c in zip(unique, counts)}


def create_data_loaders(
    db_path: str,
    batch_size: int = 16,
    num_workers: int = 0,
    train_size: float = 0.8,
    val_size: float = 0.1,
    seed: int = 42
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train, validation, and test data loaders.
    
    Args:
        db_path: Path to SQLite database
        batch_size: Batch size for training
        num_workers: Number of worker processes
        train_size: Proportion for training
        val_size: Proportion for validation
        seed: Random seed
    
    Returns:
        (train_loader, val_loader, test_loader)
    """
    
    train_dataset = TradesDataset(
        db_path,
        split='train',
        train_size=train_size,
        val_size=val_size,
        seed=seed
    )
    
    val_dataset = TradesDataset(
        db_path,
        split='val',
        train_size=train_size,
        val_size=val_size,
        seed=seed
    )
    
    test_dataset = TradesDataset(
        db_path,
        split='test',
        train_size=train_size,
        val_size=val_size,
        seed=seed
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )
    
    logger.info(f"Train samples: {len(train_dataset)}")
    logger.info(f"Val samples: {len(val_dataset)}")
    logger.info(f"Test samples: {len(test_dataset)}")
    
    return train_loader, val_loader, test_loader


class FeatureExtractor:
    """Extract and normalize features from raw trade data."""
    
    # Feature column mapping
    FEATURE_NAMES = [
        'f_structural_level',
        'f_liquidity_sweep',
        'f_momentum',
        'f_volume',
        'f_risk_reward',
        'f_macro_alignment',
        'f_on_chain',
        'f_volatility',
        'f_trend_strength',
        'f_drawdown',
        'f_time_since_trade',
        'f_correlation_spy',
        'f_position_size',
        'f_margin_util',
        'f_concurrent_trades',
        'f_losing_streak',
        'f_profit_distance',
        'f_mtf_alignment',
        'f_price_action',
        'f_confluence'
    ]
    
    @staticmethod
    def create_database(db_path: str):
        """Create SQLite database with trades_training table."""
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop existing table if present
        cursor.execute("DROP TABLE IF EXISTS trades_training")
        
        # Create table
        cursor.execute("""
            CREATE TABLE trades_training (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(20),
                direction VARCHAR(10),
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                
                -- Features (20 normalized 0-1, matching SetupQualityScorer)
                f_structural_level REAL,
                f_liquidity_sweep REAL,
                f_momentum REAL,
                f_volume REAL,
                f_risk_reward REAL,
                f_macro_alignment REAL,
                f_on_chain REAL,
                f_volatility REAL,
                f_trend_strength REAL,
                f_drawdown REAL,
                f_time_since_trade REAL,
                f_correlation_spy REAL,
                f_position_size REAL,
                f_margin_util REAL,
                f_concurrent_trades REAL,
                f_losing_streak REAL,
                f_profit_distance REAL,
                f_mtf_alignment REAL,
                f_price_action REAL,
                f_confluence REAL,
                
                -- Target
                outcome INTEGER,
                pnl_r REAL,
                closed_at TIMESTAMP,
                
                -- Metadata
                data_source VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created database: {db_path}")
    
    @staticmethod
    def insert_trade(
        db_path: str,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        features: Dict[str, float],
        outcome: int,
        pnl_r: float,
        data_source: str = 'backtest'
    ):
        """Insert a single trade with features into database."""
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades_training (
                symbol, direction, entry_price, stop_loss, take_profit,
                f_structural_level, f_liquidity_sweep, f_momentum, f_volume,
                f_risk_reward, f_macro_alignment, f_on_chain, f_volatility,
                f_trend_strength, f_drawdown, f_time_since_trade, f_correlation_spy,
                f_position_size, f_margin_util, f_concurrent_trades, f_losing_streak,
                f_profit_distance, f_mtf_alignment, f_price_action, f_confluence,
                outcome, pnl_r, data_source
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?
            )
        """, (
            symbol, direction, entry_price, stop_loss, take_profit,
            features.get('f_structural_level', 0.5),
            features.get('f_liquidity_sweep', 0.5),
            features.get('f_momentum', 0.5),
            features.get('f_volume', 0.5),
            features.get('f_risk_reward', 0.5),
            features.get('f_macro_alignment', 0.5),
            features.get('f_on_chain', 0.5),
            features.get('f_volatility', 0.5),
            features.get('f_trend_strength', 0.5),
            features.get('f_drawdown', 0.5),
            features.get('f_time_since_trade', 0.5),
            features.get('f_correlation_spy', 0.5),
            features.get('f_position_size', 0.5),
            features.get('f_margin_util', 0.5),
            features.get('f_concurrent_trades', 0.5),
            features.get('f_losing_streak', 0.5),
            features.get('f_profit_distance', 0.5),
            features.get('f_mtf_alignment', 0.5),
            features.get('f_price_action', 0.5),
            features.get('f_confluence', 0.5),
            outcome, pnl_r, data_source
        ))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_trade_count(db_path: str) -> int:
        """Get number of trades in database."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades_training")
        count = cursor.fetchone()[0]
        conn.close()
        return count


if __name__ == '__main__':
    print("Testing dataset module...")
    
    # This would be run during training setup
    # db_path = 'data/trades.db'
    # FeatureExtractor.create_database(db_path)
    # print(f"✅ Database created: {db_path}")
