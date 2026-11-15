"""Multi-setup opportunity engine; causal closed-candle signals only."""
from __future__ import annotations

import pandas as pd


def _finite(row: pd.Series, *keys: str) -> bool:
    return all(pd.notna(row.get(k)) for k in keys)


def market_regime(row: pd.Series) -> str:
    """Classify trend/range using EMA structure, ADX and normalized ATR."""
    if not _finite(row, "ema_fast", "ema_slow", "adx", "atr", "close"):
        return "unknown"
    if row["close"] <= 0:
        return "unknown"
    if row["adx"] >= 22 and abs(row["ema_fast"] - row["ema_slow"]) / row["close"] >= 0.00015:
        return "trend"
    if row["adx"] <= 18:
        return "range"
    return "transition"


def add_opportunity_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate causal trend/volatility features on completed candles."""
    from .core import add_indicators, validate_ohlcv

    data = add_indicators(validate_ohlcv(frame))
    high, low, close = data["high"], data["low"], data["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(),
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    data["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    data["regime"] = data.apply(market_regime, axis=1)
    data["pro_signal"] = "HOLD"
    data["pro_setup"] = ""
    data["pro_score"] = 0.0

    # Signals are evaluated on each completed candle. The backtester consumes
    # row i-1 and enters at row i open, so no current-bar look-ahead is used.
    for i in range(3, len(data)):
        r = data.iloc[i]
        p = data.iloc[i - 1]
        if not _finite(p, "ema_fast", "ema_slow", "rsi", "atr", "adx"):
            continue
        candidates = []
        regime = p["regime"]
        bullish = p["ema_fast"] > p["ema_slow"]
        bearish = p["ema_fast"] < p["ema_slow"]

        # Trend pullback: trend alignment plus RSI recovery through mid-zone.
        if regime == "trend" and bullish and p["rsi"] >= 50 and data.iloc[i-2]["rsi"] < 50:
            candidates.append(("BUY", "trend_pullback", 3.0))
        if regime == "trend" and bearish and p["rsi"] <= 50 and data.iloc[i-2]["rsi"] > 50:
            candidates.append(("SELL", "trend_pullback", 3.0))

        # Volatility breakout: close outside prior 20-bar range with trend agreement.
        prior = data.iloc[max(0, i-21):i-1]
        if len(prior) >= 19 and regime in ("trend", "transition"):
            if bullish and p["close"] > prior["high"].max():
                candidates.append(("BUY", "range_breakout", 2.5))
            if bearish and p["close"] < prior["low"].min():
                candidates.append(("SELL", "range_breakout", 2.5))

        # Liquidity sweep: pierce prior 10-bar extreme then close back inside.
        prior10 = data.iloc[max(0, i-11):i-1]
        if len(prior10) >= 9:
            if p["low"] < prior10["low"].min() and p["close"] > prior10["low"].min() and p["close"] > p["open"]:
                candidates.append(("BUY", "sellside_sweep_reclaim", 3.0))
            if p["high"] > prior10["high"].max() and p["close"] < prior10["high"].max() and p["close"] < p["open"]:
                candidates.append(("SELL", "buyside_sweep_reject", 3.0))

        # Three-candle fair-value gap with trend direction and displacement.
        if bullish and p["low"] > data.iloc[i-3]["high"] and p["close"] > p["open"] and p["close"]-p["open"] >= 0.5*p["atr"]:
            candidates.append(("BUY", "bullish_fvg_displacement", 2.5))
        if bearish and p["high"] < data.iloc[i-3]["low"] and p["close"] < p["open"] and p["open"]-p["close"] >= 0.5*p["atr"]:
            candidates.append(("SELL", "bearish_fvg_displacement", 2.5))

        # Range mean reversion is permitted only in a low-ADX range regime.
        if regime == "range" and p["rsi"] <= 25:
            candidates.append(("BUY", "range_mean_reversion", 2.0))
        if regime == "range" and p["rsi"] >= 75:
            candidates.append(("SELL", "range_mean_reversion", 2.0))

        # Conflicting directions are rejected rather than arbitrarily selected.
        directions = {c[0] for c in candidates}
        if len(directions) == 1:
            best = sorted(candidates, key=lambda c: c[2], reverse=True)[0]
            data.at[i, "pro_signal"] = best[0]
            data.at[i, "pro_setup"] = best[1]
            data.at[i, "pro_score"] = best[2] + 0.25 * (len(candidates)-1)
    return data
