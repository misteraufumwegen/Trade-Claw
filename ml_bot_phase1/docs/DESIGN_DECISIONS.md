# Design Decisions & Trade-offs

**Version:** 0.1  
**Date:** 2026-04-22  
**Owner:** Elon (CTO)

---

## Overview

This document captures the key decisions made during Phase 1 design and the reasoning behind them.

---

## 1. Architecture: Why 3 Layers?

### Decision
**Use a 3-layer fully-connected network (64 → 32 → 1) instead of deeper architectures.**

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Linear (1-layer)** | Very fast, simple | No nonlinearity, poor expressivity | ❌ Too simple |
| **Shallow (2-layer)** | Still simple, fast | Limited feature interaction learning | ❌ Borderline |
| **Medium (3-layer)** | Good balance, captures interactions | Not overcomplicated | ✅ CHOSEN |
| **Deep (4+ layers)** | High capacity | Overfitting risk, slow, hard to tune | ❌ Risky |

### Rationale

1. **Dataset Size:** We start with ~50 trades, growing to ~100. A 3-layer network has 3,777 parameters, which is a safe **10:1 ratio** (samples:parameters). This prevents overfitting while allowing feature interaction learning.

2. **Inference Speed:** Phase 1 goal is <1ms inference. 3 layers with 64→32 neurons stays comfortably below this on CPU.

3. **Interpretability:** More layers = less interpretable. Phase 1 prioritizes understanding what the model learns.

4. **Production Readiness:** A simple, well-tuned 3-layer model is easier to debug, monitor, and maintain than a deep network.

---

## 2. Loss Function: Binary Cross-Entropy (BCE) vs. Alternatives

### Decision
**Use Binary Cross-Entropy (BCE) loss for binary classification (win/loss).**

### Alternatives

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **MSE** | Simple, smooth | Not optimized for classification | ❌ Not ideal |
| **BCE** | Designed for binary probability, penalizes incorrect confidence | Standard, well-understood | ✅ CHOSEN |
| **Focal Loss** | Addresses class imbalance | Complex, may overfit | ❌ Overkill |
| **Hinge Loss** | Margin-based, robust | Not probability-based | ❌ Different paradigm |

### Rationale

1. **Probability Interpretation:** BCE naturally outputs a probability [0, 1]. A score of 0.8 means "80% confident this trade will be profitable." This is interpretable and matches our safety threshold (0.7).

2. **Hard Failure Penalization:** BCE heavily penalizes:
   - Predicting win (0.9) when outcome is loss → Large penalty ✓ (catch failures)
   - Predicting loss (0.1) when outcome is win → Moderate penalty (acceptable misses)

   This asymmetry is **desirable** for risk management—false positives (predicting wins that lose) are worse than false negatives (missing wins).

3. **Gradient Stability:** BCE + Sigmoid combo is a standard pattern with excellent gradient properties (no vanishing gradients).

---

## 3. Threshold: Why 0.7?

### Decision
**Set the trading threshold at 0.7 (hardcoded, not learned).**

### Alternatives

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Threshold = 0.5** | Standard default, simple | Too aggressive, may trade lower-quality setups | ❌ Too loose |
| **Threshold = 0.7** | Conservative, empirically tested | Still trades valid setups | ✅ CHOSEN |
| **Threshold = 0.9** | Ultra-conservative | Too restrictive, misses good trades | ❌ Too tight |
| **Learn threshold** | Optimized per dataset | Overcomplicates Phase 1 | ❌ Future work |

### Rationale

1. **Surgical Precision System Baseline:** The backtest report shows 80% win rate on A+ and A-grade setups (62.5% of all setups). A threshold of 0.7 aims to capture this elite subset while maintaining interpretability.

2. **Early Stopping Safety:** By rejecting scores < 0.7, we're saying "only trade if the model is fairly confident." This is conservative and aligns with Deniz's risk-management philosophy.

3. **Calibration:** If trained properly, a score of 0.7 should correspond to ~70% of those trades being profitable. This is testable and monitorable.

4. **Not Learned:** Unlike some Bayesian approaches, we don't learn the threshold during training. This prevents data leakage and makes threshold changes in production straightforward.

---

## 4. Features: 25 vs. 100+

### Decision
**Use 25 carefully selected features, not automated feature engineering.**

### Rationale

1. **Interpretability:** Each of the 25 features maps to a specific trading concept (S/R level, momentum, volatility, etc.). We can explain why the model recommends a trade.

2. **Data Efficiency:** 25 features × 50-100 trades = manageable. 100+ features would require 1000+ trades to avoid overfitting.

3. **Domain Knowledge:** The Surgical Precision System already identified 7 core criteria. Our features extend this with market context + risk metrics—human-guided, not purely algorithmic.

4. **Monitoring:** Fewer features = easier drift detection. If `f_volatility` distribution changes, we notice.

