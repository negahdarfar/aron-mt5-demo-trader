# LEAN engine evaluation (isolated branch)

This folder is an isolated QuantConnect LEAN experiment. It does not modify the existing ATR/MTF backtester and does not connect to Aron Groups or place orders.

## Phase 0: engine and data-contract validation

The first LEAN algorithm is deliberately signal-only. It subscribes to EURUSD minute data, consolidates it into M15/H1/H4 bars, and emits a diagnostic signal only after all three bars are closed. No order methods are called.

This phase checks:
- LEAN Python algorithm loading;
- Forex subscription and consolidator lifecycle;
- closed-bar synchronization (no use of an unfinished H1/H4 candle);
- deterministic ATR and trend inputs.

## Why it is not yet a performance backtest

A valid LEAN backtest needs a LEAN runtime, compatible historical forex data, and explicit brokerage/data-feed assumptions. The existing Dukascopy CSV files are not automatically interchangeable with LEAN's native data format. We must convert and validate timestamps, bid/ask convention, timezone, missing bars and price precision before comparing P/L.

No profitability claim should be made from this signal-only phase. No broker credentials or account details belong in this repository.

## Next gates

1. Run the algorithm inside a pinned LEAN Docker/CLI runtime.
2. Verify that M15/H1/H4 consolidators emit only completed bars and do not repaint.
3. Import the same historical candle range as the existing Python backtest and reconcile candle counts/timestamps.
4. Only then implement order simulation with explicit spread, slippage, commission and position sizing.
5. Compare LEAN results against the current Python baseline on identical data.

## Run

Open this folder as a LEAN Python project with a pinned LEAN CLI/runtime. The project is not yet wired to a GitHub Actions backtest because the runner's Docker image, data availability and LEAN CLI behavior must first be pinned and verified.
