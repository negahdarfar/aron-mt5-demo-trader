"""ATR breakout gated by fully closed H1 and H4 trend context.

This is a separate experimental strategy. The original atr_breakout rules are
left unchanged. Higher-timeframe features are calculated by mtf_strategy using
right-labelled, left-closed resampling and backward as-of joins, so a signal
bar only sees H1/H4 candles whose close timestamp is no later than that M15
bar's timestamp. This deliberately conservative alignment can lag one M15 bar.
"""
from __future__ import annotations

import pandas as pd

from .atr_breakout import add_atr_breakout_features
from .mtf_strategy import add_mtf_features


def filter_atr_signals_by_bias(data: pd.DataFrame) -> pd.DataFrame:
    """Keep ATR BUY/SELL only when both completed H1 and H4 biases agree."""
    required = {"atr_breakout_signal", "h1_bias", "h4_bias"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing MTF filter columns: {sorted(missing)}")
    result = data.copy()
    raw = result["atr_breakout_signal"].astype(str)
    h1 = pd.to_numeric(result["h1_bias"], errors="coerce")
    h4 = pd.to_numeric(result["h4_bias"], errors="coerce")
    buy_ok = (raw == "BUY") & (h1 == 1) & (h4 == 1)
    sell_ok = (raw == "SELL") & (h1 == -1) & (h4 == -1)
    result["atr_breakout_mtf_signal"] = "HOLD"
    result.loc[buy_ok | sell_ok, "atr_breakout_mtf_signal"] = raw.loc[buy_ok | sell_ok]
    result["atr_breakout_mtf_agreement"] = buy_ok | sell_ok
    return result


def add_atr_breakout_mtf_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build ATR breakout signals and gate them with closed H1/H4 trend."""
    atr = add_atr_breakout_features(frame)
    mtf = add_mtf_features(frame)[["timestamp", "h1_bias", "h4_bias"]]
    merged = atr.merge(mtf, on="timestamp", how="left", validate="one_to_one")
    return filter_atr_signals_by_bias(merged)
