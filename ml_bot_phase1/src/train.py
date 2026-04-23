"""
Training script for SetupQualityScorer model.

Usage:
    python src/train.py --db-path data/trades.db --epochs 100 --batch-size 16
"""

import argparse
import torch
import torch.nn as nn
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Dict

from models.setup_scorer import SetupQualityScorer, TrainingMetrics
from data.dataset import create_data_loaders, FeatureExtractor

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train_epoch(
    model: SetupQualityScorer,
    train_loader,
    criterion,
    optimizer,
    device: str,
    metrics: TrainingMetrics
) -> float:
    """Train for one epoch."""
    
    model.train()
    total_loss = 0.0
    
    for batch_x, batch_y in train_loader:
        batch_x = batch_x.to(device)
        batch_y = batch_y.to(device).float().unsqueeze(1)
        
        # Forward pass
        y_pred = model(batch_x)
        loss = criterion(y_pred, batch_y)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    avg_loss = total_loss / len(train_loader)
    metrics.add_train_loss(avg_loss)
    
    return avg_loss


def validate_epoch(
    model: SetupQualityScorer,
    val_loader,
    criterion,
    device: str,
    metrics: TrainingMetrics,
    threshold: float = 0.7
) -> float:
    """Validate model on validation set."""
    
    model.eval()
    total_loss = 0.0
    
    with torch.no_grad():
        for batch_x, batch_y in val_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device).float().unsqueeze(1)
            
            y_pred = model(batch_x)
            loss = criterion(y_pred, batch_y)
            total_loss += loss.item()
            
            # Compute metrics
            if batch_x is not None:  # First batch only for efficiency
                acc = metrics.compute_accuracy(batch_y, y_pred, threshold)
                precision = metrics.compute_precision(batch_y, y_pred, threshold)
                recall = metrics.compute_recall(batch_y, y_pred, threshold)
    
    avg_loss = total_loss / len(val_loader)
    metrics.add_val_loss(avg_loss)
    
    return avg_loss


def train(
    db_path: str,
    output_dir: str = 'checkpoints',
    epochs: int = 100,
    batch_size: int = 16,
    learning_rate: float = 0.001,
    device: str = 'cpu',
    early_stopping_patience: int = 10,
    seed: int = 42
):
    """
    Train the SetupQualityScorer model.
    
    Args:
        db_path: Path to SQLite database with trades
        output_dir: Directory to save checkpoints
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate
        device: 'cpu' or 'cuda'
        early_stopping_patience: Patience for early stopping
        seed: Random seed
    """
    
    # Setup
    torch.manual_seed(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("Training SetupQualityScorer")
    logger.info("=" * 60)
    logger.info(f"Database: {db_path}")
    logger.info(f"Epochs: {epochs}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Learning rate: {learning_rate}")
    logger.info(f"Device: {device}")
    
    # Check database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    trade_count = FeatureExtractor.get_trade_count(db_path)
    logger.info(f"Total trades in database: {trade_count}")
    
    if trade_count < 20:
        logger.warning(f"Very few trades ({trade_count}). Model may underfit.")
    
    # Create data loaders
    logger.info("Creating data loaders...")
    train_loader, val_loader, test_loader = create_data_loaders(
        db_path,
        batch_size=batch_size,
        train_size=0.8,
        val_size=0.1,
        seed=seed
    )
    
    # Initialize model
    logger.info("Initializing model...")
    model = SetupQualityScorer(
        input_size=25,
        hidden1=64,
        hidden2=32,
        dropout=0.2,
        device=device
    )
    
    logger.info(f"Model configuration: {model.get_config()}")
    
    # Training setup
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        weight_decay=1e-5
    )
    
    metrics = TrainingMetrics()
    
    # Training loop
    logger.info("Starting training...")
    best_val_loss = float('inf')
    patience_counter = 0
    
    for epoch in range(epochs):
        # Train
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device, metrics)
        
        # Validate
        val_loss = validate_epoch(model, val_loader, criterion, device, metrics)
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            
            # Save best model
            checkpoint_path = output_path / 'model_best.pt'
            save_checkpoint(checkpoint_path, model, optimizer, epoch, metrics)
            logger.info(f"[{epoch+1:3d}] Loss (train/val): {train_loss:.6f} / {val_loss:.6f} ✓ SAVED")
        else:
            patience_counter += 1
            logger.info(f"[{epoch+1:3d}] Loss (train/val): {train_loss:.6f} / {val_loss:.6f} (patience: {patience_counter}/{early_stopping_patience})")
            
            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping triggered at epoch {epoch+1}")
                break
    
    # Test on held-out test set
    logger.info("\n" + "=" * 60)
    logger.info("Evaluating on test set...")
    logger.info("=" * 60)
    
    model.eval()
    test_loss = 0.0
    test_correct = 0
    test_total = 0
    
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device).float().unsqueeze(1)
            
            y_pred = model(batch_x)
            loss = criterion(y_pred, batch_y)
            test_loss += loss.item()
            
            # Compute accuracy
            predictions = (y_pred >= 0.7).float()
            test_correct += (predictions == batch_y).sum().item()
            test_total += batch_y.size(0)
    
    test_loss /= len(test_loader)
    test_acc = test_correct / test_total if test_total > 0 else 0
    
    logger.info(f"Test Loss: {test_loss:.6f}")
    logger.info(f"Test Accuracy: {test_acc:.4f} ({test_correct}/{test_total})")
    
    # Save final metrics
    summary = {
        'completed_epochs': epoch + 1,
        'best_val_loss': best_val_loss,
        'test_loss': test_loss,
        'test_accuracy': test_acc,
        'timestamp': datetime.now().isoformat(),
        'hyperparameters': {
            'epochs': epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate,
            'early_stopping_patience': early_stopping_patience,
        }
    }
    
    summary_path = output_path / 'training_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\nTraining complete! Summary saved to {summary_path}")
    logger.info(f"Best model saved to {output_path / 'model_best.pt'}")


def save_checkpoint(
    path: Path,
    model: SetupQualityScorer,
    optimizer,
    epoch: int,
    metrics: TrainingMetrics
):
    """Save model checkpoint."""
    
    checkpoint = {
        'epoch': epoch,
        'model_state': model.state_dict(),
        'model_config': model.get_config(),
        'optimizer_state': optimizer.state_dict(),
        'metrics': metrics.get_summary(),
        'timestamp': datetime.now().isoformat(),
    }
    
    torch.save(checkpoint, path)


def load_checkpoint(path: str, device: str = 'cpu') -> SetupQualityScorer:
    """Load model from checkpoint."""
    
    checkpoint = torch.load(path, map_location=device)
    
    model = SetupQualityScorer(
        input_size=25,
        hidden1=64,
        hidden2=32,
        dropout=0.2,
        device=device
    )
    
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    
    logger.info(f"Loaded model from {path}")
    logger.info(f"Trained for {checkpoint.get('epoch', '?')} epochs")
    
    return model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train SetupQualityScorer')
    parser.add_argument('--db-path', type=str, default='data/trades.db',
                       help='Path to SQLite database')
    parser.add_argument('--output-dir', type=str, default='checkpoints',
                       help='Directory to save checkpoints')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=16,
                       help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                       help='Learning rate')
    parser.add_argument('--device', type=str, default='cpu',
                       help='Device (cpu or cuda)')
    parser.add_argument('--patience', type=int, default=10,
                       help='Early stopping patience')
    
    args = parser.parse_args()
    
    train(
        db_path=args.db_path,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        device=args.device,
        early_stopping_patience=args.patience
    )
