# Feature Schema — ML Trading Bot Phase 1

**Version:** 0.1  
**Date:** 2026-04-22  
**Owner:** Elon (CTO)  
**Status:** Complete Specification

---

## Overview

The NN input layer receives **25 normalized features** describing a potential trade setup. These features are derived from:

1. **Surgical Precision System Criteria** (7 factors scored 0-1)
2. **Market Context** (volatility, trend, regime)
3. **Risk Metrics** (position size, R:R ratio, account health)
4. **Timing & Confluence** (multi-timeframe alignment)

The model outputs a **Setup-Quality-Score (0.0-1.0)** used for final gating decision:
- Score **≥ 0.7** → Trade executed
- Score **< 0.7** → Trade rejected (safety brake)

---

## Part 1: Feature Dictionary

### Category A: Surgical Precision Criteria (7 features)

These are the core setup evaluation rules from Backtest Phase 1.

#### A1: `structural_level_score` (float, 0-1)
**Definition:** Price is at significant S/R, Order Block, or Fair Value Gap  
**Source:** Price location relative to historical levels, order flow analysis  
**Calculation:**
- 1.0 = Price **exactly** at identified S/R (±0.5% tolerance)
- 0.8 = Price at Order Block (recent institutional concentration)
- 0.6 = Price near FVG (Fair Value Gap)
- 0.3 = Price at weak support/resistance
- 0.0 = No structural confluence

**Normalization:** Already 0-1 scale. No additional scaling needed.

#### A2: `liquidity_sweep_score` (float, 0-1)
**Definition:** Price previously swept (hunted) liquidity in opposite direction  
**Source:** 20-200 bar lookback for recent swing lows/highs  
**Calculation:**
- 1.0 = Clear liquidity sweep 50-100 bars ago
- 0.8 = Sweep within last 40 bars
- 0.6 = Weak sweep pattern visible
- 0.3 = Potential sweep but unclear
- 0.0 = No sweep pattern

**Normalization:** Already 0-1 scale.

#### A3: `momentum_score` (float, 0-1)
**Definition:** Momentum divergence, MACD cross, or volume spike present  
**Source:** RSI(14), MACD(12,26,9), Volume analysis  
**Calculation:**
- 1.0 = RSI divergence + MACD cross + volume spike all confirmed
- 0.8 = Any two conditions met
- 0.6 = One condition (e.g., RSI div only)
- 0.3 = Weak momentum signal
- 0.0 = No momentum signal

**Normalization:** Already 0-1 scale.

#### A4: `volume_score` (float, 0-1)
**Definition:** Bar/candle volume exceeds 1.5x 20-bar average  
**Source:** Historical volume data  
**Calculation:**
```
volume_ratio = current_volume / SMA(volume, 20)
score = min(volume_ratio / 1.5, 1.0)  # Capped at 1.0
```
- 1.0 = volume > 3x average
- 0.8 = volume 2.0-3.0x average
- 0.6 = volume 1.5-2.0x average
- 0.3 = volume 1.0-1.5x average
- 0.0 = volume < 1.0x average

**Normalization:** Already 0-1 scale (capped).

#### A5: `risk_reward_score` (float, 0-1)
**Definition:** Trade setup meets or exceeds 1:3 R:R ratio (HARD RULE)  
**Source:** Entry, Stop-Loss, Take-Profit levels  
**Calculation:**
```
rrr = abs(TP - Entry) / abs(SL - Entry)
if rrr >= 3.0:
    score = 1.0  # HARD RULE MET
elif rrr >= 2.0:
    score = 0.8
elif rrr >= 1.5:
    score = 0.6
elif rrr >= 1.0:
    score = 0.3
else:
    score = 0.0  # REJECT (violation)
```

**Critical:** If `rrr < 1.0`, this is a **HARD FAILURE** and trade must be rejected (no NN output can override).

**Normalization:** Already 0-1 scale.

#### A6: `macro_alignment_score` (float, 0-1)
**Definition:** Macro regime supports trade direction (trend, Fed policy, etc.)  
**Source:** Daily/weekly trend, macro events in database  
**Calculation:**
- 1.0 = Strong macro tailwind (e.g., Fed pivot bullish for BTC)
- 0.8 = Macro neutral but local trend aligned
- 0.5 = Mixed macro signals
- 0.3 = Weak macro headwind
- 0.0 = Strong macro contradiction

