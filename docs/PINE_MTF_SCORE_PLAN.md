# Pine MTF Score Strategy Integration Plan

Status: integration scaffold only. The Pine source received in chat is truncated inside the Support/Resistance engine (at `if high[`), so no claim is made that the indicator has been ported.

## Objective

Create an offline, reproducible backtest strategy based on the indicator's actual MTF score-panel decisions. Preserve the Pine source's parameters and semantics wherever possible. Do not enable broker execution.

## Intended timeframe roles

- D1: broad directional veto/filter.
- H4: primary market-regime and directional confirmation.
- H1: principal decision timeframe; highest priority for trade direction.
- M15: setup/entry confirmation.
- M5: optional execution refinement only; it must not override H1/H4 direction.

The exact score thresholds and panel decision mapping must be extracted from the remaining Pine source before implementation.

## Entry policy (provisional architecture, not yet coded)

- Evaluate only completed candles.
- Longs require aligned positive higher-timeframe decisions; shorts require aligned negative decisions.
- H1 is the principal decision timeframe and must meet the Pine-defined minimum entry score.
- H4 must not contradict H1; D1 acts as a configurable directional veto.
- M15 must confirm the same direction with a completed-bar trigger.
- If required timeframes disagree, do not trade.
- Avoid double-counting correlated moving-average families when constructing any supplemental composite. Prefer the Pine panel's own normalized score and decision output over inventing a second score.

## Exit and risk policy (provisional architecture, not yet coded)

- Initial stop: structure-based where the completed-bar S/R logic provides a valid level, with ATR fallback/cap.
- Initial target: minimum planned reward/risk 2.0, subject to valid nearby S/R.
- One position at a time until the source strategy and fill model are validated.
- Exit on stop/target, confirmed opposite panel decision, or explicit structure invalidation.
- Existing daily-loss and maximum-drawdown guardrails remain active.
- No martingale, grid, averaging down, or automatic live/demo order routing.

## Required source sections before faithful implementation

1. Complete Support/Resistance engine.
2. Previous D/W/M level calculations.
3. Session calculations and timezone/session membership.
4. All EMA-set, envelope, and EMA/SMA-pair MTF calculations.
5. Ichimoku, Bollinger, volume and volume-profile score calculations.
6. Structure score calculation and final normalized score aggregation.
7. MTF table/panel construction and exact BUY/SELL/WAIT decision rules.
8. Candle trigger, ATR quality filter, alerts, and any final entry/exit conditions.

## Backtest protocol

- Keep this strategy separate from the existing `pro` strategy.
- First compare against the existing baseline and Pro results without changing their code.
- Use the previously agreed October 2026 evaluation window only after the complete Pine logic has been ported.
- Include zero-cost diagnostics and conservative spread/slippage scenarios; broker commission, swap, tick value, contract size, and account-currency conversion must be calibrated from Aron Groups specifications before treating P/L as account-currency results.
- Report trade count, win rate, profit factor, expectancy, max drawdown, losing streak, daily-loss guardrail hits, and per-timeframe decision diagnostics.
- Do not tune repeatedly on October 2026; preserve it as an evaluation period and use separate development/out-of-sample data for later tuning.

## Non-repainting and parity requirements

- No use of unconfirmed current higher-timeframe candles.
- No lookahead in MTF resampling/security-equivalent logic.
- Pivot signals become available only after their right-side confirmation bars have elapsed.
- Any Pine behavior that cannot be represented exactly in the Python backtester must be documented and tested.
- Add unit tests for score normalization, timeframe alignment, completed-bar gating, conflicting signals, and duplicate-entry prevention.

## Current blocker

The received source ends mid-expression at `if high[`. Continue sending the Pine code through the final panel/score/trigger logic. Once the complete source is available, replace this provisional plan with a faithful implementation and run CI/backtests.
