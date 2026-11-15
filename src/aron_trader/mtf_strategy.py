"""Multi-timeframe trend strategy for M15 research; not a faithful Pine port.

D1 is a directional veto, H4 confirms regime, H1 is the decision timeframe,
and M15 supplies the entry trigger. Higher-timeframe values are only exposed
after their candle has closed (right-labelled resampling + backward asof join).
"""
from __future__ import annotations

import pandas as pd

from .core import add_indicators, validate_ohlcv


def _with_adx(frame: pd.DataFrame) -> pd.DataFrame:
    data = add_indicators(frame)
    high, low, close = data["high"], data["low"], data["close"]
    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([high-low, (high-close.shift()).abs(),
                    (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di).replace(0, float("nan"))
    data["adx"] = dx.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    return data


def _resample_closed(base: pd.DataFrame, rule: str) -> pd.DataFrame:
    indexed = base.set_index("timestamp")
    bars = indexed.resample(rule, label="right", closed="right").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"])
    bars = bars.reset_index()
    return _with_adx(bars)


def add_mtf_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add causal D1/H4/H1 context and M15 entry decisions to M15 OHLCV."""
    base = _with_adx(validate_ohlcv(frame))
    if len(base) < 60:
        # Keep a stable schema; insufficient history safely produces HOLD.
        for col, default in {
            "d1_bias": 0, "h4_bias": 0, "h1_bias": 0,
            "mtf_signal": "HOLD", "mtf_score": 0.0,
            "mtf_setup": "insufficient_history",
        }.items():
            base[col] = default
        return base

    contexts = {}
    for name, rule in (("h1", "1h"), ("h4", "4h"), ("d1", "1D")):
        tf = _resample_closed(base, rule)
        tf[f"{name}_bias"] = 0
        valid = tf[["ema_fast", "ema_slow", "adx"]].notna().all(axis=1)
        bullish = valid & (tf["ema_fast"] > tf["ema_slow"]) & (tf["adx"] >= 16)
        bearish = valid & (tf["ema_fast"] < tf["ema_slow"]) & (tf["adx"] >= 16)
        tf.loc[bullish, f"{name}_bias"] = 1
        tf.loc[bearish, f"{name}_bias"] = -1
        contexts[name] = tf[["timestamp", f"{name}_bias"]]

    result = base.sort_values("timestamp").reset_index(drop=True)
    for name in ("d1", "h4", "h1"):
        result = pd.merge_asof(
            result, contexts[name].sort_values("timestamp"),
            on="timestamp", direction="backward", allow_exact_matches=True,
        )
    result["mtf_signal"] = "HOLD"
    result["mtf_score"] = 0.0
    result["mtf_setup"] = "no_alignment"

    # Strict alignment: D1/H4/H1 agree. M15 must close on the correct side
    # of EMA20 and RSI midline, with a fresh EMA20 reclaim/cross or RSI cross.
    for i in range(2, len(result)):
        p, pp = result.iloc[i-1], result.iloc[i-2]
        if pd.isna(p["atr"]) or pd.isna(p["rsi"]) or pd.isna(p["ema_fast"]):
            continue
        direction = int(p["h1_bias"])
        if direction == 0 or int(p["h4_bias"]) != direction or int(p["d1_bias"]) != direction:
            continue
        if direction == 1:
            aligned = p["close"] > p["ema_fast"] and p["rsi"] >= 50 and p["close"] > p["open"]
            trigger = (pp["close"] <= pp["ema_fast"] < p["close"]
                       or (pp["rsi"] < 50 <= p["rsi"]))
            signal = "BUY"
        else:
            aligned = p["close"] < p["ema_fast"] and p["rsi"] <= 50 and p["close"] < p["open"]
            trigger = (pp["close"] >= pp["ema_fast"] > p["close"]
                       or (pp["rsi"] > 50 >= p["rsi"]))
            signal = "SELL"
        if aligned and trigger:
            result.at[i, "mtf_signal"] = signal
            result.at[i, "mtf_score"] = 100.0
            result.at[i, "mtf_setup"] = "D1_H4_H1_aligned_M15_trigger"
    return result
