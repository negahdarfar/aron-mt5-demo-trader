import pandas as pd
import pytest

from aron_trader.walk_forward import monthly_folds, run_walk_forward


def test_monthly_folds_are_contiguous_and_exclusive():
    folds = monthly_folds("2026-05-01", "2026-08-01", 1)
    assert len(folds) == 3
    assert folds[0] == (pd.Timestamp("2026-05-01", tz="UTC"), pd.Timestamp("2026-06-01", tz="UTC"))
    assert folds[0][1] == folds[1][0]
    assert folds[-1][1] == pd.Timestamp("2026-08-01", tz="UTC")


def test_monthly_folds_reject_partial_month_boundaries():
    with pytest.raises(ValueError):
        monthly_folds("2026-05-02", "2026-08-01")
    with pytest.raises(ValueError):
        monthly_folds("2026-05-01", "2026-08-15")


def test_walk_forward_returns_independent_monthly_folds_and_cost_scenarios():
    timestamps = pd.date_range("2026-01-01", "2026-04-01", freq="15min", inclusive="left", tz="UTC")
    close = [1.1 + i * 0.000001 for i in range(len(timestamps))]
    frame = pd.DataFrame({
        "timestamp": timestamps,
        "open": close,
        "high": [x + 0.0002 for x in close],
        "low": [x - 0.0002 for x in close],
        "close": close,
        "volume": [1000.0] * len(close),
    })
    report = run_walk_forward(
        frame, "ema_rsi", "2026-02-01", "2026-04-01",
        cost_multipliers=(0, 1, 2, 3),
    )
    assert report["fold_count"] == 2
    assert len(report["scenarios"]) == 4
    assert len(report["scenarios"][0]["folds"]) == 2
    assert report["scenarios"][3]["spread"] == pytest.approx(0.0003)
    assert report["scenarios"][3]["slippage"] == pytest.approx(0.00015)
    assert all("fold_start" in fold for fold in report["scenarios"][0]["folds"])


def test_trade_diagnostics_break_down_exit_reasons_and_directions():
    from aron_trader.walk_forward import _trade_diagnostics

    report = _trade_diagnostics([
        {"side": "BUY", "pnl": 12.0, "exit_reason": "target", "entry_time": "2026-06-01T08:15:00Z"},
        {"side": "SELL", "pnl": -7.0, "exit_reason": "stop", "entry_time": "2026-06-01T08:45:00Z"},
        {"side": "BUY", "pnl": -3.0, "exit_reason": "max_drawdown_halt", "entry_time": "2026-06-01T14:00:00Z"},
        {"side": "SELL", "pnl": 5.0, "exit_reason": "target", "entry_time": "2026-06-01T14:30:00Z"},
    ])
    assert report["closed_trades"] == 4
    assert report["exit_reasons"]["target"]["count"] == 2
    assert report["exit_reasons"]["max_drawdown_halt"]["net_pnl"] == -3.0
    assert report["side_breakdown"]["BUY"]["count"] == 2
    assert report["entry_hour_utc"]["08:00 UTC"]["count"] == 2
    assert report["entry_hour_utc"]["14:00 UTC"]["net_pnl"] == 2.0
    assert report["average_win"] == pytest.approx(8.5)
    assert report["average_loss"] == pytest.approx(-5.0)
    assert report["largest_loss"] == -7.0
    assert report["max_consecutive_losses"] == 2


def test_trade_diagnostics_handles_empty_trade_log():
    from aron_trader.walk_forward import _trade_diagnostics

    report = _trade_diagnostics([])
    assert report["closed_trades"] == 0
    assert report["exit_reasons"] == {}
    assert report["entry_hour_utc"] == {}
    assert report["max_consecutive_losses"] == 0
