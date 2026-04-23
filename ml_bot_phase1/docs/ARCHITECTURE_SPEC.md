# Neural Network Architecture Specification

**Version:** 0.1  
**Date:** 2026-04-22  
**Owner:** Elon (CTO)  
**Status:** Complete Specification

---

## Executive Summary

The **Setup-Quality Scorer NN** is a fully-connected feedforward network that ingests **25 normalized features** and outputs a **single continuous score (0.0-1.0)** predicting the probability that a trade setup will be profitable (not fail).

### Design Philosophy
- **Simple & Interpretable:** 3-layer architecture, not a black box
- **Production-Ready:** Fast inference (<1ms), low memory footprint
- **Failure-Focused:** Trained to predict P(outcome ≠ loss) using binary cross-entropy
- **Modular:** Easily integrable into FastAPI bot (Phase 2)
- **Scalable:** Can retrain every 100 live trades without model versioning overhead

---

## Part 1: Network Architecture

### 1.1 Layer Specification

```
INPUT LAYER (25 features)
    ↓
HIDDEN LAYER 1: 64 neurons, ReLU activation
    ↓ Dropout (p=0.2)
    ↓
HIDDEN LAYER 2: 32 neurons, ReLU activation
    ↓ Dropout (p=0.2)
    ↓
OUTPUT LAYER: 1 neuron, Sigmoid activation
    ↓
Setup-Quality-Score (0.0-1.0)
```

### 1.2 Layer Details

#### Input Layer
- **Size:** 25 (feature vector)
- **Type:** torch.FloatTensor
- **Range:** [0.0, 1.0] (pre-normalized)
- **Batch Dimension:** (batch_size, 25)

#### Hidden Layer 1
- **Input:** 25
- **Output:** 64
- **Activation:** ReLU (x > 0 ? x : 0)
- **Initialization:** Xavier uniform (variance_scaling)
- **Dropout:** 0.2 (20% neurons randomly disabled during training)
- **Purpose:** Extract composite features from base inputs

#### Hidden Layer 2
- **Input:** 64
- **Output:** 32
- **Activation:** ReLU
- **Initialization:** Xavier uniform
- **Dropout:** 0.2
- **Purpose:** Secondary feature abstraction, dimensionality reduction

#### Output Layer
- **Input:** 32
- **Output:** 1
- **Activation:** Sigmoid (σ(x) = 1 / (1 + e^(-x)) → output in [0, 1])
- **Purpose:** Probability output (P(not failure))

### 1.3 Total Parameters

```
Layer 1: 25 × 64 + 64 = 1,664 params
Layer 2: 64 × 32 + 32 = 2,080 params
Layer 3: 32 × 1  + 1  = 33 params
─────────────────────────────────
TOTAL:                 = 3,777 params
```

Very lean model → fast training, low inference latency.

---

## Part 2: Loss Function & Training

### 2.1 Loss Function: Binary Cross-Entropy

```python
loss = BinaryCrossEntropy()
```

#### Rationale

Each trade is labeled as:
- **y = 1:** Trade profitable (outcome ∈ {1, 2})
- **y = 0:** Trade loss (outcome = 0)

Per Deniz: **"Jeder geschlossene Verlust-Trade = Failure"**

The BCE loss is:
```
L = -[y * log(ŷ) + (1 - y) * log(1 - ŷ)]
```

Where:
- `y` = true label (0 or 1)
- `ŷ` = model output (prediction in [0, 1])

#### Behavior
- If trade is loss (`y=0`) and model predicts high (ŷ=0.9): Large penalty
- If trade is win (`y=1`) and model predicts low (ŷ=0.1): Large penalty
- If correct: Low loss

This naturally penalizes **false positives** (predicting win when it's loss) more severely than **false negatives** (predicting loss when it's win).

### 2.2 Optimizer

```python
optimizer = torch.optim.Adam(
    params=model.parameters(),
    lr=0.001,          # Learning rate
    betas=(0.9, 0.999), # Exponential moving averages
    eps=1e-8,           # Numerical stability
    weight_decay=1e-5   # L2 regularization
)
```

#### Adam Settings
- **LR = 0.001:** Standard for neural networks, adjusted during training if loss plateaus
- **Weight Decay = 1e-5:** Light L2 regularization to prevent overfitting
- **Betas:** Standard defaults for Adam optimizer

### 2.3 Training Hyperparameters

```python
hyperparameters = {
    'epochs': 100,
    'batch_size': 16,
    'learning_rate': 0.001,
    'dropout_rate': 0.2,
    'weight_decay': 1e-5,
    'early_stopping_patience': 10,  # Stop if val loss doesn't improve for 10 epochs
    'validation_split': 0.2,         # 80% train, 20% validation
    'train_test_split': 0.1,         # Hold out 10% for final testing
}
```

