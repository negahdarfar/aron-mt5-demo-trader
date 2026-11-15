# MTF proxy backtest — EURUSD M15 — October 2026

## Run provenance

- GitHub Actions run: [#8 — completed successfully](https://github.com/negahdarfar/aron-mt5-demo-trader/actions/runs/43723026938)
- Data: Dukascopy-node EURUSD M15 bid candles, 2026-09-01 through 2026-11-01.
- Warm-up: September 2026.
- Evaluation window: 2026-10-01 00:00 UTC through (exclusive) 2026-11-01 00:00 UTC.
- Starting balance: $1,000 (research unit model).
- Position risk: 0.5%; target: 2R; one open position; existing daily and drawdown guards.
- The strategy is an independent MTF proxy, not a faithful port of the truncated Pine source.

## Results

| Strategy | Cost scenario | Trades | Win rate | Profit factor | Net P/L* | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|
| MTF proxy | zero modeled costs | 10 | 30.00% | 0.542 | -$24.88 | 4.44% |
| MTF proxy | 0.00010 spread + 0.00005 slippage | 10 | 30.00% | 0.390 | -$38.26 | 5.20% |
| EMA/RSI baseline | zero modeled costs | 30 | 36.67% | 1.089 | +$9.24 | 6.03% |
| EMA/RSI baseline | same cost sensitivity | 28 | 39.29% | 0.847 | -$17.07 | 6.12% |
| SMC | zero modeled costs | 42 | 35.71% | 1.032 | +$4.56 | 5.18% |
| SMC | same cost sensitivity | 14 | 14.29% | 0.199 | -$62.31 | 6.23% |
| Pro opportunity engine | zero modeled costs | 48 | 39.58% | 1.382 | +$60.83 | 6.28% |
| Pro opportunity engine | same cost sensitivity | 29 | 31.03% | 0.775 | -$28.16 | 6.25% |

*P/L is in the simulator's abstract price-unit conversion, not verified USD account P/L. The default value-per-price-unit-per-lot is a placeholder (1.0), not calibrated to Aron Groups.

## Decision

**MTF proxy fails this first October evaluation and must not be promoted to demo execution.** It loses before modeled costs and degrades further under the sensitivity assumptions. Do not optimize repeatedly against October; preserve it as an evaluation set and develop on separate historical periods before a new out-of-sample test.

The zero-cost and sensitivity scenarios are diagnostics, not a complete broker cost model. Commission, swap, tick value, contract size, account-currency conversion, lot steps, margin and real execution are not modeled. The spread/slippage assumptions are simplified price-unit costs and should not be interpreted as a broker quote.

## Next work

1. Validate on separate development periods (for example, earlier 2025–2026 data), without changing October rules.
2. Inspect the ten MTF trades and the D1/H4/H1/M15 state at each entry.
3. Correct the signal design only from development data, then freeze it.
4. Re-run untouched October and a second out-of-sample period.
5. Obtain Aron Groups EURUSD contract/tick-value and commission/swap specifications before any account-currency performance claim.

No broker connection or order placement is enabled.
