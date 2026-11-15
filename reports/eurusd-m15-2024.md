# EURUSD M15 Historical Backtest — 2024

Run date: 2026-11-15  
Source: Dukascopy historical bid candles, 2024-01-01 through 2025-01-01 (end exclusive)  
Starting balance: USD 1,000  
Risk setting: 0.5% per trade; daily loss guardrail 2%; max drawdown guardrail 6%  
Execution: offline simulation only; no Aron Groups account connection or orders.

## Results

| Metric | EMA/RSI, zero costs | SMC, zero costs | EMA/RSI, cost sensitivity | SMC, cost sensitivity |
|---|---:|---:|---:|---:|
| Ending equity | $991.58 | $1,106.67 | $970.41 | $952.64 |
| Net P/L | -$8.42 | +$106.67 | -$29.59 | -$47.36 |
| Closed trades | 30 | 190 | 28 | 54 |
| Win rate | 33.33% | 38.42% | 35.71% | 40.74% |
| Profit factor | 0.925 | 1.154 | 0.756 | 0.794 |
| Expectancy / trade | -$0.281 | +$0.561 | -$1.057 | -$0.877 |
| Max drawdown | 6.13% | 6.16% | 6.75% | 6.33% |
| Daily loss guardrail hit | Yes | Yes | Yes | Yes |
| Max drawdown guardrail hit | Yes | Yes | Yes | Yes |

## Cost sensitivity assumption

The cost sensitivity run uses a hypothetical total round-trip price-unit cost of 0.00015 on EURUSD: 0.00010 spread plus 0.00005 slippage (1.5 pips total). This is an illustration only, not an Aron Groups quote or verified execution cost. No commission, swap, margin or account-currency conversion is modeled.

## Interpretation

- EMA/RSI was negative even before costs.
- SMC was positive before costs, but turned negative under the illustrative cost assumption.
- Both approaches breached the configured 6% maximum drawdown threshold and the 2% daily loss guardrail at least once.
- The reported performance is not calibrated to the broker's contract size, tick value, account-currency conversion, bid/ask execution or commissions. The sizing model currently treats price movement as if one price unit maps directly to one account-currency unit per simulated unit. Therefore the dollar P/L and risk figures are not broker-valid estimates.

## Decision

**Do not connect this strategy to a live account or use these figures as a promise of performance.** Next work should calibrate EURUSD pip/tick value and contract sizing, use broker-specific bid/ask and commission data, make kill-switch liquidation behavior explicit, and validate on a separate out-of-sample period before any demo forward test.
