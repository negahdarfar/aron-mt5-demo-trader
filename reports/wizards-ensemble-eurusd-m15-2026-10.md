# Wizards Ensemble — EURUSD M15 — October 2026

## What this is

There is no official, universally accepted top-ten trader ranking, and the traders interviewed in Jack Schwager's *Market Wizards* do not share one strategy. The ensemble is a research approximation of public strategy families, not a copy of anyone's proprietary rules or track record.

Representative approaches discussed in public trader interviews and summaries include:

| Trader | Publicly described approach | What can be represented from this OHLCV feed |
|---|---|---|
| Richard Dennis | Systematic trend following / Turtle breakout | Donchian breakout |
| Ed Seykota | Computerized trend following, pattern recognition, money management | Trend regime and mechanical breakout |
| Larry Hite | Statistical trend following and risk limits | Trend filter and fixed fractional risk |
| Marty Schwartz | Short-term technical / moving-average momentum | EMA and RSI momentum |
| Paul Tudor Jones | Flexible macro/tape reading, asymmetric risk | Price momentum and volatility displacement only |
| Bruce Kovner | Global macro, currencies and bonds | Not reproducible without rates/macro data |
| Michael Marcus | Fundamentals plus trend tools | Trend component only; no fundamentals |
| Peter Brandt | Classical chart patterns and asymmetrical risk/reward | Simplified breakout / range structure only |
| Tony Saliba | Options volatility spreads | Not applicable to spot FX OHLCV |
| Michael Steinhardt | Variant perception, long/short equities | Not reproducible without equity/fundamental data |

## Implemented rules

- D1/H4/H1 completed-candle bias is used as a trend veto.
- Trend regime (ADX >= 22): requires higher-timeframe alignment and at least two confirming modules among Donchian breakout, EMA/RSI momentum resumption and ATR displacement.
- Range regime (ADX <= 18): mean reversion is allowed only when D1/H4/H1 are neutral, using RSI reclaim and candle direction.
- Transition regime: no trade.
- M15 is the signal timeframe; signals use completed prior candles and enter at next candle open.
- Existing single-position, ATR stop, 2R target, 0.5% risk, daily loss and drawdown guards are retained.
- No macro/news/fundamental, options-volatility, order-book or social-sentiment data are present, so those trader styles are not falsely represented as implemented.

## Validation

- GitHub Actions tests: [completed successfully](https://github.com/negahdarfar/aron-mt5-demo-trader/actions/runs/43723640173).
- Historical workflow: [completed successfully](https://github.com/negahdarfar/aron-mt5-demo-trader/actions/runs/43723647914).
- Data: Dukascopy-node EURUSD M15 bid candles from 2026-09-01 through 2026-11-01.
- September is warm-up only; evaluation window is October 2026 (UTC).
- Starting balance: $1,000 research balance; risk 0.5%; target 2R.
- The price-unit value conversion remains a placeholder, not calibrated to Aron Groups.

## Results

| Strategy | Cost assumption | Trades | Wins | Win rate | Profit factor | Net P/L* | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| Wizards ensemble | zero modeled costs | 3 | 0 | 0% | 0.000 | -14.93 units | 1.49% |
| Wizards ensemble | 0.00010 spread + 0.00005 slippage | 3 | 0 | 0% | 0.000 | -18.27 units | 1.83% |
| EMA/RSI baseline | zero modeled costs | 30 | 11 | 36.67% | 1.089 | +9.24 units | 6.03% |
| EMA/RSI baseline | same cost sensitivity | 28 | 11 | 39.29% | 0.847 | -17.07 units | 6.12% |
| Pro opportunity engine | zero modeled costs | 48 | 19 | 39.58% | 1.382 | +60.83 units | 6.28% |
| Pro opportunity engine | same cost sensitivity | 29 | 9 | 31.03% | 0.775 | -28.16 units | 6.25% |

*P/L uses the backtest's generic price-unit conversion. It is not verified USD P/L. Commission, swap, contract size, tick value, account-currency conversion, margin, lot steps and actual Aron execution are not modeled.

## Decision

**Do not connect this ensemble to a demo or live account.** It produced only three trades, all losses, on this one-month evaluation. That is a rejection for this test, not proof that all trend/momentum/range methods fail. October must remain untouched while any changes are developed on separate data.

Next validation should use substantially longer history and multiple pairs, walk-forward development/validation/test windows, broker-calibrated costs and trade-by-trade diagnostics. A profitable result is not assumed.
