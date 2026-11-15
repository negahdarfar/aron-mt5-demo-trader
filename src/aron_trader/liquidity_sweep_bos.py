"""Causal liquidity-sweep followed by market-structure break (MSS/BOS).

A sweep must pierce the prior rolling liquidity level and close back inside.
The setup is armed for a bounded number of completed candles. Entry signal is
only emitted after a later close breaks the prior internal swing in the same
direction and agrees with the EMA regime. Backtester fills next candle open.
Research heuristic only; not a complete ICT/SMC interpretation.
"""
from __future__ import annotations

import pandas as pd

from .core import add_indicators, validate_ohlcv


def add_liquidity_sweep_bos_features(
    frame: pd.DataFrame,
    liquidity_lookback: int = 20,
    structure_lookback: int = 5,
    max_bars_after_sweep: int = 8,
    regime_ema: int = 200,
) -> pd.DataFrame:
    if liquidity_lookback < 5 or structure_lookback < 2:
        raise ValueError("liquidity_lookback must be >= 5 and structure_lookback >= 2")
    if max_bars_after_sweep < 1 or regime_ema < 2:
        raise ValueError("max_bars_after_sweep and regime_ema must be >= 1 and >= 2")

    data = add_indicators(validate_ohlcv(frame))
    data["lsb_regime_ema"] = data["close"].ewm(
        span=regime_ema, adjust=False, min_periods=regime_ema
    ).mean()
    data["liquidity_high"] = data["high"].shift(1).rolling(
        liquidity_lookback, min_periods=liquidity_lookback
    ).max()
    data["liquidity_low"] = data["low"].shift(1).rolling(
        liquidity_lookback, min_periods=liquidity_lookback
    ).min()
    data["internal_high"] = data["high"].shift(1).rolling(
        structure_lookback, min_periods=structure_lookback
    ).max()
    data["internal_low"] = data["low"].shift(1).rolling(
        structure_lookback, min_periods=structure_lookback
    ).min()
    data["liquidity_sweep"] = "NONE"
    data["lsb_signal"] = "HOLD"

    armed_side: str | None = None
    armed_at: int | None = None
    sweep_extreme: float | None = None
    signal_col = data.columns.get_loc("lsb_signal")
    sweep_col = data.columns.get_loc("liquidity_sweep")

    for i in range(len(data)):
        row = data.iloc[i]
        required = ("liquidity_high", "liquidity_low", "internal_high",
                    "internal_low", "lsb_regime_ema")
        if any(pd.isna(row[c]) for c in required):
            continue

        if armed_at is not None and i - armed_at > max_bars_after_sweep:
            armed_side, armed_at, sweep_extreme = None, None, None

        # A later candle must break structure; the sweep candle cannot also
        # trigger BOS. The current candle is compared only with prior bars.
        if armed_side == "BUY" and i > armed_at:
            invalid = float(row["close"]) < float(sweep_extreme)
            bos = (float(row["close"]) > float(row["internal_high"])
                   and float(row["close"]) > float(row["lsb_regime_ema"]))
            if invalid:
                armed_side, armed_at, sweep_extreme = None, None, None
            elif bos:
                data.iat[i, signal_col] = "BUY"
                armed_side, armed_at, sweep_extreme = None, None, None
                continue
        elif armed_side == "SELL" and i > armed_at:
            invalid = float(row["close"]) > float(sweep_extreme)
            bos = (float(row["close"]) < float(row["internal_low"])
                   and float(row["close"]) < float(row["lsb_regime_ema"]))
            if invalid:
                armed_side, armed_at, sweep_extreme = None, None, None
            elif bos:
                data.iat[i, signal_col] = "SELL"
                armed_side, armed_at, sweep_extreme = None, None, None
                continue

        if armed_side is None:
            bullish_sweep = (
                float(row["low"]) < float(row["liquidity_low"])
                and float(row["close"]) > float(row["liquidity_low"])
                and float(row["close"]) > float(row["open"])
            )
            bearish_sweep = (
                float(row["high"]) > float(row["liquidity_high"])
                and float(row["close"]) < float(row["liquidity_high"])
                and float(row["close"]) < float(row["open"])
            )
            if bullish_sweep:
                data.iat[i, sweep_col] = "SELL_SIDE"
                armed_side, armed_at, sweep_extreme = "BUY", i, float(row["low"])
            elif bearish_sweep:
                data.iat[i, sweep_col] = "BUY_SIDE"
                armed_side, armed_at, sweep_extreme = "SELL", i, float(row["high"])

    return data
