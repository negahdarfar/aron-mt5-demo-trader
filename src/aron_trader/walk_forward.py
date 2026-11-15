"""Monthly rolling out-of-sample validation for fixed trading rules."""
from __future__ import annotations

from collections.abc import Sequence
import pandas as pd

from .backtest import run_backtest


def monthly_folds(start: str, end: str, fold_months: int = 1) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    start_ts = pd.to_datetime(start, utc=True)
    end_ts = pd.to_datetime(end, utc=True)
    if end_ts <= start_ts:
        raise ValueError("end must be after start")
    if fold_months < 1:
        raise ValueError("fold_months must be at least 1")
    if start_ts.day != 1 or start_ts != start_ts.normalize():
        raise ValueError("start must be the first day of a month at 00:00 UTC")
    if end_ts.day != 1 or end_ts != end_ts.normalize():
        raise ValueError("end must be the first day of a month at 00:00 UTC")

    boundaries = [start_ts]
    cursor = start_ts
    while cursor < end_ts:
        cursor = cursor + pd.DateOffset(months=fold_months)
        boundaries.append(min(cursor, end_ts))
    if boundaries[-1] != end_ts:
        raise ValueError("end must align to a complete monthly fold")
    return list(zip(boundaries[:-1], boundaries[1:]))


def run_walk_forward(
    frame: pd.DataFrame,
    strategy: str,
    test_start: str,
    test_end: str,
    *,
    starting_balance: float = 1000.0,
    risk_fraction: float = 0.005,
    base_spread: float = 0.0001,
    base_slippage: float = 0.00005,
    cost_multipliers: Sequence[float] = (0.0, 1.0, 2.0, 3.0),
    fold_months: int = 1,
) -> dict:
    """Evaluate unchanged rules in sequential monthly test folds.

    Each fold is independently initialized at starting_balance. Data is
    truncated at that fold's exclusive end so later candles cannot leak into
    the feature calculation. This is fixed-rule rolling OOS validation, not
    parameter optimization or a continuously compounded portfolio simulation.
    """
    if base_spread < 0 or base_slippage < 0:
        raise ValueError("base costs cannot be negative")
    multipliers = tuple(float(x) for x in cost_multipliers)
    if not multipliers or any(x < 0 for x in multipliers):
        raise ValueError("cost multipliers must be a non-empty sequence of non-negative values")

    data = frame.copy()
    if "timestamp" not in data:
        raise ValueError("frame must contain timestamp")
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="raise")
    data = data.sort_values("timestamp").reset_index(drop=True)

    folds = monthly_folds(test_start, test_end, fold_months)
    scenarios = []
    for multiplier in multipliers:
        fold_results = []
        for fold_start, fold_end in folds:
            available = data.loc[data["timestamp"] < fold_end].copy()
            if available.empty or not (available["timestamp"] < fold_start).any():
                raise ValueError(f"Insufficient warm-up data before {fold_start}")
            result = run_backtest(
                available,
                starting_balance=starting_balance,
                risk_fraction=risk_fraction,
                spread=base_spread * multiplier,
                slippage=base_slippage * multiplier,
                strategy=strategy,
                trade_start=fold_start.isoformat(),
                trade_end=fold_end.isoformat(),
            )
            result.pop("trade_log", None)
            fold_results.append({
                "fold_start": fold_start.isoformat(),
                "fold_end_exclusive": fold_end.isoformat(),
                **result,
            })

        trades = sum(x["trades"] for x in fold_results)
        gross_profit = sum(x["gross_profit"] for x in fold_results)
        gross_loss = sum(x["gross_loss"] for x in fold_results)
        net_profit = sum(x["net_profit"] for x in fold_results)
        scenarios.append({
            "cost_multiplier": multiplier,
            "spread": base_spread * multiplier,
            "slippage": base_slippage * multiplier,
            "folds": fold_results,
            "total_trades": trades,
            "total_wins": sum(x["wins"] for x in fold_results),
            "win_rate": sum(x["wins"] for x in fold_results) / trades if trades else 0.0,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_profit_sum_of_independent_folds": net_profit,
            "profit_factor": gross_profit / gross_loss if gross_loss else (None if not gross_profit else "infinity"),
            "expectancy_per_trade": net_profit / trades if trades else 0.0,
            "worst_fold_drawdown": max((x["max_drawdown"] for x in fold_results), default=0.0),
            "daily_loss_limit_hit_any_fold": any(x["daily_loss_limit_hit"] for x in fold_results),
            "max_drawdown_limit_hit_any_fold": any(x["max_drawdown_limit_hit"] for x in fold_results),
        })

    return {
        "strategy": strategy,
        "test_start": str(pd.to_datetime(test_start, utc=True)),
        "test_end_exclusive": str(pd.to_datetime(test_end, utc=True)),
        "fold_months": fold_months,
        "fold_count": len(folds),
        "starting_balance_per_fold": starting_balance,
        "risk_fraction": risk_fraction,
        "method": "fixed rules; sequential monthly out-of-sample folds; each fold independently starts at starting_balance; data truncated at each fold end",
        "cost_note": "Cost multipliers are sensitivity assumptions, not verified broker quotes. P/L units depend on the placeholder or configured value_per_price_unit_per_lot.",
        "scenarios": scenarios,
    }