**Normalization:** Already 0-1 scale.

#### A7: `on_chain_score` (float, 0-1)
**Definition:** On-chain metrics (if available) don't contradict setup  
**Source:** Glassnode metrics (whale transfers, active addresses, etc.)  
**Calculation:**
- 1.0 = On-chain metrics strongly support direction
- 0.8 = Neutral on-chain, no contradiction
- 0.5 = Mixed on-chain signals
- 0.3 = Weak on-chain contradiction
- 0.0 = Clear on-chain contradiction

**Note:** In Phase 1, if on-chain data unavailable, default to 0.8 (neutral).

**Normalization:** Already 0-1 scale.

---

### Category B: Market Context (5 features)

These describe the broader market environment.

#### B1: `volatility_regime` (float, 0-1)
**Definition:** Current volatility percentile vs. 252-day history  
**Source:** ATR(14) or Historical Volatility  
**Calculation:**
```
current_atr = ATR(close, 14)
atr_50th_percentile = percentile(ATR_history_252, 50)
atr_95th_percentile = percentile(ATR_history_252, 95)

if current_atr >= atr_95th_percentile:
    score = 1.0  # Very high volatility
elif current_atr >= atr_50th_percentile:
    score = 0.7  # Above normal
else:
    score = 0.4  # Below normal
```

**Normalization:** 0-1 scale (mapped from percentile).

#### B2: `trend_strength` (float, 0-1)
**Definition:** ADX(14) strength of current trend  
**Source:** Average Directional Index  
**Calculation:**
```
adx_value = ADX(close, high, low, 14)
if adx_value >= 40:
    score = 1.0
elif adx_value >= 25:
    score = 0.8
elif adx_value >= 15:
    score = 0.6
else:
    score = 0.3
```

**Normalization:** 0-1 scale.

#### B3: `current_drawdown_pct` (float, 0-1, INVERTED)
**Definition:** Current underwater percentage from recent high  
**Source:** Account equity tracking  
**Calculation:**
```
current_equity = account.balance
recent_high = max(equity_history_last_20_trades)
drawdown = (current_equity - recent_high) / recent_high

# Invert so 0 = deep drawdown, 1 = at equity high
score = max(0, 1.0 + drawdown)  # e.g., -20% DD → 0.8 score
```

**Normalization:** Clamped to [0, 1].

#### B4: `time_since_last_trade_hours` (float, 0-1)
**Definition:** Hours since last trade closed (cooldown signal)  
**Source:** Trade history  
**Calculation:**
```
hours_elapsed = (now - last_trade_close_time) / 3600
# Normalize: 0 trades in last 24h = 1.0, trades every hour = 0.0
if hours_elapsed >= 24:
    score = 1.0
elif hours_elapsed >= 1:
    score = hours_elapsed / 24
else:
    score = 0.0
```

**Purpose:** Prevent clustering trades; space them out. High score = more rest since last trade.

**Normalization:** 0-1 scale.

#### B5: `correlation_with_spy` (float, 0-1)
**Definition:** 30-day rolling correlation between BTC and SPY  
**Source:** Price data  
**Calculation:**
```
correlation = pearson_correlation(BTC_returns_30d, SPY_returns_30d)
# Correlation from -1 to +1, but we care about absolute moves
# High correlation = risk concentration (bad)
# Low correlation = diversification (good)
if abs(correlation) <= 0.3:
    score = 1.0  # Decorrelated
elif abs(correlation) <= 0.6:
    score = 0.7
else:
    score = 0.4  # Highly correlated
```

**Normalization:** 0-1 scale.

---

### Category C: Risk Metrics (5 features)

Describe position sizing and account health constraints.

#### C1: `position_size_ratio` (float, 0-1)
**Definition:** Proposed position risk as % of account  
**Source:** Position sizing: risk_amount / account_equity  
**Calculation:**
```
# Typically 2% risk per trade (hard limit per Deniz design)
proposed_risk_pct = (abs(SL - Entry) * position_qty) / account_equity

if proposed_risk_pct <= 0.01:  # <=1% risk (conservative)
    score = 1.0
elif proposed_risk_pct <= 0.02:  # <=2% risk (normal)
    score = 0.9
elif proposed_risk_pct <= 0.03:  # <=3% risk (aggressive)
    score = 0.7
elif proposed_risk_pct <= 0.05:  # <=5% risk (very aggressive)
    score = 0.4
else:
    score = 0.0  # REJECT (violation)
```

