import numpy as np
import pandas as pd
import pytest

from aron_trader.mtf_strategy import _resample_closed, add_mtf_features
from aron_trader.backtest import run_backtest


def trending_m15(days=65):
    n = days * 24 * 4
    t = np.arange(n)
    close = 1.05 + t * 0.000003 + 0.00025 * np.sin(t / 19)
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-07-01", periods=n, freq="15min", tz="UTC"),
        "open": open_, "high": np.maximum(open_, close) + 0.00008,
        "low": np.minimum(open_, close) - 0.00008, "close": close,
        "volume": np.full(n, 100.0),
    })


def test_resample_uses_only_completed_source_bars():
    data = trending_m15(days=2)
    hourly = _resample_closed(data, "1h")
    first = hourly.iloc[0]
    # The right-closed 01:00 bucket contains only the 00:00 source candle.
    assert first["timestamp"] == pd.Timestamp("2026-07-01 00:00:00+00:00")
    assert first["close"] == pytest.approx(data.iloc[0]["close"])


def test_mtf_strategy_has_safe_hold_when_history_is_short():
    result = add_mtf_features(trending_m15(days=2))
    assert (result["mtf_signal"] == "HOLD").all()
    assert set(result["mtf_signal"].unique()) == {"HOLD"}


def test_mtf_strategy_outputs_valid_decisions_and_biases():
    result = add_mtf_features(trending_m15())
    assert {"d1_bias", "h4_bias", "h1_bias", "mtf_signal",
            "mtf_score", "mtf_setup"}.issubset(result.columns)
    assert set(result["mtf_signal"].unique()).issubset({"BUY", "SELL", "HOLD"})
    # Any emitted trade must have strict D1/H4/H1 agreement on the signal bar.
    signals = result[result["mtf_signal"] != "HOLD"]
    for _, row in signals.iterrows():
        expected = 1 if row["mtf_signal"] == "BUY" else -1
        assert row["d1_bias"] == row["h4_bias"] == row["h1_bias"] == expected


def test_backtester_accepts_mtf_strategy():
    result = run_backtest(trending_m15(), strategy="mtf")
    assert result["strategy"] == "mtf"
    assert result["starting_balance"] == 1000
    assert "profit_factor" in result
