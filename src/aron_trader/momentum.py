"""Standalone RSI/ROC momentum continuation strategy for offline research.

Signals are calculated on completed candles only; the backtester enters at
the next candle open. No look-ahead is used.
"""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, validate_ohlcv


def add_momentum_features(frame: pd.DataFrame, rsi_period: int = 14,
                          roc_period: int = 10, trend_period: int = 200,
                          entry_level: float = 55.0,
                          exit_level: float = 45.0) -> pd.DataFrame:
    if min(rsi_period, roc_period, trend_period) < 2:
        raise ValueError("Momentum periods must be >= 2")
    if not 50 < entry_level < 100 or not 0 < exit_level < 50:
        raise ValueError("Invalid RSI thresholds")
    data = add_indicators(validate_ohlcv(frame), fast=20, slow=50)
    data["momentum_ema"] = data["close"].ewm(span=trend_period, adjust=False).mean()
    data["momentum_rsi"] = data["close"].pipe(
        lambda s: 100 - 100 / (1 + (
            s.diff().clip(lower=0).ewm(alpha=1/rsi_period, adjust=False).mean()
            / (-s.diff().clip(upper=0)).ewm(alpha=1/rsi_period, adjust=False).mean()
        ))
    )
    data["momentum_roc"] = data["close"].pct_change(roc_period) * 100
    data["momentum_signal"] = "HOLD"
    valid = data[["momentum_ema", "momentum_rsi", "momentum_roc", "atr"]].notna().all(axis=1)
    # Entry on RSI momentum crossing its threshold, confirmed by ROC and trend.
    buy = (valid & (data["momentum_rsi"] > entry_level)
           & (data["momentum_rsi"].shift(1) <= entry_level)
           & (data["momentum_roc"] > 0)
           & (data["close"] > data["momentum_ema"]))
    sell = (valid & (data["momentum_rsi"] < exit_level)
            & (data["momentum_rsi"].shift(1) >= exit_level)
            & (data["momentum_roc"] < 0)
            & (data["close"] < data["momentum_ema"]))
    data.loc[buy, "momentum_signal"] = "BUY"
    data.loc[sell, "momentum_signal"] = "SELL"
    return data
