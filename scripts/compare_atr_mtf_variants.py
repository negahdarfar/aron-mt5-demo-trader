"""Compare ATR baseline, H1/H4-confirmed ATR, and H1/H4 plus fixed UTC hours.

No parameters are optimized here. The two date ranges are reported separately:
Sep 2025-Apr 2026 is the earlier session-filter holdout; May-Oct 2026 is the
more recent exploratory window previously used to assess the baseline.
"""
import argparse
import json

from aron_trader.cli import load_ohlcv_csv
from aron_trader.walk_forward import run_walk_forward


PERIODS = (
    ("earlier_holdout", "2025-09-01", "2026-05-01"),
    ("recent_window", "2026-05-01", "2026-11-01"),
)


def cost_assumptions(symbol: str) -> tuple[float, float, str]:
    """Return illustrative price-unit costs using FX pip conventions.

    These are sensitivity assumptions, not verified Aron Groups quotes.
    JPY pairs use a 0.01 pip size; other major pairs use 0.0001.
    """
    normalized = symbol.lower().replace("/", "")
    if normalized.endswith("jpy"):
        return 0.01, 0.005, "JPY pair: 1.0 pip spread + 0.5 pip slippage"
    return 0.0001, 0.00005, "Non-JPY pair: 1.0 pip spread + 0.5 pip slippage"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--symbol", default="eurusd")
    args = parser.parse_args()
    frame = load_ohlcv_csv(args.csv)
    base_spread, base_slippage, cost_note = cost_assumptions(args.symbol)
    variants = (
        ("baseline_all_hours", "atr_breakout", None),
        ("atr_breakout_h1_h4", "atr_breakout_mtf", None),
        ("atr_breakout_h1_h4_hours_07_15_utc", "atr_breakout_mtf", {7, 15}),
    )
    output = {
        "symbol": args.symbol,
        "cost_assumptions": {
            "base_spread_price_units": base_spread,
            "base_slippage_price_units": base_slippage,
            "description": cost_note,
            "warning": "Illustrative pip-normalized sensitivity only; verify live Aron Groups spread, commission, swap, execution and contract specifications before any demo/live conclusions.",
        },
        "method_note": (
            "Fixed rules; monthly independent OOS folds; each fold starts at 1000 units. "
            "H1/H4 context uses only fully closed higher-timeframe candles and is joined "
            "backward to M15 timestamps. 07/15 UTC is frozen from prior exploratory work. "
            "P/L units and costs are placeholders, not Aron Groups account-currency results."
        ),
        "periods": {},
    }
    for period_name, start, end in PERIODS:
        period_result = {"start": start, "end_exclusive": end, "variants": {}}
        for name, strategy, hours in variants:
            period_result["variants"][name] = run_walk_forward(
                frame=frame,
                strategy=strategy,
                test_start=start,
                test_end=end,
                starting_balance=1000.0,
                risk_fraction=0.005,
                base_spread=base_spread,
                base_slippage=base_slippage,
                cost_multipliers=(1.0, 2.0),
                fold_months=1,
                allowed_entry_hours_utc=hours,
            )
        output["periods"][period_name] = period_result
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
