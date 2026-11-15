"""ML4T-inspired causal validation helpers for time-series features."""
from __future__ import annotations

from collections.abc import Callable, Sequence

import pandas as pd


def check_prefix_invariance(
    feature_builder: Callable[[pd.DataFrame], pd.DataFrame],
    frame: pd.DataFrame,
    cutoff: int,
    columns: Sequence[str] | None = None,
) -> dict:
    """Check that appending future rows does not rewrite already-known features.

    The feature builder is run once on the full data and once on the prefix
    ending at cutoff. The overlapping rows must match. This detects a broad
    class of lookahead leaks, including centered windows and full-sample
    normalization. It is a diagnostic, not a proof of causal correctness.
    """
    if cutoff < 2 or cutoff >= len(frame):
        raise ValueError("cutoff must be between 2 and len(frame)-1")

    full = feature_builder(frame.copy()).reset_index(drop=True)
    prefix = feature_builder(frame.iloc[:cutoff].copy()).reset_index(drop=True)
    if len(full) < cutoff or len(prefix) != cutoff:
        raise ValueError("Feature builder must preserve input row count")

    selected = list(columns) if columns is not None else [
        name for name in prefix.columns if name in full.columns
    ]
    missing = sorted(set(selected).difference(prefix.columns).union(
        set(selected).difference(full.columns)
    ))
    if missing:
        raise ValueError(f"Requested feature columns are missing: {missing}")

    try:
        pd.testing.assert_frame_equal(
            full.loc[:cutoff - 1, selected].reset_index(drop=True),
            prefix.loc[:cutoff - 1, selected].reset_index(drop=True),
            check_dtype=False,
            check_exact=False,
            rtol=1e-10,
            atol=1e-12,
        )
    except AssertionError as exc:
        return {
            "passed": False,
            "checked_rows": cutoff,
            "checked_columns": selected,
            "reason": str(exc).splitlines()[0],
        }

    return {
        "passed": True,
        "checked_rows": cutoff,
        "checked_columns": selected,
        "reason": "Prefix outputs are unchanged when future rows are appended.",
    }
