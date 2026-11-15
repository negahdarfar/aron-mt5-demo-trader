"""Regime-switching 'Wizards' ensemble for research.

Inspired by publicly described strategy families (systematic trend following,
momentum, chart breakouts, and range mean reversion). It does NOT reproduce
any trader's proprietary rules or returns. Fundamental/macro/event models are
not simulated because this OHLCV dataset contains no such inputs.
"""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, validate_ohlcv


def _adx(data: pd.DataFrame) -> pd.Series:
    high, low, close = data["high"], data["low"], data["close"]
    up, down = high.diff(), -low.diff()
    plus = up.where((up > down) & (up > 0), 0.0)
    minus = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([high-low, (high-close.shift()).abs(),
                    (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    pdi = 100 * plus.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr
    mdi = 100 * minus.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr
    dx = 100 * (pdi-mdi).abs() / (pdi+mdi).replace(0, float("nan"))
    return dx.ewm(alpha=1/14, adjust=False, min_periods=14).mean()


def _closed_context(base: pd.DataFrame, rule: str, name: str) -> pd.DataFrame:
    tf = (base.set_index("timestamp")
          .resample(rule, label="right", closed="left")
          .agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"})
          .dropna().reset_index())
    tf = add_indicators(tf)
    tf["adx"] = _adx(tf)
    tf[f"{name}_bias"] = 0
    valid = tf[["ema_fast","ema_slow","adx"]].notna().all(axis=1)
    tf.loc[valid & (tf.ema_fast > tf.ema_slow) & (tf.adx >= 16), f"{name}_bias"] = 1
    tf.loc[valid & (tf.ema_fast < tf.ema_slow) & (tf.adx >= 16), f"{name}_bias"] = -1
    return tf[["timestamp",f"{name}_bias"]]


def add_wizards_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = add_indicators(validate_ohlcv(frame))
    data["adx"] = _adx(data)
    data["wizards_signal"] = "HOLD"
    data["wizards_regime"] = "unknown"
    data["wizards_votes"] = 0
    data["wizards_setup"] = ""

    for name, rule in (("h1","1h"),("h4","4h"),("d1","1D")):
        ctx = _closed_context(data, rule, name)
        data = pd.merge_asof(data.sort_values("timestamp"),
                             ctx.sort_values("timestamp"), on="timestamp",
                             direction="backward", allow_exact_matches=True)

    # Use only completed prior bars. The backtester enters at the next bar open.
    for i in range(60, len(data)):
        p = data.iloc[i-1]
        if pd.isna(p["adx"]) or pd.isna(p["atr"]) or pd.isna(p["rsi"]):
            continue
        adx = float(p["adx"])
        direction = int(p["h1_bias"])
        if direction == 0 or int(p["h4_bias"]) != direction or int(p["d1_bias"]) != direction:
            continue

        if adx >= 22:
            regime = "trend"
            votes = []
            # Turtle-style Donchian breakout (exclude signal bar).
            hist = data.iloc[max(0, i-21):i-1]
            if len(hist) >= 19:
                if direction == 1 and p["close"] > hist["high"].max(): votes.append(("BUY","donchian_breakout"))
                if direction == -1 and p["close"] < hist["low"].min(): votes.append(("SELL","donchian_breakout"))
            # Trend pullback / momentum resumption.
            prev = data.iloc[i-2]
            if direction == 1 and p["close"] > p["ema_fast"] and p["rsi"] >= 50 and prev["rsi"] < 50:
                votes.append(("BUY","ema_rsi_momentum"))
            if direction == -1 and p["close"] < p["ema_fast"] and p["rsi"] <= 50 and prev["rsi"] > 50:
                votes.append(("SELL","ema_rsi_momentum"))
            # Volatility expansion with directional candle.
            if direction == 1 and p["close"] > p["open"] and (p["close"]-p["open"]) >= 0.8*p["atr"]:
                votes.append(("BUY","atr_displacement"))
            if direction == -1 and p["close"] < p["open"] and (p["open"]-p["close"]) >= 0.8*p["atr"]:
                votes.append(("SELL","atr_displacement"))
            wanted = "BUY" if direction == 1 else "SELL"
            count = sum(v[0] == wanted for v in votes)
            if count >= 2:
                data.at[i,"wizards_signal"] = wanted
                data.at[i,"wizards_regime"] = regime
                data.at[i,"wizards_votes"] = count
                data.at[i,"wizards_setup"] = "+".join(v[1] for v in votes if v[0] == wanted)
        elif adx <= 18:
            # Mean reversion is intentionally disabled unless all HTF trends are
            # neutral: a strong higher-timeframe bias is not faded.
            if any(int(p[k]) != 0 for k in ("d1_bias","h4_bias","h1_bias")):
                continue
            prev = data.iloc[i-2]
            buy = p["rsi"] > 30 and prev["rsi"] <= 30 and p["close"] > p["open"]
            sell = p["rsi"] < 70 and prev["rsi"] >= 70 and p["close"] < p["open"]
            if buy or sell:
                data.at[i,"wizards_signal"] = "BUY" if buy else "SELL"
                data.at[i,"wizards_regime"] = "range"
                data.at[i,"wizards_votes"] = 2
                data.at[i,"wizards_setup"] = "range_reversion_rsi_reclaim"
    return data
