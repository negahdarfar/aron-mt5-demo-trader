import numpy as np
import pandas as pd

from aron_trader.momentum import add_momentum_features
from aron_trader.backtest import run_backtest


def sample_frame(n=1200):
    t = np.arange(n)
    close = 1.10 + 0.000002*t + 0.0008*np.sin(t/17) + 0.0003*np.sin(t/5)
    op = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open": op, "high": np.maximum(op, close)+0.00008,
        "low": np.minimum(op, close)-0.00008, "close": close,
        "volume": np.full(n, 100.0),
    })


def test_momentum_features_and_signal_schema():
    out = add_momentum_features(sample_frame())
    assert {"momentum_ema", "momentum_rsi", "momentum_roc", "momentum_signal"}.issubset(out.columns)
    assert set(out.momentum_signal.unique()).issubset({"BUY", "SELL", "HOLD"})


def test_momentum_backtest_runs_independently():
    result = run_backtest(sample_frame(), strategy="momentum")
    assert result["strategy"] == "momentum"
    assert result["starting_balance"] == 1000
    assert "profit_factor" in result


def test_momentum_rejects_bad_thresholds():
    import pytest
    with pytest.raises(ValueError):
        add_momentum_features(sample_frame(), entry_level=45)
