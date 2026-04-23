"""
SetupQualityScorer Neural Network Model

A PyTorch-based feedforward network that predicts trade setup quality scores
based on 25 normalized features from the Surgical Precision Trading System.

Output: Setup-Quality-Score (0.0-1.0) indicating P(not failure)
"""

import torch
import torch.nn as nn
from typing import Tuple, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SetupQualityScorer(nn.Module):
    """
    Feedforward neural network for predicting trade setup quality.
    
    Architecture:
    - Input: 25 normalized features [0, 1]
    - Hidden Layer 1: 64 neurons, ReLU, Dropout(0.2)
    - Hidden Layer 2: 32 neurons, ReLU, Dropout(0.2)
    - Output: 1 neuron, Sigmoid → [0, 1] probability
    
    Total parameters: 3,777
    """
    
    def __init__(
        self,
        input_size: int = 25,
        hidden1: int = 64,
        hidden2: int = 32,
        dropout: float = 0.2,
        device: str = 'cpu'
    ):
        """
        Initialize the Setup Quality Scorer.
        
        Args:
            input_size: Number of input features (default: 25)
            hidden1: Neurons in first hidden layer (default: 64)
            hidden2: Neurons in second hidden layer (default: 32)
            dropout: Dropout rate (default: 0.2)
            device: Device to run on ('cpu' or 'cuda')
        """
        super(SetupQualityScorer, self).__init__()
        
        self.input_size = input_size
        self.hidden1 = hidden1
        self.hidden2 = hidden2
        self.dropout_rate = dropout
        self.device = device
        
        # Layer 1
        self.fc1 = nn.Linear(input_size, hidden1)
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)
        
        # Layer 2
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)
        
        # Output layer
        self.fc3 = nn.Linear(hidden2, 1)
        self.sigmoid = nn.Sigmoid()
        
        # Initialize weights
        self._init_weights()
        
        self.to(device)
    
    def _init_weights(self):
        """Initialize weights using Xavier uniform."""
        for module in [self.fc1, self.fc2, self.fc3]:
            nn.init.xavier_uniform_(module.weight)
            nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch_size, 25)
        
        Returns:
            output: Tensor of shape (batch_size, 1) with values in [0, 1]
        """
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.drop1(x)
        
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.drop2(x)
        
        x = self.fc3(x)
        x = self.sigmoid(x)
        
        return x
    
    def predict(
        self,
        x: torch.Tensor,
        threshold: float = 0.7,
        return_proba: bool = False
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict if setup should be traded.
        
        Args:
            x: Input features (batch_size, 25)
            threshold: Score threshold for trading decision
            return_proba: If True, also return probability scores
        
        Returns:
            If return_proba=False:
                (decisions: Boolean tensor)
            If return_proba=True:
                (scores: Float tensor, decisions: Boolean tensor)
        """
        self.eval()
        with torch.no_grad():
            scores = self.forward(x)
            decisions = (scores >= threshold).squeeze()
        
        if return_proba:
            return scores, decisions
        return decisions
    
    def get_config(self) -> Dict:
        """Return model configuration."""
        return {
            'input_size': self.input_size,
            'hidden1': self.hidden1,
            'hidden2': self.hidden2,
            'dropout': self.dropout_rate,
            'total_params': self.count_parameters()
        }
    
    def count_parameters(self) -> int:
        """Count total parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class TrainingMetrics:
    """Track metrics during training."""
    
    def __init__(self):
        self.train_loss = []
        self.val_loss = []
        self.train_acc = []
        self.val_acc = []
        self.train_precision = []
        self.train_recall = []
    
    def add_train_loss(self, loss: float):
        self.train_loss.append(loss)
    
    def add_val_loss(self, loss: float):
        self.val_loss.append(loss)
    
    def add_train_acc(self, acc: float):
        self.train_acc.append(acc)
    
    def add_val_acc(self, acc: float):
        self.val_acc.append(acc)
    
    def add_precision(self, precision: float):
        self.train_precision.append(precision)
    
    def add_recall(self, recall: float):
        self.train_recall.append(recall)
    
    def compute_accuracy(
        self,
        y_true: torch.Tensor,
        y_pred_proba: torch.Tensor,
        threshold: float = 0.7
    ) -> float:
        """Compute accuracy at decision threshold."""
        y_pred_binary = (y_pred_proba >= threshold).float()
        acc = (y_pred_binary == y_true).float().mean()
        return acc.item()
    
    def compute_precision(
        self,
        y_true: torch.Tensor,
        y_pred_proba: torch.Tensor,
        threshold: float = 0.7
    ) -> float:
        """TP / (TP + FP) — of trades we said 'yes', how many were wins?"""
        y_pred_binary = (y_pred_proba >= threshold).float()
        tp = ((y_pred_binary == 1) & (y_true == 1)).sum().float()
        fp = ((y_pred_binary == 1) & (y_true == 0)).sum().float()
        
        if (tp + fp).item() == 0:
            return 0.0
        return (tp / (tp + fp)).item()
    
    def compute_recall(
        self,
        y_true: torch.Tensor,
        y_pred_proba: torch.Tensor,
        threshold: float = 0.7
    ) -> float:
        """TP / (TP + FN) — of actual wins, how many did we catch?"""
        y_pred_binary = (y_pred_proba >= threshold).float()
        tp = ((y_pred_binary == 1) & (y_true == 1)).sum().float()
        fn = ((y_pred_binary == 0) & (y_true == 1)).sum().float()
        
        if (tp + fn).item() == 0:
            return 0.0
        return (tp / (tp + fn)).item()
    
    def compute_f1(
        self,
        y_true: torch.Tensor,
        y_pred_proba: torch.Tensor,
        threshold: float = 0.7
    ) -> float:
        """F1 score: harmonic mean of precision and recall."""
        precision = self.compute_precision(y_true, y_pred_proba, threshold)
        recall = self.compute_recall(y_true, y_pred_proba, threshold)
        
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        return {
            'final_train_loss': self.train_loss[-1] if self.train_loss else None,
            'final_val_loss': self.val_loss[-1] if self.val_loss else None,
            'best_train_loss': min(self.train_loss) if self.train_loss else None,
            'best_val_loss': min(self.val_loss) if self.val_loss else None,
            'final_train_acc': self.train_acc[-1] if self.train_acc else None,
            'final_val_acc': self.val_acc[-1] if self.val_acc else None,
            'num_epochs': len(self.train_loss),
        }


def validate_features(features: torch.Tensor, expected_size: int = 25) -> bool:
    """
    Validate feature vector before inference.
    
    Rules:
    - All values must be in [0, 1]
    - No NaN or inf values
    - Correct shape (batch_size, 25)
    
    Args:
        features: Feature tensor
        expected_size: Expected number of features
    
    Returns:
        True if valid, raises ValueError otherwise
    """
    if features.shape[-1] != expected_size:
        raise ValueError(f"Expected {expected_size} features, got {features.shape[-1]}")
    
    if (features < 0).any() or (features > 1).any():
        raise ValueError("All features must be in [0, 1]")
    
    if torch.isnan(features).any() or torch.isinf(features).any():
        raise ValueError("Features contain NaN or inf")
    
    return True


def apply_hard_gates(features: Dict[str, float]) -> Tuple[bool, str]:
    """
    Check hard rules that override NN output.
    
    These are non-negotiable constraints from Deniz's design:
    1. R/R ratio must be >= 1:3
    2. Position size must be <= 5% of account
    3. Cannot exceed position limit
    
    Args:
        features: Dictionary of feature values
    
    Returns:
        (allow_trade: bool, reason: str)
    """
    
    # Gate 1: R/R ratio (critical)
    if features.get('f_risk_reward_score', 1.0) == 0.0:
        return False, "HARD_GATE_RRR_VIOLATION"
    
    # Gate 2: Position size
    if features.get('f_position_size_ratio', 1.0) == 0.0:
        return False, "HARD_GATE_POSITION_SIZE_VIOLATION"
    
    # Gate 3: Position limit
    if features.get('f_max_concurrent_trades', 1.0) == 0.0:
        return False, "HARD_GATE_POSITION_LIMIT_EXCEEDED"
    
    return True, "GATES_PASSED"


def make_trading_decision(
    nn_score: float,
    hard_gates_pass: bool,
    threshold: float = 0.7
) -> Dict:
    """
    Final trading decision logic.
    
    Combines hard gates + NN score to make final decision.
    
    Args:
        nn_score: Output from NN (0-1)
        hard_gates_pass: Result of hard gate checks
        threshold: NN score threshold
    
    Returns:
        Dictionary with decision, reason, and confidence
    """
    
    if not hard_gates_pass:
        return {
            'decision': 'REJECT',
            'reason': 'HARD_GATES_FAILED',
            'nn_score': nn_score,
            'confidence': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    
    if nn_score >= threshold:
        confidence = nn_score - threshold
        return {
            'decision': 'TRADE',
            'reason': 'NN_SCORE_ABOVE_THRESHOLD',
            'nn_score': nn_score,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
    else:
        confidence = threshold - nn_score
        return {
            'decision': 'REJECT',
            'reason': 'NN_SCORE_BELOW_THRESHOLD',
            'nn_score': nn_score,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == '__main__':
    # Quick test
    print("Testing SetupQualityScorer...")
    
    model = SetupQualityScorer(device='cpu')
    print(f"Model config: {model.get_config()}")
    
    # Dummy input
    x = torch.randn(4, 25)
    x = torch.clamp(x, 0, 1)  # Normalize to [0, 1]
    
    # Forward pass
    scores = model(x)
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {scores.shape}")
    print(f"Output range: [{scores.min():.4f}, {scores.max():.4f}]")
    
    # Predict
    decisions = model.predict(x, threshold=0.7)
    print(f"Trade decisions: {decisions}")
    
    print("✅ Model test passed!")
