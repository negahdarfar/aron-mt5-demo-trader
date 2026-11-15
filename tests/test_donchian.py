import numpy as np
import pandas as pd

from aron_trader.donchian import add_donchian_features
from aron_trader.backtest import run_backtest


def frame(n=800):
    t=np.arange(n)
    close=1.10 + t*0.00001 + 0.0002*np.sin(t/11)
    op=np.r_[close[0],close[:-1]]
    return pd.DataFrame({
        "timestamp":pd.date_range("2025-01-01",periods=n,freq="15min",tz="UTC"),
        "open":op,"high":np.maximum(op,close)+0.00005,
        "low":np.minimum(op,close)-0.00005,"close":close,
        "volume":np.full(n,100.0),
    })


def test_donchian_has_valid_schema_and_signals():
    out=add_donchian_features(frame())
    assert {"donchian_upper","donchian_lower","donchian_signal"}.issubset(out.columns)
    assert set(out.donchian_signal.unique()).issubset({"BUY","SELL","HOLD"})


def test_donchian_backtest_runs_independently():
    result=run_backtest(frame(),strategy="donchian")
    assert result["strategy"]=="donchian"
    assert result["starting_balance"]==1000
    assert "profit_factor" in result
