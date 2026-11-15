import pandas as pd
import pytest
from aron_trader.core import add_indicators, position_size, validate_ohlcv
from aron_trader.backtest import run_backtest, _bar_exit


def sample_data(n=140):
    close = [1.10 + i * 0.0002 for i in range(n)]
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="15min"),
        "open": close, "high": [x + 0.0005 for x in close],
        "low": [x - 0.0005 for x in close], "close": close,
        "volume": [1000] * n,
    })


def test_indicators_are_created():
    result = add_indicators(sample_data())
    assert {"ema_fast", "ema_slow", "rsi", "atr"}.issubset(result.columns)
    assert result["atr"].dropna().gt(0).all()


def test_position_size_respects_risk_cash():
    lots = position_size(1000, 0.005, 0.01, 100000)
    assert lots == pytest.approx(0.005)


def test_position_size_rejects_excessive_risk():
    with pytest.raises(ValueError):
        position_size(1000, 0.1, 0.01)


def test_validation_rejects_bad_candles():
    bad = sample_data(5)
    bad.loc[0, "high"] = 0.5
    with pytest.raises(ValueError):
        validate_ohlcv(bad)


def test_backtest_returns_metrics_without_execution():
    result = run_backtest(sample_data())
    assert result["starting_balance"] == 1000
    assert result["ending_balance"] > 0
    assert "trade_log" in result
    assert "profit_factor" in result
    assert "expectancy_per_trade" in result
    assert "max_consecutive_losses" in result
    assert "ending_equity" in result


def test_smc_features_are_causal_and_have_expected_columns():
    from aron_trader.smc import add_smc_features
    data = sample_data(30)
    result = add_smc_features(data, swing_left=2, swing_right=2)
    assert {"bullish_bos", "bearish_bos", "bullish_fvg", "bearish_fvg",
            "bullish_ob_low", "bearish_ob_high", "smc_signal"}.issubset(result.columns)
    # A swing at source index 3 is confirmed after two right-side candles, at index 5.
    pivot_data = sample_data(12)
    pivot_data["high"] = [1, 2, 3, 5, 3, 2, 1, 2, 3, 2, 1, 2]
    pivot_data["low"] = [x - 0.01 for x in pivot_data["high"]]
    pivot_data["open"] = [x - 0.005 for x in pivot_data["high"]]
    pivot_data["close"] = pivot_data["open"]
    pivot_result = add_smc_features(pivot_data, swing_left=2, swing_right=2)
    assert pd.isna(pivot_result.loc[4, "confirmed_swing_high"])
    assert pivot_result.loc[5, "confirmed_swing_high"] == 5


def test_backtest_accepts_smc_strategy():
    result = run_backtest(sample_data(), strategy="smc")
    assert result["strategy"] == "smc"
    assert result["starting_balance"] == 1000


def test_backtest_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        run_backtest(sample_data(), strategy="unknown")



def test_backtest_stop_gap_fills_at_worse_open():
    position = {"side": "BUY", "stop": 1.095, "target": 1.115}
    bar = pd.Series({"open": 1.090, "high": 1.100, "low": 1.085, "close": 1.095})
    price, reason = _bar_exit(position, bar)
    assert price == pytest.approx(1.090)
    assert reason == "stop_gap"


def test_backtest_target_gap_fills_at_open():
    position = {"side": "SELL", "stop": 1.105, "target": 1.085}
    bar = pd.Series({"open": 1.080, "high": 1.090, "low": 1.075, "close": 1.082})
    price, reason = _bar_exit(position, bar)
    assert price == pytest.approx(1.080)
    assert reason == "target_gap"


def test_backtest_rejects_invalid_guardrails():
    with pytest.raises(ValueError):
        run_backtest(sample_data(), max_daily_loss=0)
    with pytest.raises(ValueError):
        run_backtest(sample_data(), max_drawdown_limit=0.8)


def test_load_ohlcv_csv_converts_unix_milliseconds(tmp_path):
    from aron_trader.cli import load_ohlcv_csv
    path = tmp_path / "dukascopy.csv"
    pd.DataFrame({
        "timestamp": [1735689600000, 1735690500000],
        "open": [1.1, 1.2], "high": [1.11, 1.21],
        "low": [1.09, 1.19], "close": [1.1, 1.2],
        "volume": [100, 120],
    }).to_csv(path, index=False)
    loaded = load_ohlcv_csv(str(path))
    assert str(loaded.loc[0, "timestamp"]) == "2025-01-01 00:00:00+00:00"


def test_backtest_liquidates_open_position_when_daily_limit_breached(monkeypatch):
    import aron_trader.backtest as backtest_module

    data = sample_data(140)
    # A sharp adverse close breaches the 2% daily equity-loss threshold.
    data.loc[100, ["open", "high", "low", "close"]] = [
        1.10, 1.101, 1.079, 1.080
    ]
    monkeypatch.setattr(backtest_module, "generate_signal", lambda row: "BUY")
    # Isolate the risk-kill-switch behavior from ordinary stop execution.
    monkeypatch.setattr(backtest_module, "_bar_exit", lambda position, bar: (None, None))

    result = backtest_module.run_backtest(
        data, strategy="ema_rsi", max_daily_loss=0.02,
        max_drawdown_limit=0.50
    )
    halted = [trade for trade in result["trade_log"]
              if trade["exit_reason"] == "daily_loss_halt"]
    assert halted
    assert result["daily_loss_limit_hit"] is True
    assert result["open_position_at_end"] is False


def test_backtest_limits_positions_to_requested_month_window(monkeypatch):
    import aron_trader.backtest as backtest_module

    data = sample_data(200)
    monkeypatch.setattr(backtest_module, "generate_signal", lambda row: "BUY")
    monkeypatch.setattr(
        backtest_module, "_bar_exit",
        lambda position, bar: (float(bar["close"]), "test_exit")
    )
    result = backtest_module.run_backtest(
        data, strategy="ema_rsi",
        trade_start="2025-01-02", trade_end="2025-01-03",
        max_daily_loss=0.10, max_drawdown_limit=0.50
    )
    assert result["trade_start"] == "2025-01-02 00:00:00+00:00"
    assert result["trade_end_exclusive"] == "2025-01-03 00:00:00+00:00"
    assert result["trade_log"]
    for trade in result["trade_log"]:
        assert pd.Timestamp("2025-01-02", tz="UTC") <= trade["entry_time"]
        assert trade["entry_time"] < pd.Timestamp("2025-01-03", tz="UTC")
