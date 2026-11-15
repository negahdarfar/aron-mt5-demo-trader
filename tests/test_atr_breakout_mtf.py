import numpy as np
import pandas as pd
import pytest

from aron_trader.atr_breakout_mtf import (
    add_atr_breakout_mtf_features,
    filter_atr_signals_by_bias,
)
from aron_trader.validation import check_prefix_invariance


def test_filter_requires_both_h1_and_h4_to_agree():
    frame = pd.DataFrame({
        "atr_breakout_signal": ["BUY", "BUY", "SELL", "SELL", "HOLD"],
        "h1_bias": [1, 1, -1, 1, 1],
        "h4_bias": [1, -1, -1, -1, 1],
    })
    result = filter_atr_signals_by_bias(frame)
    assert result["atr_breakout_mtf_signal"].tolist() == ["BUY", "HOLD", "SELL", "HOLD", "HOLD"]
    assert result["atr_breakout_mtf_agreement"].tolist() == [True, False, True, False, False]


def test_filter_fails_closed_on_missing_or_neutral_context():
    frame = pd.DataFrame({
        "atr_breakout_signal": ["BUY", "SELL"],
        "h1_bias": [1, -1],
        "h4_bias": [0, np.nan],
    })
    result = filter_atr_signals_by_bias(frame)
    assert result["atr_breakout_mtf_signal"].tolist() == ["HOLD", "HOLD"]


def sample_frame(n=18000):
    t = np.arange(n)
    close = 1.10 + 0.0000005*t + 0.00035*np.sin(t/13) + 0.00012*np.sin(t/71)
    op = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open": op,
        "high": np.maximum(op, close) + 0.00006,
        "low": np.minimum(op, close) - 0.00006,
        "close": close,
        "volume": np.full(n, 100.0),
    })


def test_atr_breakout_mtf_features_are_prefix_invariant():
    frame = sample_frame()
    result = check_prefix_invariance(add_atr_breakout_mtf_features, frame, cutoff=12000)
    assert result["passed"] is True, result


def test_atr_breakout_mtf_features_fail_closed_on_short_history():
    out = add_atr_breakout_mtf_features(sample_frame(100))
    assert set(out["atr_breakout_mtf_signal"].unique()) == {"HOLD"}