**Normalization:** 0-1 scale.

#### C2: `margin_utilization_pct` (float, 0-1, INVERTED)
**Definition:** Current margin used / available  
**Source:** Broker account data  
**Calculation:**
```
utilization = margin_used / margin_available
# High utilization = less breathing room = risky
if utilization <= 0.3:
    score = 1.0  # Plenty of margin
elif utilization <= 0.5:
    score = 0.8
elif utilization <= 0.7:
    score = 0.6
else:
    score = 0.3  # Tight margin
```

**Normalization:** Inverted from utilization (high utilization = low score).

#### C3: `max_concurrent_trades` (float, 0-1)
**Definition:** Current # open trades vs. max allowed  
**Source:** Portfolio state  
**Calculation:**
```
max_allowed = 5  # Design decision
current = len(open_positions)

if current < max_allowed:
    score = 1.0 - (current / max_allowed)
else:
    score = 0.0  # REJECT (position limit)
```

**Normalization:** 0-1 scale.

#### C4: `losing_streak_cooldown` (float, 0-1)
**Definition:** Prevent over-trading after losing streak  
**Source:** Trade history (last 10 trades)  
**Calculation:**
```
recent_trades = trades[-10:]
losses = sum(1 for t in recent_trades if t.pnl < 0)

if losses <= 1:
    score = 1.0  # No significant streak
elif losses <= 3:
    score = 0.7
elif losses <= 5:
    score = 0.4
else:
    score = 0.0  # After 5+ losses, pause (mental reset)
```

**Purpose:** Psychological protection against revenge trading.

**Normalization:** 0-1 scale.

#### C5: `profit_target_distance` (float, 0-1)
**Definition:** How far TP is from current price (opportunity score)  
**Source:** Price levels  
**Calculation:**
```
tp_distance_pct = abs(TP - current_price) / current_price
# Trades with TP far away (high potential) are favorable
# But not so far that they're unrealistic

if tp_distance_pct >= 0.10:  # >10% move needed
    score = 1.0
elif tp_distance_pct >= 0.05:
    score = 0.9
elif tp_distance_pct >= 0.02:
    score = 0.7
else:
    score = 0.3  # TP very close (scalp-like, lower confidence)
```

**Normalization:** 0-1 scale.

---

### Category D: Timing & Confluence (3 features)

Multi-timeframe alignment and market structure.

#### D1: `mtf_alignment_score` (float, 0-1)
**Definition:** Setup aligned across multiple timeframes (1h, 4h, 1d)  
**Source:** Technical analysis across TFs  
**Calculation:**
- 1.0 = All 3 TFs (1h, 4h, 1d) aligned
- 0.9 = 2/3 TFs aligned + one neutral
- 0.7 = 2/3 TFs aligned + one against
- 0.5 = 1 TF aligned, 2 against
- 0.3 = All TFs against

**Purpose:** Higher TF confluence = higher conviction.

**Normalization:** 0-1 scale.

#### D2: `recent_price_action_score` (float, 0-1)
**Definition:** Last 5 bars show clean price action without false signals  
**Source:** Bar patterns (pin bars, inside bars, strong closes)  
**Calculation:**
- 1.0 = 4-5 bars of clean directional moves (no whipsaws)
- 0.8 = 3 bars clean, 1-2 noise
- 0.6 = Mixed price action
- 0.3 = Choppy, indecisive
- 0.0 = Whipsaw/reversal pattern

**Normalization:** 0-1 scale.

#### D3: `confluence_count` (float, 0-1, NORMALIZED)
**Definition:** How many independent signals converge  
**Source:** Sum of all signals present  
**Calculation:**
```
signals = [
    'price_at_sr' (binary),
    'momentum_indicator' (binary),
    'volume_spike' (binary),
    'macro_event' (binary),
    'on_chain_signal' (binary)
]
confluence = sum(signals) / len(signals)  # 0-1
```

**Normalization:** Already 0-1 (ratio of signals present).

---

## Part 2: Feature Normalization & Scaling

### Normalization Rules

All **25 features are already on [0, 1] scale** before input to NN.

#### For Categories A, B, C, D:
- Raw values are computed according to specs above
- Results are explicitly clamped to [0.0, 1.0]
- No additional scaling needed (NN expects normalized inputs)

