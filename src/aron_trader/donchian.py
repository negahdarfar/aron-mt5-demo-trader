"""Standalone Donchian channel breakout strategy for offline research.

Signals are generated from the prior completed candle. The channel excludes
that signal candle, and the backtester enters at the next candle open.
"""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, validate_ohlcv


def add_donchian_features(frame: pd.DataFrame, entry_period: int = 20,
                          trend_period: int = 50) -> pd.DataFrame:
    if entry_period < 2 or trend_period < 2:
        raise ValueError("Donchian periods must be >= 2")
    data = add_indicators(validate_ohlcv(frame), fast=20, slow=trend_period)
    # Shift the rolling channel so the breakout candle is not part of its own
    # threshold. Backtester reads the previous completed candle's signal.
    data["donchian_upper"] = data["high"].shift(1).rolling(entry_period,
                                                            min_periods=entry_period).max()
    data["donchian_lower"] = data["low"].shift(1).rolling(entry_period,
                                                           min_periods=entry_period).min()
    data["donchian_signal"] = "HOLD"
    valid = data[["donchian_upper", "donchian_lower", "ema_slow", "atr"]].notna().all(axis=1)
    buy = valid & (data["close"] > data["donchian_upper"]) & (data["close"] > data["ema_slow"])
    sell = valid & (data["close"] < data["donchian_lower"]) & (data["close"] < data["ema_slow"])
    data.loc[buy, "donchian_signal"] = "BUY"
    data.loc[sell, "donchian_signal"] = "SELL"
    return data
