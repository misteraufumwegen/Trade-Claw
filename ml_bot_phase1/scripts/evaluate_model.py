#!/usr/bin/env python
"""
Evaluate trained model on test set.

Usage:
    python scripts/evaluate_model.py \\
        --model checkpoints/model_best.pt \\
        --db-path data/trades.db
"""

import argparse
import torch
import sys
from pathlib import Path
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.setup_scorer import SetupQualityScorer
from data.dataset import create_data_loaders

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate(
    model_path: str,
    db_path: str,
    device: str = 'cpu',
    threshold: float = 0.7
):
    """
    Evaluate model on test set.
    
    Args:
        model_path: Path to trained model checkpoint
        db_path: Path to SQLite database
        device: Device to use ('cpu' or 'cuda')
        threshold: Decision threshold
    """
    
    logger.info("=" * 60)
    logger.info("Model Evaluation")
    logger.info("=" * 60)
    
    # Check paths
    if not Path(model_path).exists():
        logger.error(f"Model not found: {model_path}")
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    # Load model
    logger.info(f"Loading model from {model_path}...")
    checkpoint = torch.load(model_path, map_location=device)
    
    model = SetupQualityScorer(device=device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    
    # Load data
    logger.info(f"Loading data from {db_path}...")
    train_loader, val_loader, test_loader = create_data_loaders(
        db_path,
        batch_size=16
    )
    
    criterion = torch.nn.BCELoss()
    
    # Evaluate on each split
    for split_name, data_loader in [('Train', train_loader), ('Val', val_loader), ('Test', test_loader)]:
        logger.info(f"\n{split_name.upper()} Set Evaluation:")
        logger.info("-" * 60)
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for batch_x, batch_y in data_loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device).float().unsqueeze(1)
                
                # Forward pass
                y_pred = model(batch_x)
                loss = criterion(y_pred, batch_y)
                total_loss += loss.item() * batch_y.size(0)
                
                # Metrics
                predictions = (y_pred >= threshold).float()
                correct = (predictions == batch_y).sum().item()
                total_correct += correct
                total_samples += batch_y.size(0)
                
                all_predictions.extend(y_pred.cpu().numpy().flatten().tolist())
                all_targets.extend(batch_y.cpu().numpy().flatten().tolist())
        
        avg_loss = total_loss / total_samples if total_samples > 0 else 0
        accuracy = total_correct / total_samples if total_samples > 0 else 0
        
        # Compute additional metrics
        import numpy as np
        all_predictions = np.array(all_predictions)
        all_targets = np.array(all_targets)
        
        # Precision
        pred_binary = (all_predictions >= threshold).astype(int)
        tp = np.sum((pred_binary == 1) & (all_targets == 1))
        fp = np.sum((pred_binary == 1) & (all_targets == 0))
        fn = np.sum((pred_binary == 0) & (all_targets == 1))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        logger.info(f"  Loss:      {avg_loss:.6f}")
        logger.info(f"  Accuracy:  {accuracy:.4f} ({total_correct}/{total_samples})")
        logger.info(f"  Precision: {precision:.4f}")
        logger.info(f"  Recall:    {recall:.4f}")
        logger.info(f"  F1 Score:  {f1:.4f}")
        
        # Threshold analysis
        logger.info(f"\n  At threshold {threshold}:")
        logger.info(f"    True Positives:  {tp}")
        logger.info(f"    False Positives: {fp}")
        logger.info(f"    False Negatives: {fn}")
    
    # Score distribution
    logger.info("\n" + "=" * 60)
    logger.info("Score Distribution (Test Set)")
    logger.info("=" * 60)
    
    with torch.no_grad():
        all_scores = []
        for batch_x, _ in test_loader:
            batch_x = batch_x.to(device)
            scores = model(batch_x)
            all_scores.extend(scores.cpu().numpy().flatten().tolist())
    
    all_scores = np.array(all_scores)
    logger.info(f"  Min:    {all_scores.min():.4f}")
    logger.info(f"  Max:    {all_scores.max():.4f}")
    logger.info(f"  Mean:   {all_scores.mean():.4f}")
    logger.info(f"  Median: {np.median(all_scores):.4f}")
    logger.info(f"  Std:    {all_scores.std():.4f}")
    
    # Percentiles
    logger.info(f"\n  Percentiles:")
    for p in [25, 50, 75, 90, 95]:
        logger.info(f"    {p}th: {np.percentile(all_scores, p):.4f}")
    
    # Score by outcome
    with torch.no_grad():
        test_x, test_y = [], []
        for batch_x, batch_y in test_loader:
            test_x.append(batch_x)
            test_y.append(batch_y)
        
        test_x = torch.cat(test_x)
        test_y = torch.cat(test_y)
        
        test_x = test_x.to(device)
        scores = model(test_x).cpu().numpy().flatten()
        targets = test_y.numpy()
    
    logger.info(f"\n  Scores by Outcome:")
    for outcome in [0, 1]:
        outcome_scores = scores[targets == outcome]
        if len(outcome_scores) > 0:
            outcome_label = "Loss" if outcome == 0 else "Win"
            logger.info(f"    {outcome_label}s: mean={outcome_scores.mean():.4f}, std={outcome_scores.std():.4f}, n={len(outcome_scores)}")
    
    logger.info("\n✅ Evaluation complete!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate trained model')
    parser.add_argument('--model', type=str, default='checkpoints/model_best.pt',
                       help='Path to trained model checkpoint')
    parser.add_argument('--db-path', type=str, default='data/trades.db',
                       help='Path to SQLite database')
    parser.add_argument('--device', type=str, default='cpu',
                       help='Device (cpu or cuda)')
    parser.add_argument('--threshold', type=float, default=0.7,
                       help='Decision threshold')
    
    args = parser.parse_args()
    
    try:
        evaluate(
            model_path=args.model,
            db_path=args.db_path,
            device=args.device,
            threshold=args.threshold
        )
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
