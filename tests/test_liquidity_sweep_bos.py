import numpy as np
import pandas as pd
import pytest

from aron_trader.liquidity_sweep_bos import add_liquidity_sweep_bos_features


def frame(n=700):
    x = np.arange(n)
    close = 1.08 + 0.000002*x + 0.0004*np.sin(x/7)
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open": open_,
        "high": np.maximum(open_, close) + 0.0001,
        "low": np.minimum(open_, close) - 0.0001,
        "close": close,
        "volume": 100.0,
    })


def test_liquidity_sweep_bos_feature_schema():
    out = add_liquidity_sweep_bos_features(frame())
    assert {"liquidity_high", "liquidity_low", "internal_high",
            "internal_low", "liquidity_sweep", "lsb_signal"}.issubset(out.columns)
    assert set(out["lsb_signal"].unique()).issubset({"BUY", "SELL", "HOLD"})


def test_liquidity_sweep_bos_prefix_invariance():
    data = frame()
    full = add_liquidity_sweep_bos_features(data)
    cut = 500
    prefix = add_liquidity_sweep_bos_features(data.iloc[:cut].copy())
    pd.testing.assert_series_equal(
        full["lsb_signal"].iloc[:cut].reset_index(drop=True),
        prefix["lsb_signal"].reset_index(drop=True),
    )


@pytest.mark.parametrize("kwargs", [
    {"liquidity_lookback": 4},
    {"structure_lookback": 1},
    {"max_bars_after_sweep": 0},
    {"regime_ema": 1},
])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        add_liquidity_sweep_bos_features(frame(), **kwargs)