#### Missing Data Handling:
If a feature cannot be computed (e.g., no on-chain data available):
- Use a **neutral default**: 0.5
- Log the missing feature for auditing
- In Phase 2, implement fallback data sources

---

## Part 3: Feature Pipeline (Data Flow)

```
Raw Market Data (OHLCV, on-chain, macro)
        ↓
[Feature Extraction Module]
        ↓
Compute all 25 scores per sample
        ↓
Validation: All values in [0, 1]?
        ↓
[Normalization Layer]
        ↓
PyTorch Tensor (batch_size, 25)
        ↓
NN Model Input
```

### Feature Extraction Order:
1. **Surgical Precision scores** (A1-A7): 7 features
2. **Market context** (B1-B5): 5 features
3. **Risk metrics** (C1-C5): 5 features
4. **Timing/confluence** (D1-D3): 3 features
5. **Total: 25 features**

### Hard Failure Rules:
Before NN inference, check:
```
if A5_risk_reward_score == 0.0:
    return REJECT (do not trade)
if C1_position_size > 0.05:
    return REJECT (do not trade)
if C3_max_concurrent_trades == 0.0:
    return REJECT (position limit)
```

These are **gate conditions** that override any NN output.

---

## Part 4: Training Data Format

### SQLite Schema for Training

```sql
CREATE TABLE trades_training (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20),
    direction VARCHAR(10),  -- 'long', 'short'
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    
    -- Feature Vector (25 floats)
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
    
    -- Target Variable
    outcome INTEGER,  -- 0=LOSS, 1=PROFITABLE (>0R), 2=BREAKEVEN (0R ±1%)
    pnl_r REAL,  -- P&L in multiples of R
    closed_at TIMESTAMP,
    
    -- Metadata
    data_source VARCHAR(50),  -- 'backtest' or 'live'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Target Variable:
```
outcome = {
    0: "LOSS"        # Trade closed at loss (pnl_r < 0)
    1: "WIN"         # Trade closed at profit (pnl_r > 0)
    2: "BREAKEVEN"   # pnl_r between -0.01 and +0.01
}
```

Per Deniz design: **Failure = Closed loss trade**. NN predicts probability that trade will NOT fail (i.e., P(outcome ≠ 0)).

---

## Part 5: Example Feature Vector

```python
example_trade = {
    # Surgical Precision (7)
    'structural_level_score': 1.0,
    'liquidity_sweep_score': 0.8,
    'momentum_score': 0.9,
    'volume_score': 0.85,
    'risk_reward_score': 1.0,
    'macro_alignment_score': 0.8,
    'on_chain_score': 0.8,
    
    # Market Context (5)
    'volatility_regime': 0.75,
    'trend_strength': 0.9,
    'current_drawdown_pct': 0.95,
    'time_since_last_trade_hours': 1.0,
    'correlation_with_spy': 0.85,
    
    # Risk Metrics (5)
    'position_size_ratio': 0.9,
    'margin_utilization_pct': 0.8,
    'max_concurrent_trades': 1.0,
    'losing_streak_cooldown': 1.0,
    'profit_target_distance': 0.95,
    
    # Timing (3)
    'mtf_alignment_score': 1.0,
    'recent_price_action_score': 0.85,
    'confluence_count': 0.8,
}
# Average: 0.90 (high confidence setup, would be allowed)
```

---

## Part 6: Validation Checklist

Before training, validate:
- [ ] All 25 features computed for each sample
- [ ] No NaN or inf values (use 0.5 defaults if missing)
- [ ] All values in [0, 1]
- [ ] Hard failure rules pre-computed (removed from training)
- [ ] Training set balance: not heavily skewed (80% wins OK, >95% = problematic)
- [ ] Feature distribution checked (no single feature always 0 or 1)
- [ ] Backtest data >= 50 trades minimum for initial training
- [ ] Future live trades logged in same schema for retraining

---

## Part 7: Future Enhancements (Phase 2+)

- [ ] Add sentiment features (Twitter, news sentiment)
- [ ] Add more on-chain metrics (whale transfers, exchange flows)
- [ ] Add news event flags (earnings, Fed announcements)
- [ ] Feature importance analysis (SHAP values)
- [ ] Automatic feature engineering (polynomial combinations)
- [ ] Periodic feature drift detection

---

**Document Version:** 0.1  
**Last Updated:** 2026-04-22  
**Next Review:** 2026-04-27 (before training)
