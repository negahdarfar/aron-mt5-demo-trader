"""Fixed-rule monthly OOS comparison for liquidity-sweep/BOS research."""
import argparse
import json

from aron_trader.cli import load_ohlcv_csv
from aron_trader.walk_forward import run_walk_forward


PERIODS = (
    ("earlier_holdout", "2025-09-01", "2026-05-01"),
    ("recent_window", "2026-05-01", "2026-11-01"),
)


def costs(symbol):
    if symbol.lower().replace("/", "").endswith("jpy"):
        return 0.01, 0.005, "JPY: 1 pip spread + 0.5 pip slippage (illustrative)"
    return 0.0001, 0.00005, "Non-JPY: 1 pip spread + 0.5 pip slippage (illustrative)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    frame = load_ohlcv_csv(args.csv)
    spread, slippage, cost_label = costs(args.symbol)
    variants = (
        ("atr_breakout_mtf", "atr_breakout_mtf"),
        ("bos_retest", "bos_retest"),
        ("liquidity_sweep_bos", "liquidity_sweep_bos"),
    )
    output = {
        "symbol": args.symbol,
        "cost_assumptions": {
            "spread_price_units": spread,
            "slippage_price_units": slippage,
            "description": cost_label,
            "warning": "Illustrative only. Not broker-verified. Commission, swap, account-currency conversion, contract size and execution are not modeled.",
        },
        "method": "Fixed parameters; monthly independent OOS folds; each fold starts at 1000 units; 0.5% risk; no parameter optimization; costs 1x and 2x.",
        "periods": {},
    }
    for period, start, end in PERIODS:
        output["periods"][period] = {"start": start, "end_exclusive": end, "variants": {}}
        for name, strategy in variants:
            output["periods"][period]["variants"][name] = run_walk_forward(
                frame=frame, strategy=strategy, test_start=start, test_end=end,
                starting_balance=1000.0, risk_fraction=0.005,
                base_spread=spread, base_slippage=slippage,
                cost_multipliers=(1.0, 2.0), fold_months=1,
            )
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
