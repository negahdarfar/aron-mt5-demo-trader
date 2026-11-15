import numpy as np
import pandas as pd
import pytest
from aron_trader.bos_retest import add_bos_retest_features
from aron_trader.backtest import run_backtest

def sample_frame(n=1600):
    t = np.arange(n)
    close = 1.08 + 0.000004*t + 0.0005*np.sin(t/9) + 0.0002*np.sin(t/3)
    op = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open": op, "high": np.maximum(op, close)+0.00012,
        "low": np.minimum(op, close)-0.00012, "close": close,
        "volume": np.full(n, 100.0),
    })

def test_bos_retest_feature_schema_and_values():
    out = add_bos_retest_features(sample_frame())
    assert {"bos_regime_ema", "bos_swing_high", "bos_swing_low", "bos_retest_signal"}.issubset(out.columns)
    assert set(out.bos_retest_signal.unique()).issubset({"BUY", "SELL", "HOLD"})

def test_bos_retest_backtest_runs_independently():
    result = run_backtest(sample_frame(), strategy="bos_retest")
    assert result["strategy"] == "bos_retest"
    assert result["starting_balance"] == 1000
    assert "profit_factor" in result

def test_bos_retest_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        add_bos_retest_features(sample_frame(), swing_lookback=1)
