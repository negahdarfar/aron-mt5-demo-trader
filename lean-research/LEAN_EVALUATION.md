# LEAN evaluation checklist

- [ ] Pin LEAN CLI version and Docker image digest.
- [ ] Confirm OANDA data subscription availability for the intended environment.
- [ ] Verify the algorithm imports and completes warm-up.
- [ ] Assert consolidator timestamps are monotonic and closed before M15 decisions.
- [ ] Reconcile M15/H1/H4 bar timestamps against the Python/Dukascopy dataset.
- [ ] Add realistic bid/ask spread and slippage model.
- [ ] Add commission and account-currency conversion only after broker contract specs are verified.
- [ ] Implement order simulation only after parity checks pass.
- [ ] Run earlier holdout and recent window without parameter optimization.
- [ ] Compare PF, expectancy, max drawdown, trade count, monthly stability and cost sensitivity.

The current algorithm is intentionally a diagnostic shell, not a profitable strategy and not a trading bot.
