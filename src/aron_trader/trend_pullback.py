"""Trend pullback continuation with EMA structure and candle confirmation."""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, validate_ohlcv


def add_trend_pullback_features(frame: pd.DataFrame, pullback_lookback: int = 3,
                                fast: int = 20, trend: int = 50,
                                regime: int = 200) -> pd.DataFrame:
    """Signal after a recent EMA20 touch and a completed reversal candle.

    Long: EMA50 > EMA200, one of the previous N lows touched/breached EMA20,
    and the current candle closes bullish above EMA20.
    Short: exact inverse. Backtest enters at the next candle open.
    """
    if pullback_lookback < 1 or fast < 2 or trend <= fast or regime <= trend:
        raise ValueError("Require lookback >= 1 and 2 <= fast < trend < regime")
    data = add_indicators(validate_ohlcv(frame), fast=fast, slow=trend)
    data["pullback_ema_regime"] = data["close"].ewm(
        span=regime, adjust=False, min_periods=regime
    ).mean()
    data["pullback_recent_low"] = data["low"].shift(1).rolling(
        pullback_lookback, min_periods=pullback_lookback
    ).min()
    data["pullback_recent_high"] = data["high"].shift(1).rolling(
        pullback_lookback, min_periods=pullback_lookback
    ).max()
    data["trend_pullback_signal"] = "HOLD"
    valid = data[["ema_fast", "ema_slow", "pullback_ema_regime",
                  "pullback_recent_low", "pullback_recent_high", "atr"]].notna().all(axis=1)
    uptrend = (data["ema_slow"] > data["pullback_ema_regime"])
    downtrend = (data["ema_slow"] < data["pullback_ema_regime"])
    bullish_reclaim = (data["close"] > data["open"]) & (data["close"] > data["ema_fast"])
    bearish_reclaim = (data["close"] < data["open"]) & (data["close"] < data["ema_fast"])
    long_pullback = data["pullback_recent_low"] <= data["ema_fast"].shift(1)
    short_pullback = data["pullback_recent_high"] >= data["ema_fast"].shift(1)
    buy = valid & uptrend & long_pullback & bullish_reclaim
    sell = valid & downtrend & short_pullback & bearish_reclaim
    data.loc[buy, "trend_pullback_signal"] = "BUY"
    data.loc[sell, "trend_pullback_signal"] = "SELL"
    return data
