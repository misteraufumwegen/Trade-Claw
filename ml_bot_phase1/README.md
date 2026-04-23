# ML Trading Bot — Phase 1: Setup Quality Scorer

**Version:** 0.1  
**Status:** 🟡 Initial Prototype (Training)  
**Owner:** Elon (CTO)  
**Deadline:** 2026-04-27  

---

## 📋 Overview

**Setup Quality Scorer** is a neural network that predicts whether a potential trade setup will be profitable based on 25 features from the Surgical Precision Trading System.

**Architecture:**
- Input: 25 normalized features [0, 1]
- Hidden Layers: 64 → 32 neurons (ReLU + Dropout)
- Output: Probability score [0, 1]

**Decision Gate:** Score ≥ 0.7 → Trade. Score < 0.7 → Reject.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Prepare Data

Create training database from backtest data:

```bash
python scripts/prepare_training_data.py --source backtest_data.json --output data/trades.db
```

This script:
- Loads backtest trades from JSON
- Computes all 25 features per trade
- Populates SQLite database
- Validates feature distributions

### 3. Train Model

```bash
python src/train.py \
    --db-path data/trades.db \
    --epochs 100 \
    --batch-size 16 \
    --learning-rate 0.001 \
    --output-dir checkpoints
```

**Output:**
- `checkpoints/model_best.pt` — Best model checkpoint
- `checkpoints/training_summary.json` — Metrics summary

### 4. Evaluate Model

```bash
python scripts/evaluate_model.py --model checkpoints/model_best.pt --db-path data/trades.db
```

---

## 📁 Project Structure

```
ml_bot_phase1/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── docs/
│   ├── FEATURE_SCHEMA.md         # Feature dictionary (25 features)
│   ├── ARCHITECTURE_SPEC.md      # NN architecture details
│   └── DESIGN_DECISIONS.md       # Trade-offs and rationale
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── setup_scorer.py       # NN model class + metrics
│   ├── data/
│   │   ├── __init__.py
│   │   └── dataset.py            # PyTorch Dataset + DataLoader
│   ├── train.py                  # Training script
│   └── __init__.py
├── scripts/
│   ├── prepare_training_data.py  # Convert backtest → SQLite
│   ├── evaluate_model.py         # Test set evaluation
│   └── inference_example.py      # Single setup scoring
├── tests/
│   ├── unit/
│   │   ├── test_models.py        # Model tests
│   │   └── test_data.py          # Dataset tests
│   └── integration/
│       └── test_training.py      # End-to-end training
└── checkpoints/
    ├── model_best.pt            # Trained model weights
    └── training_summary.json    # Training metrics
```

---

## 🧠 Model Architecture

### Network Diagram

```
Input (25 features)
    ↓
Linear(25 → 64)
ReLU Activation
Dropout(0.2)
    ↓
Linear(64 → 32)
ReLU Activation
Dropout(0.2)
    ↓
Linear(32 → 1)
Sigmoid Activation
    ↓
Output (0.0-1.0 probability)
```

### Key Specs

| Parameter | Value |
|-----------|-------|
| **Total Parameters** | 3,777 |
| **Input Size** | 25 (normalized features) |
| **Hidden Sizes** | 64, 32 |
| **Activation** | ReLU → ReLU → Sigmoid |
| **Dropout Rate** | 0.2 |
| **Loss Function** | Binary Cross-Entropy |
| **Optimizer** | Adam (lr=0.001) |
| **Inference Latency** | < 1ms per setup |

---

## 📊 Feature Schema

**25 Features (all normalized to [0, 1]):**

### Surgical Precision Criteria (7)
1. `structural_level` — Price at S/R, Order Block, or FVG
2. `liquidity_sweep` — Recent liquidity hunt in opposite direction
3. `momentum` — RSI divergence, MACD cross, or volume spike
4. `volume` — Current volume > 1.5x 20-day average
5. `risk_reward` — TP/SL ratio ≥ 1:3 (HARD RULE)
6. `macro_alignment` — Macro regime supports direction
7. `on_chain` — On-chain metrics don't contradict

### Market Context (5)
8. `volatility_regime` — ATR percentile vs 252-day history
9. `trend_strength` — ADX(14) strength
10. `drawdown_pct` — Current underwater % from recent high
11. `time_since_last_trade` — Hours since last trade closed
12. `correlation_spy` — 30-day correlation with SPY

### Risk Metrics (5)
13. `position_size_ratio` — Risk as % of account equity
14. `margin_util` — Margin used / available
15. `max_concurrent_trades` — Current open trades vs limit
16. `losing_streak` — Trades lost in last 10 (cooldown)
17. `profit_distance` — % move needed to hit TP

