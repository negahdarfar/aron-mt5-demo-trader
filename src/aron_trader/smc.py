"""Causal, candle-based SMC research features. No broker execution."""
from __future__ import annotations

import pandas as pd
from .core import validate_ohlcv


def add_smc_features(frame: pd.DataFrame, swing_left: int = 3,
                     swing_right: int = 3, ob_lookback: int = 12) -> pd.DataFrame:
    """Add confirmed swing, BOS, 3-candle FVG and simple OB-zone features.

    A swing is exposed only on its confirmation candle (after swing_right bars),
    avoiding future leakage. BOS uses the most recently confirmed swing.
    A signal requires BOS + same-direction FVG + a prior opposing candle
    identified as a simple order-block zone. This is a research heuristic,
    not a complete ICT/SMC interpretation.
    """
    if swing_left < 1 or swing_right < 1 or ob_lookback < 1:
        raise ValueError("Swing sizes and OB lookback must be positive")
    data = validate_ohlcv(frame)
    n = len(data)
    data["confirmed_swing_high"] = float("nan")
    data["confirmed_swing_low"] = float("nan")
    data["last_swing_high"] = float("nan")
    data["last_swing_low"] = float("nan")
    data["bullish_bos"] = False
    data["bearish_bos"] = False
    data["bullish_fvg"] = False
    data["bearish_fvg"] = False
    data["bullish_ob_low"] = float("nan")
    data["bullish_ob_high"] = float("nan")
    data["bearish_ob_low"] = float("nan")
    data["bearish_ob_high"] = float("nan")
    data["smc_signal"] = "HOLD"

    last_high = float("nan")
    last_low = float("nan")
    bull_ob = (float("nan"), float("nan"))
    bear_ob = (float("nan"), float("nan"))

    for i in range(n):
        pivot = i - swing_right
        if pivot >= swing_left and pivot + swing_right < n:
            left = pivot - swing_left
            right = pivot + swing_right
            highs = data["high"].iloc[left:right + 1]
            lows = data["low"].iloc[left:right + 1]
            ph = float(data["high"].iloc[pivot])
            pl = float(data["low"].iloc[pivot])
            if ph == float(highs.max()) and (highs == ph).sum() == 1:
                last_high = ph
                data.at[i, "confirmed_swing_high"] = ph
            if pl == float(lows.min()) and (lows == pl).sum() == 1:
                last_low = pl
                data.at[i, "confirmed_swing_low"] = pl

        data.at[i, "last_swing_high"] = last_high
        data.at[i, "last_swing_low"] = last_low

        if i >= 2:
            bullish_fvg = float(data["low"].iloc[i]) > float(data["high"].iloc[i - 2])
            bearish_fvg = float(data["high"].iloc[i]) < float(data["low"].iloc[i - 2])
            data.at[i, "bullish_fvg"] = bullish_fvg
            data.at[i, "bearish_fvg"] = bearish_fvg
        else:
            bullish_fvg = bearish_fvg = False

        close = float(data["close"].iloc[i])
        prev_close = float(data["close"].iloc[i - 1]) if i else close
        bullish_bos = pd.notna(last_high) and close > last_high and prev_close <= last_high
        bearish_bos = pd.notna(last_low) and close < last_low and prev_close >= last_low
        data.at[i, "bullish_bos"] = bool(bullish_bos)
        data.at[i, "bearish_bos"] = bool(bearish_bos)

        if bullish_bos:
            start = max(0, i - ob_lookback)
            for j in range(i - 1, start - 1, -1):
                if float(data["close"].iloc[j]) < float(data["open"].iloc[j]):
                    bull_ob = (float(data["low"].iloc[j]), float(data["open"].iloc[j]))
                    break
        if bearish_bos:
            start = max(0, i - ob_lookback)
            for j in range(i - 1, start - 1, -1):
                if float(data["close"].iloc[j]) > float(data["open"].iloc[j]):
                    bear_ob = (float(data["open"].iloc[j]), float(data["high"].iloc[j]))
                    break

        if pd.notna(bull_ob[0]):
            data.at[i, "bullish_ob_low"], data.at[i, "bullish_ob_high"] = bull_ob
        if pd.notna(bear_ob[0]):
            data.at[i, "bearish_ob_low"], data.at[i, "bearish_ob_high"] = bear_ob

        if bullish_bos and bullish_fvg and pd.notna(bull_ob[0]):
            data.at[i, "smc_signal"] = "BUY"
        elif bearish_bos and bearish_fvg and pd.notna(bear_ob[0]):
            data.at[i, "smc_signal"] = "SELL"

    return data
