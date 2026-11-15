"""Standalone EMA trend-following crossover strategy (offline research)."""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, validate_ohlcv


def add_ema_trend_features(frame: pd.DataFrame, fast: int = 20,
                           slow: int = 50, regime: int = 200) -> pd.DataFrame:
    if fast < 2 or slow <= fast or regime <= slow:
        raise ValueError("Require 2 <= fast < slow < regime")
    data = add_indicators(validate_ohlcv(frame), fast=fast, slow=slow)
    data["ema_regime"] = data["close"].ewm(
        span=regime, adjust=False, min_periods=regime
    ).mean()
    data["ema_trend_signal"] = "HOLD"

    # Cross is evaluated on the just-closed candle; entry occurs at next open.
    cross_up = ((data["ema_fast"] > data["ema_slow"]) &
                (data["ema_fast"].shift(1) <= data["ema_slow"].shift(1)))
    cross_down = ((data["ema_fast"] < data["ema_slow"]) &
                  (data["ema_fast"].shift(1) >= data["ema_slow"].shift(1)))
    valid = data[["ema_fast", "ema_slow", "ema_regime", "atr"]].notna().all(axis=1)
    buy = valid & cross_up & (data["close"] > data["ema_regime"])
    sell = valid & cross_down & (data["close"] < data["ema_regime"])
    data.loc[buy, "ema_trend_signal"] = "BUY"
    data.loc[sell, "ema_trend_signal"] = "SELL"
    return data
