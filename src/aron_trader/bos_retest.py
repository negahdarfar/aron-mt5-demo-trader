"""Market-structure break and retest strategy (offline research only)."""
from __future__ import annotations
import pandas as pd
from .core import add_indicators, validate_ohlcv

def add_bos_retest_features(frame: pd.DataFrame, swing_lookback: int = 5,
                            retest_bars: int = 8, fast: int = 50,
                            regime: int = 200, tolerance_atr: float = 0.15) -> pd.DataFrame:
    """Break prior rolling swing, then enter on a confirmed retest.

    Break levels use only preceding candles. A breakout arms one level for at
    most retest_bars completed candles. A reclaim generates a signal; the
    backtester fills at the following open.
    """
    if swing_lookback < 2 or retest_bars < 1 or fast < 2 or regime <= fast:
        raise ValueError("Require lookback >= 2, retest_bars >= 1 and 2 <= fast < regime")
    if tolerance_atr < 0 or tolerance_atr > 1:
        raise ValueError("tolerance_atr must be between 0 and 1")
    data = add_indicators(validate_ohlcv(frame), fast=20, slow=fast)
    data["bos_regime_ema"] = data["close"].ewm(span=regime, adjust=False, min_periods=regime).mean()
    data["bos_swing_high"] = data["high"].shift(1).rolling(swing_lookback, min_periods=swing_lookback).max()
    data["bos_swing_low"] = data["low"].shift(1).rolling(swing_lookback, min_periods=swing_lookback).min()
    data["bos_retest_signal"] = "HOLD"
    armed_side, armed_level, armed_at = None, None, None
    signal_col = data.columns.get_loc("bos_retest_signal")
    for i in range(len(data)):
        row = data.iloc[i]
        if pd.isna(row["bos_swing_high"]) or pd.isna(row["bos_swing_low"]) or pd.isna(row["atr"]) or pd.isna(row["bos_regime_ema"]):
            continue
        if armed_at is not None and i - armed_at > retest_bars:
            armed_side, armed_level, armed_at = None, None, None
        if armed_side == "BUY":
            retest = (row["low"] <= armed_level + row["atr"] * tolerance_atr
                      and row["close"] > armed_level and row["close"] > row["open"]
                      and row["close"] > row["bos_regime_ema"])
            if retest:
                data.iat[i, signal_col] = "BUY"
                armed_side, armed_level, armed_at = None, None, None
                continue
        elif armed_side == "SELL":
            retest = (row["high"] >= armed_level - row["atr"] * tolerance_atr
                      and row["close"] < armed_level and row["close"] < row["open"]
                      and row["close"] < row["bos_regime_ema"])
            if retest:
                data.iat[i, signal_col] = "SELL"
                armed_side, armed_level, armed_at = None, None, None
                continue
        if armed_side is None:
            if row["close"] > row["bos_swing_high"] and row["close"] > row["bos_regime_ema"]:
                armed_side, armed_level, armed_at = "BUY", float(row["bos_swing_high"]), i
            elif row["close"] < row["bos_swing_low"] and row["close"] < row["bos_regime_ema"]:
                armed_side, armed_level, armed_at = "SELL", float(row["bos_swing_low"]), i
    return data
