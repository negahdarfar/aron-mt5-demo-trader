import numpy as np
import pandas as pd

from aron_trader.wizards_ensemble import add_wizards_features
from aron_trader.backtest import run_backtest


def sample(days=90):
    n=days*24*4
    t=np.arange(n)
    close=1.05 + t*0.000002 + 0.00035*np.sin(t/17) + 0.00012*np.sin(t/5)
    op=np.r_[close[0],close[:-1]]
    return pd.DataFrame({
        "timestamp":pd.date_range("2026-01-01",periods=n,freq="15min",tz="UTC"),
        "open":op,"high":np.maximum(op,close)+0.00007,
        "low":np.minimum(op,close)-0.00007,"close":close,
        "volume":np.full(n,100.0),
    })


def test_wizards_strategy_has_stable_schema_and_valid_signals():
    out=add_wizards_features(sample())
    assert {"wizards_signal","wizards_regime","wizards_votes","wizards_setup",
            "h1_bias","h4_bias","d1_bias"}.issubset(out.columns)
    assert set(out.wizards_signal.unique()).issubset({"BUY","SELL","HOLD"})
    assert set(out.wizards_regime.unique()).issubset({"trend","range","unknown"})


def test_wizards_no_trade_with_incomplete_history():
    out=add_wizards_features(sample(days=2))
    assert (out.wizards_signal=="HOLD").all()


def test_backtester_accepts_wizards_strategy():
    out=run_backtest(sample(),strategy="wizards")
    assert out["strategy"]=="wizards"
    assert out["starting_balance"]==1000
    assert "profit_factor" in out
