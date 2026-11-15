import numpy as np
import pandas as pd

from aron_trader.ema_trend import add_ema_trend_features
from aron_trader.backtest import run_backtest


def candles(n=900):
    t=np.arange(n)
    close=1.10 + 0.000015*t + 0.0008*np.sin(t/37)
    op=np.r_[close[0],close[:-1]]
    return pd.DataFrame({
        "timestamp":pd.date_range("2025-01-01",periods=n,freq="15min",tz="UTC"),
        "open":op,"high":np.maximum(op,close)+0.00008,
        "low":np.minimum(op,close)-0.00008,"close":close,
        "volume":np.full(n,100.0),
    })


def test_ema_trend_features_and_signal_vocabulary():
    out=add_ema_trend_features(candles())
    assert {"ema_regime","ema_trend_signal","ema_fast","ema_slow","atr"}.issubset(out.columns)
    assert set(out.ema_trend_signal.unique()).issubset({"BUY","SELL","HOLD"})
    assert out.ema_trend_signal.iloc[:200].eq("HOLD").all()


def test_ema_trend_backtest_runs_as_separate_strategy():
    result=run_backtest(candles(),strategy="ema_trend")
    assert result["strategy"]=="ema_trend"
    assert result["starting_balance"]==1000
    assert "profit_factor" in result
