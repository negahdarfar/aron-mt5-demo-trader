# Professional Trading System Architecture

## Mission

Evolve the starter EMA/RSI + SMC research script into a modular, multi-market, multi-strategy trading system for the Aron Groups MT5 environment. The system must discover and rank qualified opportunities, not blindly trade every market movement.

This is a staged engineering plan. It does not claim profitability and does not authorize live orders.

## Reference projects and what we reuse

| Project | Reusable design | What we do not copy blindly |
|---|---|---|
| NautilusTrader | Event-driven architecture, instrument/order/position state, portfolio-aware risk, shared research/live concepts | Its Rust core and venue adapters are not a drop-in MT5 connection. A dedicated MT5 adapter and compatibility tests are required. |
| QuantConnect LEAN | Separation of data, alpha/signal, portfolio construction, risk management and execution | Brokerage integrations and market data entitlements are venue-specific; no assumption of an Aron adapter. |
| VectorBT | Fast parameter sweeps, vectorized signal research and robustness checks | Vectorized research is not the final execution simulator and can hide order-path details. |
| QuantStats | Performance, drawdown and risk reporting | Metrics do not validate data quality or execution assumptions. |

## Target architecture

1. **Market data**
   - Instrument metadata and symbol aliases from the broker.
   - Historical OHLCV and, when available, bid/ask/tick data.
   - Session calendar, timezone normalization, missing-bar and stale-data checks.
   - Separate market-data provider interface from strategy logic.

2. **Feature and market-regime layer**
   - ATR/volatility, trend strength, momentum, range/trend classification.
   - Multi-timeframe context with explicit closed-candle rules.
   - Session and spread filters.
   - No look-ahead: every feature must declare when it becomes available.

3. **Strategy/alpha modules**
   - Trend continuation and pullback.
   - Breakout and retest.
   - Liquidity sweep / displacement / market structure shift.
   - BOS/CHOCH, FVG and order-block retest.
   - Range mean reversion.
   - Volatility expansion and session setups.
   - Each strategy emits a structured candidate: direction, entry zone, invalidation, target logic, expiry, confidence components and reason codes. A strategy is not allowed to place orders.

4. **Opportunity scanner and ranking**
   - Scan a configurable symbol universe and timeframes.
   - Reject stale data, excessive spread, low liquidity, conflicting regime or poor reward/risk.
   - Rank qualified candidates by setup quality, confluence, expected costs and portfolio correlation.
   - Deduplicate repeated signals and prevent chasing late entries.
   - Report rejected opportunities with explicit reasons; never claim to capture literally every opportunity.

5. **Portfolio and risk manager**
   - Risk budget per trade and per day.
   - Aggregate open risk across correlated symbols.
   - Maximum simultaneous positions, exposure and margin checks.
   - Hard daily-loss and drawdown lockouts.
   - Lot sizing from broker contract/tick specifications and account-currency conversion.
   - Fail closed when instrument metadata, prices or account state are unavailable.

6. **Event-driven execution**
   - Order lifecycle: intent -> pre-trade checks -> submit -> acknowledge/reject -> partial fill/fill -> modify/cancel -> reconcile.
   - Idempotent client order IDs and duplicate-order protection.
   - Reconcile broker positions/orders after reconnect.
   - Demo-only account allowlist and explicit live-account block.
   - MT5 adapter isolated behind a broker interface; no credentials in GitHub.

7. **Research and validation**
   - Event-driven backtest with spread, commission, swap, slippage, gaps, partial fills where data permits.
   - Walk-forward and out-of-sample evaluation; no tuning on the final test window.
   - Monthly report remains October-only when requested; warm-up bars are not counted as trades.
   - Compare strategy, symbol, timeframe and regime. Track expectancy, profit factor, drawdown, exposure, turnover, costs and stability.
   - Preserve every configuration, data source, code commit and report for reproducibility.

8. **Operations and monitoring**
   - Structured logs, health checks, heartbeat, alerts and kill switch.
   - Paper/demo shadow mode before any execution.
   - Recovery tests for network loss, terminal restart, stale quotes and rejected orders.

## Initial strategy universe

The first implementation should not enable all strategies at once. Implement and test each independently, then combine them behind a common candidate schema:

- Trend: EMA structure + ADX/regime + pullback confirmation.
- Structure: confirmed swing BOS/CHOCH with retest.
- Liquidity: equal highs/lows sweep + displacement + close confirmation.
- Imbalance: FVG formation and controlled retest.
- Order block: causal last opposing candle before displacement/BOS, invalidation and mitigation rules.
- Range: volatility-normalized mean reversion only when the regime classifier says range.
- Session: London/New York session windows in broker/server timezone, with DST-aware conversion.

The existing EMA/RSI and simplified SMC functions are prototypes only. They must be replaced or wrapped to meet the candidate contract and receive dedicated unit tests.

## Delivery phases

### Phase A — foundation (next)
- Define typed domain models for Instrument, Candle, Candidate, Order, Fill, Position and AccountSnapshot.
- Add a strategy registry and common signal contract.
- Add regime, spread/session and opportunity-ranking modules.
- Add deterministic tests for no-lookahead, duplicate signals, risk aggregation and position sizing.

### Phase B — research engine
- Replace the single-position simulator with an event-driven portfolio simulator.
- Add realistic instrument specifications, costs, margin and multi-position accounting.
- Add walk-forward and monthly-only report generation.

### Phase C — broker integration
- Build a separate MT5 terminal adapter for Windows/VPS.
- Verify Aron symbol contract metadata and demo account identity.
- Add reconciliation, kill switch, reconnect and order-state tests.
- Android remains a monitoring/control client; it cannot host the MT5 Expert Advisor/Python terminal bridge.

### Phase D — controlled demo validation
- Run shadow signals first, then demo-only orders.
- Compare predicted vs actual fills and costs.
- Require a predeclared minimum sample and out-of-sample stability before considering any further stage.

## Non-negotiable safety rules

- No live trading code path until explicitly authorized and separately reviewed.
- Never infer pip value, contract size, lot step, commission or swap.
- Never treat a backtest as proof of future profitability.
- Never use future candles or revised higher-timeframe candles before they close.
- Never silently continue after stale data, disconnect, unknown account type or risk-state failure.
- A candidate is not a trade: portfolio risk and execution checks must approve it.