#### Rationale
- **100 epochs:** Enough iterations to converge without overfitting
- **Batch size 16:** Balance between stability and memory
- **Early stopping:** Prevent overfitting; stop when validation loss plateaus
- **80/20 split:** Standard validation split for small datasets

### 2.4 Training Loop Pseudocode

```python
for epoch in range(num_epochs):
    # Training phase
    model.train()
    train_loss = 0
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        
        y_pred = model(batch_x)
        loss = criterion(y_pred, batch_y)
        
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
    
    # Validation phase
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for batch_x, batch_y in val_loader:
            y_pred = model(batch_x)
            loss = criterion(y_pred, batch_y)
            val_loss += loss.item()
    
    # Early stopping check
    if val_loss > best_val_loss:
        patience_counter += 1
        if patience_counter >= 10:
            print("Early stopping triggered")
            break
    else:
        best_val_loss = val_loss
        patience_counter = 0
        # Save checkpoint
        torch.save(model.state_dict(), 'model_best.pt')
```

---

## Part 3: Model Class (PyTorch)

### 3.1 Python Implementation

```python
import torch
import torch.nn as nn

class SetupQualityScorer(nn.Module):
    """
    Neural Network for predicting trade setup quality.
    
    Input: 25 normalized features (0-1 range)
    Output: Setup quality score (0-1, probability of not failing)
    """
    
    def __init__(self, input_size=25, hidden1=64, hidden2=32, dropout=0.2):
        """
        Args:
            input_size: Number of input features (default: 25)
            hidden1: Neurons in first hidden layer (default: 64)
            hidden2: Neurons in second hidden layer (default: 32)
            dropout: Dropout rate (default: 0.2)
        """
        super(SetupQualityScorer, self).__init__()
        
        self.fc1 = nn.Linear(input_size, hidden1)
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)
        
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)
        
        self.fc3 = nn.Linear(hidden2, 1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
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
    
    def predict(self, x, threshold=0.7):
        """
        Predict if setup should be traded.
        
        Args:
            x: Input features (batch_size, 25)
            threshold: Score threshold for trading (default: 0.7)
        
        Returns:
            scores: Float tensor of shape (batch_size, 1)
            decisions: Boolean tensor (True = trade, False = reject)
        """
        self.eval()
        with torch.no_grad():
            scores = self.forward(x)
            decisions = (scores >= threshold).squeeze()
        return scores, decisions
```

---

## Part 4: Inference Pipeline

### 4.1 Single Trade Inference

```python
def score_setup(
    features_dict: dict,
    model: SetupQualityScorer,
    threshold: float = 0.7,
    device: str = 'cpu'
) -> dict:
    """
    Score a single trade setup and decide whether to trade.
    
    Args:
        features_dict: 25-key dictionary with feature values (all 0-1)
        model: Trained SetupQualityScorer instance
        threshold: Decision threshold (default: 0.7)
        device: 'cpu' or 'cuda'
    
    Returns:
        {
            'score': float (0-1),
            'trade': bool (True if score >= threshold),
            'confidence': float (how close to threshold),
            'timestamp': datetime
        }
    """
    # Convert dict to tensor
    feature_vector = torch.tensor([
        features_dict['f_structural_level'],
        features_dict['f_liquidity_sweep'],
        # ... (all 25 features in order)
    ], dtype=torch.float32).unsqueeze(0).to(device)
    
    # Inference
    model.eval()
    with torch.no_grad():
        score = model(feature_vector).item()
    
    # Decision
    trade = score >= threshold
    confidence = abs(score - threshold)  # Distance from threshold
    
    return {
        'score': score,
        'trade': trade,
        'confidence': confidence,
        'timestamp': datetime.now()
    }
```

### 4.2 Batch Inference (for backtesting)

```python
def score_batch(
    feature_matrix: torch.Tensor,  # Shape: (N, 25)
    model: SetupQualityScorer,
    threshold: float = 0.7,
    device: str = 'cpu'
) -> dict:
    """
    Score multiple setups in batch (faster).
    
    Args:
        feature_matrix: Tensor of shape (N, 25)
        model: Trained SetupQualityScorer
        threshold: Decision threshold
        device: 'cpu' or 'cuda'
    
    Returns:
        {
            'scores': Tensor (N, 1),
            'trades': Tensor (N,) bool,
            'mean_score': float,
            'pass_rate': float (% passing threshold)
        }
    """
    model.eval()
    device_tensor = feature_matrix.to(device)
    
    with torch.no_grad():
        scores = model(device_tensor)
    
    trades = (scores >= threshold).squeeze()
    pass_rate = trades.float().mean().item()
    
    return {
        'scores': scores,
        'trades': trades,
        'mean_score': scores.mean().item(),
        'pass_rate': pass_rate
    }
```

---

## Part 5: Model Persistence