### Timing & Confluence (3)
18. `mtf_alignment` — Multi-timeframe alignment score
19. `price_action` — Recent bar pattern quality
20. `confluence_count` — # of independent signals converging

**See `docs/FEATURE_SCHEMA.md` for complete details.**

---

## 🎯 Training Process

### Data Pipeline

```
Raw Trade Data (JSON/CSV)
    ↓ [Feature Extraction]
SQLite Database (20 columns: features + outcome)
    ↓ [Dataset + DataLoader]
PyTorch Tensors (batch_size, 25)
    ↓ [Model]
Loss & Gradients
    ↓ [Backprop + Optimizer]
Updated Weights
```

### Training Loop

```python
for epoch in range(num_epochs):
    # Training phase
    for batch_x, batch_y in train_loader:
        y_pred = model(batch_x)
        loss = criterion(y_pred, batch_y)
        loss.backward()
        optimizer.step()
    
    # Validation phase
    val_loss = evaluate(model, val_loader)
    
    # Early stopping check
    if val_loss < best_val_loss:
        save_checkpoint(model)
    else:
        patience_counter += 1
```

### Hyperparameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Epochs | 100 | Stopped early if validation loss plateaus |
| Batch Size | 16 | Balanced for stability + memory |
| Learning Rate | 0.001 | Adam optimizer default |
| Weight Decay | 1e-5 | Light L2 regularization |
| Dropout | 0.2 | 20% of neurons dropped during training |
| Early Stopping | 10 epochs | Stop if no improvement for 10 epochs |
| Train/Val/Test | 80/10/10 | Standard split with random seed |

---

## 📈 Expected Performance

### Target Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| **Accuracy** | ≥ 80% | At threshold 0.7 |
| **Precision** | ≥ 85% | Of trades we take, % are wins |
| **Recall** | ≥ 70% | Of actual wins, % we catch |
| **F1 Score** | ≥ 0.75 | Harmonic mean |
| **Inference Time** | < 1ms | Per single setup |

### Baseline Performance (50+ backtest trades)

From Phase 1 backtest report:
- **Win Rate:** 80.0%
- **Profit Factor:** 12.42x
- **Sharpe Ratio:** 17.26

The NN should learn to predict this 80% win rate on training data and maintain 75%+ on hold-out test set.

---

## 🔧 Usage Examples

### 1. Score a Single Setup

```python
from src.models.setup_scorer import SetupQualityScorer
import torch

# Load model
model = SetupQualityScorer()
checkpoint = torch.load('checkpoints/model_best.pt')
model.load_state_dict(checkpoint['model_state'])

# Features for a trade setup
features = torch.tensor([[
    1.0,    # structural_level
    0.8,    # liquidity_sweep
    0.9,    # momentum
    0.85,   # volume
    1.0,    # risk_reward
    0.8,    # macro_alignment
    0.8,    # on_chain
    0.75,   # volatility
    0.9,    # trend_strength
    0.95,   # drawdown
    1.0,    # time_since_trade
    0.85,   # correlation_spy
    0.9,    # position_size
    0.8,    # margin_util
    1.0,    # concurrent_trades
    1.0,    # losing_streak
    0.95,   # profit_distance
    1.0,    # mtf_alignment
    0.85,   # price_action
    0.8,    # confluence
]], dtype=torch.float32)

# Predict
score = model(features)
print(f"Setup Quality Score: {score.item():.4f}")

if score.item() >= 0.7:
    print("✅ TRADE")
else:
    print("❌ REJECT")
```

### 2. Batch Inference (Backtesting)

```python
# Score 100 setups at once
features = torch.randn(100, 25)
features = torch.clamp(features, 0, 1)

scores, decisions = model.predict(features, threshold=0.7, return_proba=True)
print(f"Scores shape: {scores.shape}")
print(f"Trade rate: {decisions.float().mean():.2%}")
```

### 3. Integration with Trading Bot (Phase 2)

```python
# In FastAPI endpoint
@app.post("/score_setup")
async def score_setup(features: dict) -> dict:
    feature_tensor = torch.tensor([...])
    score = model(feature_tensor).item()
    
    decision = 'TRADE' if score >= 0.7 else 'REJECT'
    return {'score': score, 'decision': decision}
```

---

## 🧪 Testing

### Run Unit Tests

```bash
python -m pytest tests/unit/ -v
```

### Run Integration Tests

```bash
python -m pytest tests/integration/ -v
```

### Test Coverage

```bash
python -m pytest tests/ --cov=src --cov-report=html
```

Target coverage: **≥ 80%**

