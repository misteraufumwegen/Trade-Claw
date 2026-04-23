"""
Unit tests for SetupQualityScorer model.
"""

import pytest
import torch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from models.setup_scorer import (
    SetupQualityScorer,
    TrainingMetrics,
    validate_features,
    apply_hard_gates,
    make_trading_decision
)


class TestSetupQualityScorer:
    """Test the NN model."""
    
    def test_model_initialization(self):
        """Test model can be created."""
        model = SetupQualityScorer(input_size=25, hidden1=64, hidden2=32)
        assert model is not None
        assert model.input_size == 25
    
    def test_model_forward_pass(self):
        """Test forward pass produces correct output shape and range."""
        model = SetupQualityScorer()
        x = torch.randn(4, 25)
        x = torch.clamp(x, 0, 1)  # Normalize
        
        output = model(x)
        
        assert output.shape == (4, 1)
        assert (output >= 0).all() and (output <= 1).all()
    
    def test_model_predict(self):
        """Test predict method."""
        model = SetupQualityScorer()
        x = torch.tensor([[0.8] * 25], dtype=torch.float32)
        
        decisions = model.predict(x, threshold=0.7)
        assert isinstance(decisions, torch.Tensor)
        assert decisions.dtype == torch.bool
    
    def test_model_predict_with_proba(self):
        """Test predict with return_proba=True."""
        model = SetupQualityScorer()
        x = torch.tensor([[0.8] * 25], dtype=torch.float32)
        
        scores, decisions = model.predict(x, return_proba=True)
        assert scores.shape == (1, 1)
        assert decisions.shape == (1,)
    
    def test_model_parameter_count(self):
        """Test model has expected number of parameters."""
        model = SetupQualityScorer()
        param_count = model.count_parameters()
        
        # Expected: 25*64+64 + 64*32+32 + 32*1+1 = 1664 + 2080 + 33 = 3777
        assert param_count == 3777
    
    def test_model_config(self):
        """Test get_config returns expected keys."""
        model = SetupQualityScorer()
        config = model.get_config()
        
        assert 'input_size' in config
        assert 'hidden1' in config
        assert 'hidden2' in config
        assert 'dropout' in config
        assert 'total_params' in config
    
    def test_model_gradient_computation(self):
        """Test that gradients flow correctly."""
        model = SetupQualityScorer()
        x = torch.randn(2, 25, requires_grad=False)
        x = torch.clamp(x, 0, 1)
        y = torch.tensor([[1.0], [0.0]])
        
        loss_fn = torch.nn.BCELoss()
        y_pred = model(x)
        loss = loss_fn(y_pred, y)
        
        loss.backward()
        
        # Check gradients exist
        for param in model.parameters():
            assert param.grad is not None
    
    def test_model_eval_mode(self):
        """Test eval mode (no dropout)."""
        model = SetupQualityScorer()
        x = torch.randn(1, 25)
        x = torch.clamp(x, 0, 1)
        
        model.eval()
        with torch.no_grad():
            out1 = model(x)
            out2 = model(x)
        
        # In eval mode (no dropout), outputs should be identical
        assert torch.allclose(out1, out2)


class TestTrainingMetrics:
    """Test the TrainingMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metrics object can be created."""
        metrics = TrainingMetrics()
        assert metrics is not None
        assert len(metrics.train_loss) == 0
    
    def test_add_loss(self):
        """Test adding loss values."""
        metrics = TrainingMetrics()
        metrics.add_train_loss(0.5)
        metrics.add_train_loss(0.4)
        metrics.add_val_loss(0.45)
        
        assert len(metrics.train_loss) == 2
        assert len(metrics.val_loss) == 1
    
    def test_compute_accuracy(self):
        """Test accuracy computation."""
        metrics = TrainingMetrics()
        y_true = torch.tensor([[1.0], [0.0], [1.0], [0.0]])
        y_pred = torch.tensor([[0.9], [0.1], [0.8], [0.2]])
        
        acc = metrics.compute_accuracy(y_true, y_pred, threshold=0.5)
        assert acc == 1.0  # All correct
    
    def test_compute_precision(self):
        """Test precision computation."""
        metrics = TrainingMetrics()
        y_true = torch.tensor([[1.0], [1.0], [0.0]])
        y_pred = torch.tensor([[0.9], [0.4], [0.8]])  # Predict 1: correct, 1: wrong, 0: wrong
        
        precision = metrics.compute_precision(y_true, y_pred, threshold=0.5)
        # TP=1, FP=1 → precision = 1/2 = 0.5
        assert abs(precision - 0.5) < 0.01
    
    def test_compute_recall(self):
        """Test recall computation."""
        metrics = TrainingMetrics()
        y_true = torch.tensor([[1.0], [1.0], [0.0]])
        y_pred = torch.tensor([[0.9], [0.4], [0.8]])
        
        recall = metrics.compute_recall(y_true, y_pred, threshold=0.5)
        # TP=1, FN=1 → recall = 1/2 = 0.5
        assert abs(recall - 0.5) < 0.01
    
    def test_compute_f1(self):
        """Test F1 score computation."""
        metrics = TrainingMetrics()
        y_true = torch.tensor([[1.0], [1.0], [0.0], [0.0]])
        y_pred = torch.tensor([[0.9], [0.9], [0.1], [0.1]])
        
        f1 = metrics.compute_f1(y_true, y_pred, threshold=0.5)
        assert 0 <= f1 <= 1
    
    def test_get_summary(self):
        """Test summary generation."""
        metrics = TrainingMetrics()
        metrics.add_train_loss(0.5)
        metrics.add_val_loss(0.45)
        
        summary = metrics.get_summary()
        assert 'final_train_loss' in summary
        assert 'final_val_loss' in summary
        assert 'num_epochs' in summary