### 5.1 Checkpoint Format

```python
checkpoint = {
    'epoch': current_epoch,
    'model_state': model.state_dict(),
    'optimizer_state': optimizer.state_dict(),
    'hyperparameters': hyperparameters,
    'metrics': {
        'train_loss': train_loss_history,
        'val_loss': val_loss_history,
        'train_acc': train_acc_history,
        'val_acc': val_acc_history,
    },
    'timestamp': datetime.now().isoformat(),
    'data_version': 'v0.1_backtest_50trades',
}

torch.save(checkpoint, 'checkpoints/model_v0.1.pt')
```

### 5.2 Loading for Inference

```python
def load_model(checkpoint_path: str, device: str = 'cpu') -> SetupQualityScorer:
    """Load trained model from checkpoint."""
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    model = SetupQualityScorer(
        input_size=25,
        hidden1=64,
        hidden2=32,
        dropout=0.2
    ).to(device)
    
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    
    return model
```

---

## Part 6: Performance Monitoring

### 6.1 Metrics During Training

```python
class TrainingMetrics:
    """Track metrics during training."""
    
    def __init__(self):
        self.train_loss = []
        self.val_loss = []
        self.train_acc = []
        self.val_acc = []
        self.train_precision = []
        self.train_recall = []
    
    def compute_accuracy(self, y_true, y_pred_proba, threshold=0.7):
        """Compute accuracy at decision threshold."""
        y_pred_binary = (y_pred_proba >= threshold).float()
        acc = (y_pred_binary == y_true).float().mean()
        return acc.item()
    
    def compute_precision(self, y_true, y_pred_proba, threshold=0.7):
        """TP / (TP + FP) — of trades we said 'yes', how many were wins?"""
        y_pred_binary = (y_pred_proba >= threshold).float()
        tp = ((y_pred_binary == 1) & (y_true == 1)).sum().item()
        fp = ((y_pred_binary == 1) & (y_true == 0)).sum().item()
        
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)
    
    def compute_recall(self, y_true, y_pred_proba, threshold=0.7):
        """TP / (TP + FN) — of actual wins, how many did we catch?"""
        y_pred_binary = (y_pred_proba >= threshold).float()
        tp = ((y_pred_binary == 1) & (y_true == 1)).sum().item()
        fn = ((y_pred_binary == 0) & (y_true == 1)).sum().item()
        
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)
```

### 6.2 Key Metrics to Track

| Metric | Target | Notes |
|--------|--------|-------|
| **Train Loss** | Decreasing | Should trend down |
| **Val Loss** | Stable, low | Should not increase (overfitting signal) |
| **Accuracy** | ≥ 80% | At threshold 0.7 |
| **Precision** | ≥ 85% | Of trades we take, % that are wins |
| **Recall** | ≥ 70% | Of actual wins, % we catch |
| **F1 Score** | ≥ 0.75 | Harmonic mean of precision & recall |

---

## Part 7: Edge Cases & Safety

### 7.1 Input Validation

```python
def validate_features(features: torch.Tensor) -> bool:
    """
    Validate feature vector before inference.
    
    Rules:
    - All values must be in [0, 1]
    - No NaN or inf values
    - Correct shape (batch_size, 25)
    """
    if features.shape[-1] != 25:
        raise ValueError(f"Expected 25 features, got {features.shape[-1]}")
    
    if (features < 0).any() or (features > 1).any():
        raise ValueError("All features must be in [0, 1]")
    
    if torch.isnan(features).any() or torch.isinf(features).any():
        raise ValueError("Features contain NaN or inf")
    
    return True
```

### 7.2 Hard Gates (Pre-NN Checks)

Before NN inference, enforce these gates:

```python
def apply_hard_gates(features: dict) -> tuple[bool, str]:
    """
    Check hard rules that override NN output.
    
    Returns:
        (allow_trade: bool, reason: str)
    """
    
    # Gate 1: R/R ratio must be >= 1:3
    if features['f_risk_reward_score'] == 0.0:
        return False, "HARD_GATE_RRR"
    
    # Gate 2: Position size must be <= 5% of account
    if features['f_position_size_ratio'] == 0.0:
        return False, "HARD_GATE_POSITION_SIZE"
    
    # Gate 3: Cannot exceed position limit
    if features['f_max_concurrent_trades'] == 0.0:
        return False, "HARD_GATE_POSITION_LIMIT"
    
    return True, "GATES_PASSED"
```

### 7.3 NN Threshold Enforcement

