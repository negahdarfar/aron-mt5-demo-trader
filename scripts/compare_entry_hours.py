"""Compare baseline ATR breakout with a fixed UTC session filter on an earlier holdout."""
import argparse
import json

from aron_trader.cli import load_ohlcv_csv
from aron_trader.walk_forward import run_walk_forward


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--symbol", default="eurusd")
    parser.add_argument("--test-start", default="2025-09-01")
    parser.add_argument("--test-end", default="2026-05-01")
    args = parser.parse_args()
    frame = load_ohlcv_csv(args.csv)
    common = dict(
        frame=frame, strategy="atr_breakout",
        test_start=args.test_start, test_end=args.test_end,
        starting_balance=1000.0, risk_fraction=0.005,
        base_spread=0.0001, base_slippage=0.00005,
        cost_multipliers=(0.0, 1.0, 2.0, 3.0), fold_months=1,
    )
    baseline = run_walk_forward(**common)
    filtered = run_walk_forward(**common, allowed_entry_hours_utc={7, 15})
    result = {
        "symbol": args.symbol,
        "holdout_period": {"start": args.test_start, "end_exclusive": args.test_end},
        "comparison_note": (
            "This earlier period was not the period used for the previously reported May-Oct 2026 "
            "hour ranking. The 07/15 UTC filter is frozen before this comparison. "
            "Each monthly fold starts independently at 1000 units; P/L units use an unverified "
            "placeholder value-per-price-unit and cost assumptions are not broker quotes."
        ),
        "baseline_all_hours": baseline,
        "fixed_hours_07_15_utc": filtered,
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
