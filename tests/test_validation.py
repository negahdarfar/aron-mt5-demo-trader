import pandas as pd
import pytest

from aron_trader.validation import check_prefix_invariance


def sample_frame(n=20):
    return pd.DataFrame({"close": [100.0 + i for i in range(n)]})


def causal_builder(frame):
    result = frame.copy()
    result["past_mean"] = result["close"].rolling(3, min_periods=1).mean()
    return result


def leaking_builder(frame):
    result = frame.copy()
    result["future_max"] = result["close"].iloc[::-1].cummax().iloc[::-1]
    return result


def test_prefix_invariance_accepts_causal_rolling_feature():
    result = check_prefix_invariance(causal_builder, sample_frame(), cutoff=12)
    assert result["passed"] is True
    assert result["checked_rows"] == 12


def test_prefix_invariance_detects_future_information_leak():
    result = check_prefix_invariance(leaking_builder, sample_frame(), cutoff=12)
    assert result["passed"] is False
    assert "future_max" in result["checked_columns"]


def test_prefix_invariance_rejects_invalid_cutoff():
    with pytest.raises(ValueError):
        check_prefix_invariance(causal_builder, sample_frame(), cutoff=20)