```python
def make_trading_decision(
    nn_score: float,
    hard_gates_pass: bool,
    threshold: float = 0.7
) -> dict:
    """
    Final trading decision logic.
    
    Returns:
        {
            'decision': 'TRADE' | 'REJECT',
            'reason': str,
            'nn_score': float,
            'confidence': float
        }
    """
    
    if not hard_gates_pass:
        return {
            'decision': 'REJECT',
            'reason': 'HARD_GATES_FAILED',
            'nn_score': nn_score,
            'confidence': 0.0
        }
    
    if nn_score >= threshold:
        confidence = nn_score - threshold
        return {
            'decision': 'TRADE',
            'reason': 'NN_SCORE_ABOVE_THRESHOLD',
            'nn_score': nn_score,
            'confidence': confidence
        }
    else:
        confidence = threshold - nn_score
        return {
            'decision': 'REJECT',
            'reason': 'NN_SCORE_BELOW_THRESHOLD',
            'nn_score': nn_score,
            'confidence': confidence
        }
```

---

## Part 8: Deployment (Phase 2 Integration)

### 8.1 FastAPI Integration

```python
# In FastAPI bot (Phase 2)
from ml_bot.models.setup_scorer import SetupQualityScorer

app = FastAPI()

# Load model on startup
model = None

@app.on_event("startup")
async def load_model():
    global model
    model = SetupQualityScorer().to('cuda')
    checkpoint = torch.load('checkpoints/model_v0.1.pt')
    model.load_state_dict(checkpoint['model_state'])

@app.post("/score_setup")
async def score_setup_endpoint(features: dict) -> dict:
    """Score a setup and return decision."""
    hard_gates_pass, gate_reason = apply_hard_gates(features)
    
    feature_tensor = torch.tensor([...], dtype=torch.float32).unsqueeze(0)
    nn_score = model(feature_tensor).item()
    
    decision = make_trading_decision(nn_score, hard_gates_pass)
    
    return decision
```

### 8.2 Inference Latency Target

- **Single setup:** < 1ms
- **Batch (100 setups):** < 50ms

The small model (3.7k params) easily meets these targets on CPU.

---

## Part 9: Design Decisions & Trade-offs

### 9.1 Why 3 Layers?

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| 1 Layer | Fast, simple | Low expressivity | ❌ |
| 2 Layers | Good balance | Still underfit on complex patterns | ❌ |
| 3 Layers | Captures interactions | Not overcomplex | ✅ |
| 4+ Layers | Higher capacity | Overfitting risk, slower | ❌ |

### 9.2 Why ReLU?

- Non-linearity needed to capture feature interactions
- Fast computation (no exp/log like tanh)
- Prevents vanishing gradient problem
- Standard choice for modern networks

### 9.3 Why Sigmoid Output?

- Outputs probability in [0, 1] naturally
- Matches binary classification (win/loss)
- Interpretable as "confidence in setup"

### 9.4 Why Dropout?

- Prevents overfitting on small training sets
- 20% rate is conservative (not too aggressive)
- Ensemble effect: improves generalization

### 9.5 Why Binary Cross-Entropy?

- Designed for binary classification (win/loss)
- Naturally penalizes incorrect predictions
- Stable training with sigmoid output
- Standard loss for probability estimation

---

## Part 10: Training Data Requirements

### Minimum Dataset Size

```
50 trades minimum for Phase 1 prototype
- 40 training (80%)
- 10 validation (20%)

Target for Phase 1 completion:
100+ trades from backtest
```

### Data Quality

- Must have complete feature vectors (no missing values)
- Must have ground truth labels (actual P&L)
- Must span multiple market regimes (bull, bear, consolidation)
- Should avoid look-ahead bias in feature calculation

---

## Part 11: Debugging & Monitoring

### 11.1 Common Issues

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Loss increasing | LR too high | Reduce LR to 0.0005 |
| Loss plateaus | LR too low | Increase LR to 0.002 |
| Training is slow | Batch size too small | Increase to 32 |
| Overfitting (val loss >> train loss) | Model too large | Add dropout or regularization |
| All predictions same value | Dying ReLU | Check feature scaling |

### 11.2 Monitoring Checklist

```
During training:
- [ ] Loss decreasing every epoch
- [ ] Validation loss tracking training loss
- [ ] No NaN in loss history
- [ ] No inf in gradients
- [ ] Checkpoint saving on best val loss
- [ ] Early stopping triggered at right time

After training:
- [ ] Final model loads without error
- [ ] Inference latency < 1ms
- [ ] Output scores in [0, 1]
- [ ] Test accuracy >= 80%
```

---

## Part 12: Future Work (Phase 2+)

- [ ] Add LSTM layers for temporal dependencies
- [ ] Implement feature importance (SHAP values)
- [ ] Add uncertainty estimates (Bayesian NN)
- [ ] Ensemble methods (mixture of models)
- [ ] Hyperparameter tuning (Bayesian optimization)
- [ ] Real-time retraining pipeline
- [ ] Model versioning and A/B testing

---

**Document Version:** 0.1  
**Last Updated:** 2026-04-22  
**Next Review:** 2026-04-27 (after training)