---

## 📝 Training Output

### Training Summary (JSON)

```json
{
  "completed_epochs": 45,
  "best_val_loss": 0.324,
  "test_loss": 0.361,
  "test_accuracy": 0.82,
  "timestamp": "2026-04-27T14:30:00",
  "hyperparameters": {
    "epochs": 100,
    "batch_size": 16,
    "learning_rate": 0.001,
    "early_stopping_patience": 10
  }
}
```

### Model Checkpoint (PyTorch)

```python
checkpoint = {
    'epoch': 44,
    'model_state': {...},  # Model weights
    'optimizer_state': {...},  # Optimizer state
    'metrics': {
        'final_train_loss': 0.298,
        'final_val_loss': 0.324,
        'best_train_loss': 0.250,
        'best_val_loss': 0.324
    },
    'timestamp': '2026-04-27T14:30:00'
}
```

---

## 🔄 Retraining (Phase 2)

Once Phase 1 prototype is deployed (Phase 2 integration):

### Automatic Retraining Trigger

```python
# Every 100 new live trades:
if num_new_trades >= 100:
    # Add live trades to training database
    FeatureExtractor.insert_trade(...)
    
    # Retrain model
    train(db_path='data/trades.db', epochs=50)
    
    # Validate on test set
    evaluate_model()
    
    # If better: deploy new version
    if new_accuracy > old_accuracy:
        deploy_model('checkpoints/model_best.pt')
```

### Retraining Safety Rules

1. **Never discard old checkpoint** — Keep model v0.1, v0.2, etc.
2. **Test before production** — Validate on hold-out test set
3. **Monitor drift** — Alert if accuracy drops > 5%
4. **Gradual rollout** — A/B test new model against old one

---

## ⚠️ Safety & Constraints

### Hard Gates (Pre-NN Checks)

These rules are enforced BEFORE NN inference:

1. **R/R Ratio ≥ 1:3** — MANDATORY. No exceptions.
2. **Position Size ≤ 5% Account** — Risk management.
3. **Position Limit ≤ 5 Concurrent** — Portfolio concentration.

If any gate fails → Trade rejected immediately (NN never consulted).

### NN Threshold

- **Score ≥ 0.7** → Trade allowed
- **Score < 0.7** → Trade rejected

Threshold is configurable but defaults to 0.7 (chosen during Phase 1 training).

---

## 🐛 Troubleshooting

### Training Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Loss not decreasing | LR too high | Reduce to 0.0005 |
| Loss plateaus | LR too low | Increase to 0.002 |
| Overfitting (val >> train) | Model too large | Add dropout or reduce hidden sizes |
| Out of memory | Batch size too large | Reduce to 8 |

### Data Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No data loaded | Database empty | Run `prepare_training_data.py` |
| Features out of range | Normalization error | Check FEATURE_SCHEMA.md |
| NaN in loss | Invalid features | Replace with 0.5 default |

---

## 📚 Documentation

- **`docs/FEATURE_SCHEMA.md`** — Complete feature dictionary with formulas
- **`docs/ARCHITECTURE_SPEC.md`** — NN architecture, training, inference details
- **`docs/DESIGN_DECISIONS.md`** — Trade-offs and rationale

---

## 🎯 Deliverables (Phase 1)

- ✅ NN Architecture Spec (docs/ARCHITECTURE_SPEC.md)
- ✅ Feature Schema (docs/FEATURE_SCHEMA.md)
- ✅ Data Pipeline (src/data/dataset.py + scripts/)
- ✅ Model Implementation (src/models/setup_scorer.py)
- ✅ Training Script (src/train.py)
- ✅ Unit Tests (tests/unit/)
- ✅ Integration Tests (tests/integration/)
- ✅ README (this file)
- ⏳ Trained Checkpoint v0.1 (checkpoints/model_best.pt)
- ⏳ Training Report (checkpoints/training_summary.json)

---

## 🚀 Next Steps (Phase 2)

1. **Integration with FastAPI Bot** — Embed model in trade decision pipeline
2. **Live Trading** — Start with paper trading, then real money
3. **Monitoring** — Track win rate, drawdown, Sharpe ratio
4. **Retraining** — Automatic retrain every 100 live trades
5. **Feature Drift Detection** — Alert if feature distributions change
6. **Model Versioning** — Keep history of model versions

---

## 📞 Support

- **Owner:** Elon (CTO)
- **Questions:** Reach out in Telegram/Slack
- **Issues:** Create GitHub issue in main repo

---

**Last Updated:** 2026-04-22  
**Next Review:** 2026-04-27 (Phase 1 Complete)
