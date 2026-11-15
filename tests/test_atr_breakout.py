import numpy as np
import pandas as pd
import pytest

from aron_trader.atr_breakout import add_atr_breakout_features
from aron_trader.backtest import run_backtest


def sample_frame(n=1200):
    t = np.arange(n)
    close = 1.10 + 0.000001*t + 0.00035*np.sin(t/13)
    op = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open": op, "high": np.maximum(op, close)+0.00006,
        "low": np.minimum(op, close)-0.00006, "close": close,
        "volume": np.full(n, 100.0),
    })


def test_atr_breakout_feature_schema_and_signal_values():
    out = add_atr_breakout_features(sample_frame())
    assert {"atr_channel_high", "atr_channel_low", "atr_baseline", "atr_breakout_signal"}.issubset(out.columns)
    assert set(out.atr_breakout_signal.unique()).issubset({"BUY", "SELL", "HOLD"})


def test_atr_breakout_backtest_runs_independently():
    result = run_backtest(sample_frame(), strategy="atr_breakout")
    assert result["strategy"] == "atr_breakout"
    assert result["starting_balance"] == 1000
    assert "profit_factor" in result


def test_atr_breakout_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        add_atr_breakout_features(sample_frame(), expansion=1.0)
