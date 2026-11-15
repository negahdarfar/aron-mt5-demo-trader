import numpy as np
import pandas as pd
import pytest

from aron_trader.trend_pullback import add_trend_pullback_features
from aron_trader.backtest import run_backtest


def sample_frame(n=1400):
    t = np.arange(n)
    close = 1.08 + 0.000004*t + 0.00045*np.sin(t/11) + 0.00018*np.sin(t/3)
    op = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open": op, "high": np.maximum(op, close)+0.00010,
        "low": np.minimum(op, close)-0.00010, "close": close,
        "volume": np.full(n, 100.0),
    })


def test_trend_pullback_feature_schema_and_values():
    out = add_trend_pullback_features(sample_frame())
    assert {"pullback_ema_regime", "pullback_recent_low",
            "pullback_recent_high", "trend_pullback_signal"}.issubset(out.columns)
    assert set(out.trend_pullback_signal.unique()).issubset({"BUY", "SELL", "HOLD"})


def test_trend_pullback_backtest_runs_independently():
    result = run_backtest(sample_frame(), strategy="trend_pullback")
    assert result["strategy"] == "trend_pullback"
    assert result["starting_balance"] == 1000
    assert "profit_factor" in result


def test_trend_pullback_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        add_trend_pullback_features(sample_frame(), pullback_lookback=0)
