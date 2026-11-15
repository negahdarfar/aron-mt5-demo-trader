"""Command-line runner for offline CSV backtests."""
import argparse
import json
import pandas as pd
from .backtest import run_backtest


def load_ohlcv_csv(path: str) -> pd.DataFrame:
    """Load project CSVs and Dukascopy-node CSVs (Unix-ms timestamps)."""
    frame = pd.read_csv(path)
    if "timestamp" not in frame.columns:
        raise ValueError("CSV must contain a timestamp column")
    if pd.api.types.is_numeric_dtype(frame["timestamp"]):
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="ARON demo-trader offline backtest")
    parser.add_argument("--csv", required=True, help="Path to OHLCV CSV file")
    parser.add_argument("--symbol", default="UNKNOWN")
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--strategy", choices=("ema_rsi", "smc", "pro", "mtf", "wizards", "donchian", "ema_trend", "momentum", "atr_breakout", "trend_pullback", "bos_retest", "liquidity_sweep_bos"), default="ema_rsi")
    parser.add_argument("--spread", type=float, default=0.0,
                        help="Simplified total round-trip cost in price units")
    parser.add_argument("--slippage", type=float, default=0.0,
                        help="Simplified total round-trip cost in price units")
    parser.add_argument("--trade-start", help="First eligible trade date/time (UTC)")
    parser.add_argument("--trade-end", help="Exclusive end date/time (UTC)")
    args = parser.parse_args()
    result = run_backtest(
        load_ohlcv_csv(args.csv),
        starting_balance=args.balance,
        strategy=args.strategy,
        spread=args.spread,
        slippage=args.slippage,
        trade_start=args.trade_start,
        trade_end=args.trade_end,
    )
    result.pop("trade_log", None)
    print(json.dumps({"symbol": args.symbol, **result}, indent=2, default=str))


if __name__ == "__main__":
    main()