### Future Work (Phase 2+)
- Polynomial feature combinations
- Automated feature interaction discovery
- Feature importance analysis (SHAP values)

---

## 5. Data: SQLite vs. Alternatives

### Decision
**Use SQLite for training data storage (not CSV, not Parquet, not in-memory).**

### Alternatives

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **CSV** | Simple, portable | No schema, no transactions | ❌ Too simple |
| **SQLite** | Schema, portable, fast, zero config | Limited scalability (OK for Phase 1) | ✅ CHOSEN |
| **PostgreSQL** | Scalable, powerful | Requires server, overkill for Phase 1 | ⏳ Phase 2 |
| **Parquet** | Efficient, columnar | Overkill, harder to update | ❌ Not needed |
| **In-Memory** | Fast | Can't persist, can't audit | ❌ Risky |

### Rationale

1. **Retraining Loop:** Every 100 live trades, we retrain. SQLite allows appending new trades without re-exporting data.

2. **Audit Trail:** Every trade has a timestamp, source (backtest/live), and full feature vector. If something goes wrong, we can audit and replay.

3. **Reproducibility:** Model v0.1 was trained on trades.db as of 2026-04-27. Model v0.2 was trained on updated trades.db. Clear version history.

4. **No Operational Overhead:** SQLite requires no server, no setup, no maintenance. Perfect for Phase 1.

---

## 6. Dropout: 20% vs. Other Rates

### Decision
**Use Dropout(0.2) in both hidden layers.**

### Alternatives

| Rate | Use Case | Verdict |
|------|----------|---------|
| **0.0** | No dropout (classical NN) | ❌ May overfit on small dataset |
| **0.1** | Light regularization | Reasonable, but weak |
| **0.2** | Standard dropout | ✅ CHOSEN (industry default) |
| **0.3** | Strong regularization | Too aggressive, underfits |
| **0.5** | Heavy dropout (RNNs) | ❌ Overkill for fully-connected |

### Rationale

1. **Small Dataset:** With only 50-100 training samples, overfitting is the main risk. 20% dropout reduces overfitting without excessive underfitting.

2. **Empirical:** 0.2 is the most widely used dropout rate in industry. Well-tested, good results.

3. **Not at Output:** We don't use dropout before the sigmoid. Output layer should be deterministic.

---

## 7. Batch Size: 16 vs. 32/8

### Decision
**Use batch_size=16 for training.**

### Trade-offs

| Size | Stability | Memory | Speed | Verdict |
|------|-----------|--------|-------|---------|
| **8** | Very stable | Low | Slow (more updates) | ⏳ Slow |
| **16** | Good | Medium | Balanced | ✅ CHOSEN |
| **32** | Less stable | Higher | Fast | May overfit |

### Rationale

1. **Small Dataset:** With 40 training samples (80% of 50), batch_size=16 means just 2.5 batches per epoch. Smaller batches (8) give more gradient updates; larger (32) are noisier.

2. **Stability:** 16 is a sweet spot—large enough for stable gradients, small enough for frequent updates.

3. **Memory:** 16 samples × 25 features fits easily on CPU or GPU (negligible overhead).

---

## 8. Learning Rate: 0.001 vs. Adaptive Scheduling

### Decision
**Use fixed LR=0.001 (Adam default) with patience-based early stopping, not LR scheduling.**

### Rationale

1. **Simplicity:** Fixed LR is easy to reason about. If loss plateaus, we stop early. If underfitting, we retrain with higher LR (0.002).

2. **Adam Optimizer:** Adam already includes adaptive per-parameter learning rates (via exponential moving averages). No need for additional scheduling.

3. **Phase 1 Constraint:** We retrain every 100 trades, so each training run is short (50 epochs or less). LR scheduling is more useful for 100+ epoch training.

### Future Work
- Implement ReduceLROnPlateau scheduler
- Warmup + cosine annealing for Phase 2

---

## 9. Early Stopping: Patience=10 vs. Other Values

### Decision
**Stop training if validation loss doesn't improve for 10 consecutive epochs.**

### Rationale

1. **Prevents Overfitting:** After 10 epochs of no improvement, the model is likely memorizing noise.

2. **Not Too Greedy:** Patience=3 might stop too early on noisy val loss. Patience=20 might wait too long.

3. **Empirical:** Patience=10 is a standard heuristic for small datasets.

---

## 10. Train/Val/Test Split: 80/10/10

### Decision
**Use 80% training, 10% validation, 10% test.**

### Rationale

1. **Standard Split:** This is the most common split in machine learning.

2. **Small Dataset Adaptation:** With 50 trades:
   - Train: 40 samples
   - Val: 5 samples
   - Test: 5 samples
   
   Tiny val/test sets, but acceptable for Phase 1.

3. **Deterministic:** Use random_seed=42 for reproducibility.

