"""Run monthly rolling out-of-sample validation from a Dukascopy OHLCV CSV."""
import argparse
import json
import pandas as pd

from aron_trader.cli import load_ohlcv_csv
from aron_trader.walk_forward import run_walk_forward


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--symbol", default="eurusd")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--test-end", required=True)
    parser.add_argument("--fold-months", type=int, default=1)
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--risk", type=float, default=0.005)
    parser.add_argument("--base-spread", type=float, default=0.0001)
    parser.add_argument("--base-slippage", type=float, default=0.00005)
    args = parser.parse_args()
    report = run_walk_forward(
        load_ohlcv_csv(args.csv),
        strategy=args.strategy,
        test_start=args.test_start,
        test_end=args.test_end,
        starting_balance=args.balance,
        risk_fraction=args.risk,
        base_spread=args.base_spread,
        base_slippage=args.base_slippage,
        fold_months=args.fold_months,
    )
    print(json.dumps({"symbol": args.symbol, **report}, indent=2, default=str))


if __name__ == "__main__":
    main()
