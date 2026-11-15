# Professional Opportunity Engine — October 2026 Research Report

## Scope
- Instrument: EURUSD
- Timeframe: M15
- Trading window: 2026-10-01 00:00 UTC through 2026-11-01 00:00 UTC (end exclusive)
- Starting simulated balance: 1,000 units
- Strategy: `pro` (multi-setup opportunity engine)
- Historical candles downloaded from Dukascopy by the GitHub Actions workflow.
- CI tests for the engine and backtester passed before this run.

## Results

| Metric | Zero modeled costs | Cost sensitivity case |
|---|---:|---:|
| Trades | 48 | 29 |
| Wins | 19 | 9 |
| Win rate | 39.58% | 31.03% |
| Net P/L (simulation units) | +60.83 | -28.16 |
| Ending balance | 1,060.83 | 971.84 |
| Profit factor | 1.382 | 0.775 |
| Expectancy per trade | +1.267 | -0.971 |
| Maximum drawdown | 6.28% | 6.25% |
| Maximum consecutive losses | 7 | 7 |
| Daily loss limit hit | Yes | Yes |
| Maximum drawdown limit hit | Yes | Yes |

The cost sensitivity workflow supplied `--spread 0.0001 --slippage 0.00005`. In this backtester these are combined as modeled round-trip price-unit costs. This is a hypothetical sensitivity case, not a verified Aron Groups spread/commission schedule.

## Interpretation
The strategy was positive before modeled costs but negative in the cost-sensitivity case. Both cases breached the configured 6% maximum drawdown guardrail; both also hit the daily loss guardrail at least once. This is not an acceptable basis for demo deployment.

## Critical limitations
1. `value_per_price_unit_per_lot=1.0` remains a placeholder. It is not calibrated to the Aron Groups EURUSD contract specification or the account's deposit currency. Therefore P/L, sizing, and drawdown expressed in account-currency units are not broker-accurate.
2. Commission, swap, margin, minimum/step lot size, tick value, currency conversion, execution latency, requotes, and broker-specific fills are not modeled.
3. The backtester is a simplified single-position OHLCV simulator, not a live MT5 execution engine.
4. October is one evaluation month and one symbol/timeframe. These results do not establish robustness or future profitability.
5. The cost-free result must not be used as a performance forecast.

## Decision
**Do not connect this strategy to a live account or enable automated demo execution yet.** Next work should prioritize verified broker contract/cost calibration, improved fill simulation, and independent out-of-sample validation. Do not optimize repeatedly against October alone.