### Phase 2 Consideration
- Implement k-fold cross-validation for more robust estimates
- Stratified split (equal win/loss distribution in each fold)

---

## 11. Hard Gates: Why Pre-NN?

### Decision
**Check hard rules BEFORE NN inference, not learned into the model.**

### Rationale

1. **Safety First:** Hard rules (R/R ≥ 1:3, position size ≤ 5%) are non-negotiable per Deniz's spec. They must never be overridden by NN output.

2. **Interpretability:** If a trade is rejected due to R/R, that's a clear, auditable reason—not a black-box NN vote.

3. **Flexibility:** We can adjust hard gates (e.g., increase position limit) without retraining the model.

---

## 12. What We're NOT Doing (Phase 1 Constraints)

### Ensemble Methods
**Why not:** Adds complexity, requires more tuning, better for Phase 2+.

### LSTM/RNN for Temporal Patterns
**Why not:** Phase 1 is fully-connected. Each trade is independent input. LSTMs need sequence data (price history).

### Attention Mechanisms
**Why not:** Overkill for 25 features. Attention shines with 1000+ dimensional inputs.

### Hyperparameter Tuning (GridSearch/Bayesian)
**Why not:** Takes days to run. Phase 1 uses manual tuning + early stopping.

### Feature Normalization/Standardization
**Why not:** Features are already [0, 1]. No need for additional scaling.

### Class Weights (for Imbalance)
**Why not:** From backtest, win rate is 80%. Mild imbalance, manageable.

### Transfer Learning
**Why not:** No pre-trained models available for trading. Start from scratch.

---

## 13. Testing Strategy: Unit vs. Integration

### Decision
**80% unit tests (model, data pipeline), 20% integration tests (full training run).**

### Rationale

1. **Unit Tests:** Fast, isolated, easy to debug. Test model forward pass, loss computation, metrics.

2. **Integration Tests:** Slow but essential. Verify end-to-end training works without errors.

3. **Avoid Over-Testing:** Don't test PyTorch itself (assume it works). Focus on our code.

---

## 14. Model Persistence: Checkpoint Format

### Decision
**Save full checkpoint (model weights, optimizer state, metrics, hyperparams), not just model.pt.**

### Rationale

1. **Resume Training:** If training crashes at epoch 45, we can resume from the saved optimizer state (momentum, Adam moments).

2. **Reproducibility:** Checkpoint includes all hyperparameters and training metrics. Easy to understand what model_v0.1 is.

3. **Model Versioning:** Each checkpoint is self-contained. v0.1, v0.2, v0.3 can coexist without conflicts.

---

## 15. Scoring Philosophy: Calibration vs. Discrimination

### Decision
**Focus on discrimination (ranking good setups > bad ones), not perfect calibration (0.8 score = 80% win rate exactly).**

### Rationale

1. **Practical Goal:** We need to rank setups. If the model says 0.8 > 0.6, that's the key insight.

2. **Calibration Complexity:** Perfect calibration requires 1000+ samples + careful tuning. Phase 1 has 50.

3. **Threshold Agility:** If scores aren't perfectly calibrated, we just adjust the threshold (e.g., 0.65 instead of 0.7). No retraining needed.

### Phase 2 Work
- Compute calibration plots
- Platt scaling or isotonic regression if needed

---

## 16. Risk of Each Decision

| Decision | Risk | Mitigation |
|----------|------|-----------|
| 3 layers | May underfit on complex patterns | Add layers in Phase 2 if needed |
| 0.7 threshold | May be too strict/loose | Monitor pass rate and adjust empirically |
| Small dataset | High variance in metrics | Use cross-validation in Phase 2 |
| Fixed LR | May get stuck in local minima | Manual LR adjustment between retrains |
| SQLite | Single point of failure | Automatic backups + version control |
| No feature engineering | Miss important interactions | SHAP analysis in Phase 2 |

---

## 17. Open Questions (For Phase 2)

1. **Should we use different thresholds for long vs. short?** (Currently shared)
2. **Should we retrain on ALL 100+ trades or just the newest 100?** (Currently last 100)
3. **How often to retrain—every 100 trades or on a timer?** (Currently event-driven)
4. **Should we version the model or continuously update?** (Currently keep multiple versions)
5. **How to detect model degradation (concept drift)?** (Not implemented yet)

---

## Summary

The Phase 1 design prioritizes:
1. **Simplicity** — easy to understand and debug
2. **Safety** — hard gates + conservative threshold
3. **Reproducibility** — deterministic splits, version control
4. **Monitoring** — clear metrics, interpretable features
5. **Modularity** — drop-in replacement for Phase 2 bot

Trade-offs lean toward **conservative** (may miss some trades) rather than **aggressive** (may take losses). This is intentional for Phase 1 learning.

---

**Last Updated:** 2026-04-22  
**Next Review:** 2026-04-27 (Phase 1 Complete)
