# ML4T-Inspired Validation Guardrails

This project borrows validation practices from [ml4t/skills](https://github.com/ml4t/skills) and [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills). These are methodology references, not broker adapters or proof of profitability.

## Controls now enforced

- OHLCV prices must be positive and finite; volume must be finite and non-negative.
- Missing timestamps and duplicate timestamps are rejected.
- OHLC candle geometry is checked before indicators are calculated.
- `check_prefix_invariance` compares features computed on a full time series with the same features computed using only a historical prefix. A mismatch flags possible future-data leakage.

## How to use the causal check

```python
from aron_trader.validation import check_prefix_invariance
from aron_trader.smc import add_smc_features

result = check_prefix_invariance(
    add_smc_features,
    historical_ohlcv,
    cutoff=int(len(historical_ohlcv) * 0.7),
)
if not result["passed"]:
    raise RuntimeError(f"Possible lookahead leak: {result['reason']}")
```

Run it separately for every feature builder and for multiple cutoffs. Passing is a useful diagnostic, not a mathematical proof: it cannot detect every form of leakage, incorrect timestamps, revised source data, or a bad fill model.

## Required validation before any demo consideration

1. Preserve time order; never shuffle time-series folds.
2. Use only information available at the decision timestamp; execute no earlier than the next tradable price.
3. Run expanding/rolling walk-forward tests with purge/embargo where labels overlap.
4. Calibrate spread, commission, swap, slippage, contract size, tick value, lot step and account-currency conversion from the actual broker's symbol specification.
5. Report gross and net results, per-fold metrics, trade count, expectancy, profit factor, max drawdown and losing streak.
6. Stress costs at 1x, 2x and 3x; assess parameter plateaus rather than a single optimized point.
7. Keep the final holdout untouched until design decisions are frozen.

## Important limitations

The current backtester is a lightweight OHLC bar simulator, not a full event-driven broker simulator. It does not yet model bid/ask tick streams, partial fills, requotes, market impact, swaps, commissions, margin calls or Aron Groups contract specifications. Its default `value_per_price_unit_per_lot=1.0` is a placeholder. Existing historical test months have already been inspected and are not pristine holdouts.
