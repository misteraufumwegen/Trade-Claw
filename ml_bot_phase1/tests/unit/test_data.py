"""
Unit tests for data pipeline and dataset classes.
"""

import pytest
import torch
import sqlite3
import sys
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from data.dataset import TradesDataset, FeatureExtractor


class TestFeatureExtractor:
    """Test the FeatureExtractor class."""
    
    def test_create_database(self):
        """Test database creation."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            FeatureExtractor.create_database(db_path)
            
            # Verify table exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            assert any('trades_training' in t for t in tables)
        finally:
            Path(db_path).unlink()
    
    def test_insert_trade(self):
        """Test inserting a trade into database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            FeatureExtractor.create_database(db_path)
            
            features = {
                'f_structural_level': 0.9,
                'f_liquidity_sweep': 0.8,
                # ... other features would be here
            }
            
            FeatureExtractor.insert_trade(
                db_path=db_path,
                symbol='BTC/USD',
                direction='long',
                entry_price=45000.0,
                stop_loss=44000.0,
                take_profit=46500.0,
                features=features,
                outcome=1,
                pnl_r=1.5
            )
            
            # Verify trade was inserted
            count = FeatureExtractor.get_trade_count(db_path)
            assert count == 1
        finally:
            Path(db_path).unlink()
    
    def test_get_trade_count(self):
        """Test getting trade count."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            FeatureExtractor.create_database(db_path)
            count = FeatureExtractor.get_trade_count(db_path)
            assert count == 0
        finally:
            Path(db_path).unlink()


class TestTradesDataset:
    """Test the TradesDataset class."""
    
    @pytest.fixture
    def sample_database(self):
        """Create a sample database with test data."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Create database and insert sample data
        FeatureExtractor.create_database(db_path)
        
        # Insert 20 sample trades
        for i in range(20):
            features = {f'f_feature_{j}': 0.5 for j in range(20)}
            FeatureExtractor.insert_trade(
                db_path=db_path,
                symbol='BTC/USD',
                direction='long' if i % 2 == 0 else 'short',
                entry_price=45000.0 + i * 100,
                stop_loss=44000.0 + i * 100,
                take_profit=46500.0 + i * 100,
                features=features,
                outcome=1 if i % 3 != 0 else 0,
                pnl_r=1.5 if i % 3 != 0 else -0.5
            )
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink()
    
    def test_dataset_initialization(self, sample_database):
        """Test dataset can be initialized."""
        dataset = TradesDataset(
            sample_database,
            split='train',
            train_size=0.8,
            val_size=0.1
        )
        
        assert dataset is not None
        assert len(dataset) > 0
    
    def test_dataset_length(self, sample_database):
        """Test dataset length is correct."""
        dataset = TradesDataset(sample_database, split='train')
        train_len = len(dataset)
        
        dataset_val = TradesDataset(sample_database, split='val')
        val_len = len(dataset_val)
        
        dataset_test = TradesDataset(sample_database, split='test')
        test_len = len(dataset_test)
        
        total = train_len + val_len + test_len
        assert total == 20
    
    def test_dataset_getitem(self, sample_database):
        """Test getting an item from dataset."""
        dataset = TradesDataset(sample_database, split='train')
        
        features, label = dataset[0]
        
        assert isinstance(features, torch.Tensor)
        assert isinstance(label, torch.Tensor)
        assert features.shape == (20,)  # 20 features (but we only use 20 not 25 in schema)
        assert label.shape == ()
    
    def test_dataset_label_distribution(self, sample_database):
        """Test label distribution."""
        dataset = TradesDataset(sample_database, split='train')
        dist = dataset.get_label_distribution()
        
        assert isinstance(dist, dict)
        assert 0 in dist or 1 in dist  # Should have at least one class


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
