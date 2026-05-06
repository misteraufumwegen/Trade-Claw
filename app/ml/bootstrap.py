"""
Bootstrap pipeline (Phase 3).

This is the *cold-start* solution to the ML chicken-and-egg problem: we need
labelled trades to train, but the model is supposed to filter trades — so we
synthesise the initial training set from historical market data instead.

Pipeline:

    yfinance OHLCV  →  generate candidate setups across history
                       (long & short, naive structural-break detection)
                  →  compute the same 20-feature vector the live ML gate uses
                  →  simulate each setup forward N candles to label WIN/LOSS
                  →  emit (X, y) for the trainer

The bootstrap is intentionally *boring*. It does not try to beat the market;
it gives the NN a meaningful prior so cold-start filtering isn't 50/50. The
real signal will come from live retraining once outcomes accumulate.

Important caveats:
- Many of the 7-criteria features (liquidity_sweep, etc.) cannot be inferred
  from OHLCV alone; we use heuristic proxies (volatility breakouts, RSI,
  volume vs 20-day average, weekly trend). The proxy is documented at each
  call site so future-you knows which features are signal-y vs noise.
- Forex/Metals data via yfinance is end-of-day. For intraday training data
  you'd need a paid feed; out of scope here.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd  # noqa: F401


# Default symbol universe — covers the user's stated markets:
#   forex (EUR/USD, GBP/USD, USD/JPY), crypto (BTC, ETH), metals (GLD, SLV)
DEFAULT_SYMBOLS: tuple[str, ...] = (
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "BTC-USD",
    "ETH-USD",
    "GLD",
    "SLV",
)


@dataclass
class BootstrapResult:
    samples: int
    wins: int
    losses: int
    symbols_processed: list[str]
    time_range: tuple[str, str]


def fetch_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame | None:
    """Fetch end-of-day OHLCV via yfinance.

    Returns ``None`` (and logs) when the call fails so the caller can skip
    the symbol gracefully.
    """
    try:
        import yfinance as yf  # noqa: PLC0415

        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            logger.warning("No data returned for %s", symbol)
            return None
        df = df.dropna()
        return df
    except Exception:  # noqa: BLE001
        logger.exception("yfinance failed for %s", symbol)
        return None


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    import pandas as pd  # noqa: PLC0415

    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def _generate_setups(
    df: pd.DataFrame,
    symbol: str,
    *,
    min_lookback: int = 30,
    forward_window: int = 10,
    risk_atr_mult: float = 1.5,
    reward_atr_mult: float = 4.5,  # 1:3 R/R
) -> Iterable[dict]:
    """Walk the price history and emit candidate setups with labels.

    Heuristic: when the close breaks above the 20-day high (long) or below
    the 20-day low (short), spawn a setup with SL = entry ∓ 1.5*ATR and
    TP = entry ± 4.5*ATR (i.e. 1:3 R/R). Forward-test 10 candles to label.
    """
    import pandas as pd  # noqa: PLC0415

    if len(df) < min_lookback + forward_window + 5:
        return

    df = df.copy()
    df["ATR"] = _atr(df)
    df["RSI"] = _rsi(df["Close"])
    df["VolMA"] = df["Volume"].rolling(20).mean() if "Volume" in df else 1.0
    df["WeekTrend"] = df["Close"].pct_change(5).rolling(5).mean()
    df["20dHigh"] = df["High"].rolling(20).max().shift(1)
    df["20dLow"] = df["Low"].rolling(20).min().shift(1)

    for idx in range(min_lookback, len(df) - forward_window):
        row = df.iloc[idx]
        atr = row["ATR"]
        if not (atr and atr > 0):
            continue

        close = float(row["Close"])
        rsi = float(row["RSI"]) if not pd.isna(row["RSI"]) else 50.0
        vol = float(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 0.0
        vol_ma = float(row["VolMA"]) if not pd.isna(row["VolMA"]) else max(vol, 1.0)
        week = float(row["WeekTrend"]) if not pd.isna(row["WeekTrend"]) else 0.0

        # Long setup: 20-day breakout
        if close > float(row["20dHigh"]) and rsi > 50:
            entry = close
            sl = entry - risk_atr_mult * atr
            tp = entry + reward_atr_mult * atr
            yield from _maybe_emit(
                df,
                idx,
                symbol,
                side="BUY",
                entry=entry,
                sl=sl,
                tp=tp,
                rsi=rsi,
                vol=vol,
                vol_ma=vol_ma,
                week=week,
                atr=atr,
                forward_window=forward_window,
            )
        # Short setup: 20-day breakdown
        if close < float(row["20dLow"]) and rsi < 50:
            entry = close
            sl = entry + risk_atr_mult * atr
            tp = entry - reward_atr_mult * atr
            yield from _maybe_emit(
                df,
                idx,
                symbol,
                side="SELL",
                entry=entry,
                sl=sl,
                tp=tp,
                rsi=rsi,
                vol=vol,
                vol_ma=vol_ma,
                week=week,
                atr=atr,
                forward_window=forward_window,
            )


def _maybe_emit(
    df,
    idx,
    symbol,
    *,
    side,
    entry,
    sl,
    tp,
    rsi,
    vol,
    vol_ma,
    week,
    atr,
    forward_window,
):
    """Forward-test the setup and yield a labelled feature row."""

    forward = df.iloc[idx + 1 : idx + 1 + forward_window]
    hit_tp = False
    hit_sl = False
    float(forward.iloc[-1]["Close"])
    for _, fr in forward.iterrows():
        high = float(fr["High"])
        low = float(fr["Low"])
        if side == "BUY":
            if high >= tp:
                hit_tp = True
                break
            if low <= sl:
                hit_sl = True
                break
        else:
            if low <= tp:
                hit_tp = True
                break
            if high >= sl:
                hit_sl = True
                break

    if not (hit_tp or hit_sl):
        # Skip ambiguous setups — keep the dataset clean
        return

    label = 1.0 if hit_tp else 0.0

    # Heuristic proxies for the 20-feature vector. Most map naturally;
    # macro/on-chain are weak proxies but kept for schema compatibility.
    # All values are clipped to [0, 1].
    def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
        if x != x:
            return 0.5
        return max(lo, min(hi, x))

    rr = abs(tp - entry) / max(abs(entry - sl), 1e-9)
    week_aligned = (week > 0 and side == "BUY") or (week < 0 and side == "SELL")

    features = [
        # Surgical-precision proxies
        _clip(1.0 if (hit_tp or hit_sl) else 0.0),  # f_structural_level
        _clip(1.0 if abs(rsi - 50) > 10 else 0.0),  # f_liquidity_sweep proxy
        _clip(abs(rsi - 50) / 50.0),  # f_momentum
        _clip(vol / max(vol_ma, 1e-9) / 2.0),  # f_volume (saturates at 2x avg)
        _clip(rr / 3.0),  # f_risk_reward
        _clip(1.0 if week_aligned else 0.0),  # f_macro_alignment
        0.5,  # f_on_chain (no signal here)
        _clip(atr / max(entry, 1e-9) / 0.05),  # f_volatility (5% saturates)
        _clip(0.5 + week * 5.0),  # f_trend_strength
        0.0,  # f_drawdown (assume fresh)
        0.5,  # f_time_since_trade
        0.5,  # f_correlation_spy
        0.5,  # f_position_size
        0.5,  # f_margin_util
        1.0,  # f_concurrent_trades
        1.0,  # f_losing_streak
        _clip(rr / 5.0),  # f_profit_distance
        _clip(1.0 if week_aligned else 0.0),  # f_mtf_alignment
        _clip(abs(rsi - 50) / 50.0),  # f_price_action
        _clip(((1.0 if week_aligned else 0.0) + min(rr / 3, 1)) / 2),  # f_confluence
    ]

    yield {
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "label": label,
        "features": features,
    }


def build_synthetic_dataset(
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    period: str = "2y",
) -> tuple[list[list[float]], list[float], list[str]]:
    """Build a labelled dataset across multiple symbols.

    Returns (X, y, symbols_processed).
    """
    X: list[list[float]] = []
    y: list[float] = []
    processed: list[str] = []
    for symbol in symbols:
        df = fetch_ohlcv(symbol, period=period)
        if df is None:
            continue
        before = len(X)
        for setup in _generate_setups(df, symbol):
            X.append(setup["features"])
            y.append(setup["label"])
        added = len(X) - before
        if added > 0:
            processed.append(symbol)
            logger.info("Bootstrap: %s → %d setups", symbol, added)
    return X, y, processed


def bootstrap(
    db,
    *,
    symbols: Iterable[str] | None = None,
    period: str = "2y",
    epochs: int = 200,
    learning_rate: float = 1e-3,
    activate: bool = True,
) -> dict:
    """One-shot bootstrap: fetch data, label, train, save checkpoint."""
    from .trainer import train_from_outcomes  # noqa: PLC0415

    syms = list(symbols) if symbols else list(DEFAULT_SYMBOLS)
    started = datetime.utcnow()
    X, y, processed = build_synthetic_dataset(syms, period=period)
    if not X:
        raise RuntimeError("Bootstrap produced no samples; check yfinance access.")

    wins = int(sum(y))
    losses = len(y) - wins
    logger.info(
        "Bootstrap dataset: %d samples (%d wins / %d losses) across %s",
        len(X),
        wins,
        losses,
        processed,
    )

    # Reuse the live trainer with synthetic-only data (no outcomes table read)
    train_from_outcomes(
        db,
        epochs=epochs,
        learning_rate=learning_rate,
        activate=activate,
        extra_data=(X, y),
    ) if False else None  # train_from_outcomes requires DB; we go direct.

    # Direct training path that does not require outcomes table
    return _direct_train(
        X,
        y,
        processed,
        epochs=epochs,
        learning_rate=learning_rate,
        activate=activate,
        started=started,
    )


def _direct_train(
    X: list[list[float]],
    y: list[float],
    processed: list[str],
    *,
    epochs: int,
    learning_rate: float,
    activate: bool,
    started: datetime,
) -> dict:
    import json as _json  # noqa: PLC0415

    import torch  # noqa: PLC0415
    import torch.nn as nn  # noqa: PLC0415

    from ml_bot_phase1.src.models.setup_scorer import SetupQualityScorer  # noqa: PLC0415

    from .service import _default_checkpoint_path, initialize_model  # noqa: PLC0415

    Xt = torch.tensor(X, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

    wins = int(sum(y))
    losses = len(y) - wins
    pos_weight = torch.tensor([losses / max(wins, 1)], dtype=torch.float32)
    criterion = nn.BCELoss()
    model = SetupQualityScorer(input_size=Xt.shape[1], device="cpu")
    optim = torch.optim.Adam(model.parameters(), lr=learning_rate)

    final_loss = 0.0
    final_acc = 0.0
    model.train()
    for _epoch in range(epochs):
        optim.zero_grad()
        preds = model(Xt)
        weights = torch.where(yt > 0.5, pos_weight, torch.ones_like(yt))
        loss = (criterion(preds, yt) * weights).mean()
        loss.backward()
        optim.step()
        final_loss = float(loss.item())
        with torch.no_grad():
            final_acc = float(((preds >= 0.5).float() == yt).float().mean().item())

    timestamp = started.strftime("%Y%m%dT%H%M%S")
    ckpt_dir = _default_checkpoint_path().parent
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / f"scorer_bootstrap_{timestamp}.pt"
    torch.save({"state_dict": model.state_dict()}, ckpt_path)

    metadata = {
        "kind": "bootstrap",
        "samples": len(X),
        "wins": wins,
        "losses": losses,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "final_loss": final_loss,
        "final_accuracy": final_acc,
        "started_at": started.isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "symbols": processed,
    }
    (ckpt_dir / f"scorer_bootstrap_{timestamp}.json").write_text(_json.dumps(metadata, indent=2))

    activated = False
    if activate:
        active_path = _default_checkpoint_path()
        active_path.write_bytes(ckpt_path.read_bytes())
        initialize_model(active_path)
        activated = True

    return {
        "samples": len(X),
        "wins": wins,
        "losses": losses,
        "symbols_processed": processed,
        "epochs": epochs,
        "final_loss": final_loss,
        "final_accuracy": final_acc,
        "checkpoint_path": str(ckpt_path),
        "activated": activated,
        "started_at": started.isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
    }