class TestFeatureValidation:
    """Test feature validation functions."""
    
    def test_validate_features_valid(self):
        """Test validation passes for valid features."""
        features = torch.tensor([[0.5] * 25], dtype=torch.float32)
        assert validate_features(features) is True
    
    def test_validate_features_wrong_size(self):
        """Test validation fails for wrong feature size."""
        features = torch.tensor([[0.5] * 24], dtype=torch.float32)
        with pytest.raises(ValueError, match="Expected 25 features"):
            validate_features(features)
    
    def test_validate_features_out_of_range(self):
        """Test validation fails for out-of-range values."""
        features = torch.tensor([[1.5] * 25], dtype=torch.float32)
        with pytest.raises(ValueError, match="[0, 1]"):
            validate_features(features)
    
    def test_validate_features_nan(self):
        """Test validation fails for NaN values."""
        features = torch.tensor([[float('nan')] * 25], dtype=torch.float32)
        with pytest.raises(ValueError, match="NaN"):
            validate_features(features)
    
    def test_validate_features_inf(self):
        """Test validation fails for inf values."""
        features = torch.tensor([[float('inf')] * 25], dtype=torch.float32)
        with pytest.raises(ValueError, match="inf"):
            validate_features(features)


class TestHardGates:
    """Test hard gate enforcement."""
    
    def test_gates_pass(self):
        """Test gates pass with valid features."""
        features = {
            'f_risk_reward_score': 1.0,
            'f_position_size_ratio': 0.5,
            'f_max_concurrent_trades': 0.8
        }
        allow, reason = apply_hard_gates(features)
        assert allow is True
        assert reason == "GATES_PASSED"
    
    def test_gate_rrr_violation(self):
        """Test R/R gate failure."""
        features = {
            'f_risk_reward_score': 0.0,  # Hard failure
            'f_position_size_ratio': 0.5,
            'f_max_concurrent_trades': 0.8
        }
        allow, reason = apply_hard_gates(features)
        assert allow is False
        assert "RRR" in reason
    
    def test_gate_position_size_violation(self):
        """Test position size gate failure."""
        features = {
            'f_risk_reward_score': 1.0,
            'f_position_size_ratio': 0.0,  # Hard failure
            'f_max_concurrent_trades': 0.8
        }
        allow, reason = apply_hard_gates(features)
        assert allow is False
        assert "POSITION_SIZE" in reason
    
    def test_gate_position_limit_violation(self):
        """Test position limit gate failure."""
        features = {
            'f_risk_reward_score': 1.0,
            'f_position_size_ratio': 0.5,
            'f_max_concurrent_trades': 0.0  # Hard failure
        }
        allow, reason = apply_hard_gates(features)
        assert allow is False
        assert "POSITION_LIMIT" in reason


class TestTradingDecision:
    """Test final trading decision logic."""
    
    def test_decision_trade_allowed(self):
        """Test trade decision when score is above threshold."""
        decision = make_trading_decision(
            nn_score=0.8,
            hard_gates_pass=True,
            threshold=0.7
        )
        
        assert decision['decision'] == 'TRADE'
        assert decision['nn_score'] == 0.8
        assert decision['confidence'] == 0.1  # 0.8 - 0.7
    
    def test_decision_trade_rejected_low_score(self):
        """Test trade decision when score is below threshold."""
        decision = make_trading_decision(
            nn_score=0.6,
            hard_gates_pass=True,
            threshold=0.7
        )
        
        assert decision['decision'] == 'REJECT'
        assert decision['nn_score'] == 0.6
        assert decision['confidence'] == 0.1  # 0.7 - 0.6
    
    def test_decision_trade_rejected_gates(self):
        """Test trade decision when hard gates fail."""
        decision = make_trading_decision(
            nn_score=0.9,
            hard_gates_pass=False,
            threshold=0.7
        )
        
        assert decision['decision'] == 'REJECT'
        assert decision['reason'] == 'HARD_GATES_FAILED'
        assert decision['confidence'] == 0.0
    
    def test_decision_has_timestamp(self):
        """Test decision includes timestamp."""
        decision = make_trading_decision(
            nn_score=0.8,
            hard_gates_pass=True
        )
        
        assert 'timestamp' in decision
        assert isinstance(decision['timestamp'], str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
