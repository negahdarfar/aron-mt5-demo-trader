"""Standalone ATR volatility-expansion breakout strategy (offline research)."""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, validate_ohlcv


def add_atr_breakout_features(frame: pd.DataFrame, channel_period: int = 20,
                              atr_period: int = 14, volatility_period: int = 50,
                              expansion: float = 1.10) -> pd.DataFrame:
    """Break prior range only when current ATR exceeds its prior ATR baseline."""
    if min(channel_period, atr_period, volatility_period) < 2:
        raise ValueError("All ATR breakout periods must be >= 2")
    if expansion <= 1.0:
        raise ValueError("expansion must be > 1")
    data = add_indicators(validate_ohlcv(frame))
    # Both range and volatility baseline are shifted: the signal candle cannot
    # change its own breakout threshold or volatility reference.
    data["atr_channel_high"] = data["high"].shift(1).rolling(
        channel_period, min_periods=channel_period
    ).max()
    data["atr_channel_low"] = data["low"].shift(1).rolling(
        channel_period, min_periods=channel_period
    ).min()
    data["atr_baseline"] = data["atr"].shift(1).rolling(
        volatility_period, min_periods=volatility_period
    ).mean()
    data["atr_breakout_signal"] = "HOLD"
    valid = data[["atr_channel_high", "atr_channel_low", "atr_baseline", "atr"]].notna().all(axis=1)
    volatile = valid & (data["atr"] > data["atr_baseline"] * expansion)
    buy = volatile & (data["close"] > data["atr_channel_high"])
    sell = volatile & (data["close"] < data["atr_channel_low"])
    data.loc[buy, "atr_breakout_signal"] = "BUY"
    data.loc[sell, "atr_breakout_signal"] = "SELL"
    return data
