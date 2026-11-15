"""Conservative single-position OHLCV backtester (offline research only)."""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, generate_signal, validate_ohlcv
from .smc import add_smc_features
from .opportunity_engine import add_opportunity_features


def _bar_exit(position: dict, bar: pd.Series):
    """Return a conservative stop/target fill, accounting for opening gaps."""
    side = position["side"]
    stop, target = position["stop"], position["target"]
    opening = float(bar["open"])
    if side == "BUY":
        if opening <= stop:
            return opening, "stop_gap"
        if opening >= target:
            return opening, "target_gap"
        if bar["low"] <= stop:
            return stop, "stop"
        if bar["high"] >= target:
            return target, "target"
    else:
        if opening >= stop:
            return opening, "stop_gap"
        if opening <= target:
            return opening, "target_gap"
        if bar["high"] >= stop:
            return stop, "stop"
        if bar["low"] <= target:
            return target, "target"
    return None, None


def run_backtest(frame: pd.DataFrame, starting_balance: float = 1000.0,
                 risk_fraction: float = 0.005, spread: float = 0.0,
                 slippage: float = 0.0, reward_risk: float = 2.0,
                 strategy: str = "ema_rsi", max_daily_loss: float = 0.02,
                 max_drawdown_limit: float = 0.06,
                 value_per_price_unit_per_lot: float = 1.0,
                 trade_start: str | None = None,
                 trade_end: str | None = None) -> dict:
    """Run a price-unit research simulation; costs are total round-trip price units.

    The instrument's contract size, account-currency conversion, margin, swap,
    commissions and broker-specific execution rules are not inferred here.
    """
    if starting_balance <= 0 or not 0 < risk_fraction <= 0.02:
        raise ValueError("Invalid balance or risk fraction")
    if spread < 0 or slippage < 0 or reward_risk < 1:
        raise ValueError("Invalid trading costs or reward/risk")
    if (not pd.notna(value_per_price_unit_per_lot)
            or value_per_price_unit_per_lot <= 0):
        raise ValueError("value_per_price_unit_per_lot must be positive")
    if not 0 < max_daily_loss <= 0.10 or not 0 < max_drawdown_limit <= 0.50:
        raise ValueError("Invalid daily loss or drawdown limit")
    if strategy not in {"ema_rsi", "smc", "pro", "mtf", "wizards", "donchian", "ema_trend", "momentum", "atr_breakout"}:
        raise ValueError("Unsupported strategy")

    data = add_indicators(validate_ohlcv(frame))
    if strategy == "smc":
        data = add_smc_features(data)
    elif strategy == "pro":
        data = add_opportunity_features(data)
    elif strategy == "mtf":
        from .mtf_strategy import add_mtf_features
        data = add_mtf_features(data)
    elif strategy == "wizards":
        from .wizards_ensemble import add_wizards_features
        data = add_wizards_features(data)
    elif strategy == "donchian":
        from .donchian import add_donchian_features
        data = add_donchian_features(data)
    elif strategy == "ema_trend":
        from .ema_trend import add_ema_trend_features
        data = add_ema_trend_features(data)
    elif strategy == "momentum":
        from .momentum import add_momentum_features
        data = add_momentum_features(data)
    elif strategy == "atr_breakout":
        from .atr_breakout import add_atr_breakout_features
        data = add_atr_breakout_features(data)

    # Indicators are calculated on all available history (warm-up), but only
    # candles inside [trade_start, trade_end) are eligible for positions.
    start_ts = (pd.to_datetime(trade_start, utc=True).as_unit("ns")
                if trade_start else data["timestamp"].iloc[0])
    end_ts = (pd.to_datetime(trade_end, utc=True).as_unit("ns")
              if trade_end else data["timestamp"].iloc[-1] + pd.Timedelta(seconds=1))
    if end_ts <= start_ts:
        raise ValueError("trade_end must be later than trade_start")
    start_idx = int((data["timestamp"] < start_ts).sum())
    end_idx = int((data["timestamp"] < end_ts).sum())
    if end_idx - start_idx < 2:
        raise ValueError("Not enough candles inside the requested trading window")

    balance = float(starting_balance)
    equity_peak = balance
    max_drawdown = 0.0
    trades = []
    position = None
    daily_start_equity = balance
    last_equity = balance
    active_day = None
    trading_halted_daily = False
    daily_loss_limit_ever_hit = False
    trading_halted_drawdown = False
    round_trip_cost = float(spread + slippage)

    # Signals use the previous completed candle; fills use this candle's open.
    for i in range(max(1, start_idx), end_idx):
        bar = data.iloc[i]
        prev = data.iloc[i - 1]
        current_day = pd.Timestamp(bar["timestamp"]).date()
        if current_day != active_day:
            active_day = current_day
            daily_start_equity = last_equity
            trading_halted_daily = False

        if position is not None:
            exit_price, exit_reason = _bar_exit(position, bar)
            if exit_price is not None:
                direction = 1 if position["side"] == "BUY" else -1
                pnl = (direction * (exit_price - position["entry"])
                       * position["lots"] * value_per_price_unit_per_lot)
                pnl -= round_trip_cost * position["lots"] * value_per_price_unit_per_lot
                balance += pnl
                trades.append({
                    "side": position["side"], "pnl": pnl,
                    "entry": position["entry"], "exit": exit_price,
                    "entry_time": position["entry_time"],
                    "exit_reason": exit_reason, "lots": position["lots"],
                })
                position = None

        # Mark current equity at this candle close, including open P/L and
        # estimated full round-trip price costs for conservative risk checks.
        unrealized = 0.0
        if position is not None:
            direction = 1 if position["side"] == "BUY" else -1
            unrealized = (direction * (float(bar["close"]) - position["entry"])
                          * position["lots"] * value_per_price_unit_per_lot)
            unrealized -= round_trip_cost * position["lots"] * value_per_price_unit_per_lot
        equity = balance + unrealized
        last_equity = equity
        equity_peak = max(equity_peak, equity)
        if equity_peak > 0:
            max_drawdown = max(max_drawdown, (equity_peak - equity) / equity_peak)
        if daily_start_equity > 0 and (daily_start_equity - equity) / daily_start_equity >= max_daily_loss:
            trading_halted_daily = True
            daily_loss_limit_ever_hit = True
        if max_drawdown >= max_drawdown_limit:
            trading_halted_drawdown = True

        # A breached risk limit liquidates an open position at the current
        # candle close (plus modeled round-trip costs) and blocks new entries.
        # This is a bar-close approximation, not a broker-side stop guarantee.
        if position is not None and (trading_halted_daily or trading_halted_drawdown):
            direction = 1 if position["side"] == "BUY" else -1
            exit_price = float(bar["close"])
            pnl = (direction * (exit_price - position["entry"])
                   * position["lots"] * value_per_price_unit_per_lot)
            pnl -= round_trip_cost * position["lots"] * value_per_price_unit_per_lot
            balance += pnl
            trades.append({
                "side": position["side"], "pnl": pnl,
                "entry": position["entry"], "exit": exit_price,
                "entry_time": position["entry_time"],
                "exit_reason": ("max_drawdown_halt" if trading_halted_drawdown
                                else "daily_loss_halt"),
                "lots": position["lots"],
            })
            position = None
            last_equity = balance

        if position is None and not trading_halted_daily and not trading_halted_drawdown:
            signal = (str(prev["smc_signal"]) if strategy == "smc"
                      else str(prev["pro_signal"]) if strategy == "pro"
                      else str(prev["mtf_signal"]) if strategy == "mtf"
                      else str(prev["wizards_signal"]) if strategy == "wizards"
                      else str(prev["donchian_signal"]) if strategy == "donchian"
                      else str(prev["ema_trend_signal"]) if strategy == "ema_trend"
                      else str(prev["momentum_signal"]) if strategy == "momentum"
                      else str(prev["atr_breakout_signal"]) if strategy == "atr_breakout"
                      else generate_signal(prev))
            atr = prev.get("atr")
            if signal in ("BUY", "SELL") and pd.notna(atr) and atr > 0 and equity > 0:
                entry = float(bar["open"])
                stop_distance = float(atr)
                risk_cash = equity * risk_fraction
                lots = risk_cash / (stop_distance * value_per_price_unit_per_lot)
                direction = 1 if signal == "BUY" else -1
                stop = entry - direction * stop_distance
                target = entry + direction * stop_distance * reward_risk
                position = {"side": signal, "entry": entry, "stop": stop,
                            "target": target, "lots": lots,
                            "entry_time": bar["timestamp"]}

    final_close = float(data.iloc[end_idx - 1]["close"])
    unrealized_pnl = 0.0
    if position is not None:
        direction = 1 if position["side"] == "BUY" else -1
        unrealized_pnl = (direction * (final_close - position["entry"])
                          * position["lots"] * value_per_price_unit_per_lot)
        unrealized_pnl -= round_trip_cost * position["lots"] * value_per_price_unit_per_lot
    ending_equity = balance + unrealized_pnl
    equity_peak = max(equity_peak, ending_equity)
    if equity_peak > 0:
        max_drawdown = max(max_drawdown, (equity_peak - ending_equity) / equity_peak)

    wins = sum(t["pnl"] > 0 for t in trades)
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    losses = len(trades) - wins
    average_win = gross_profit / wins if wins else 0.0
    average_loss = gross_loss / losses if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (None if not gross_profit else "infinity")
    expectancy = sum(t["pnl"] for t in trades) / len(trades) if trades else 0.0
    loss_streak = max_loss_streak = 0
    for trade in trades:
        if trade["pnl"] < 0:
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            loss_streak = 0
    return {
        "strategy": strategy,
        "trade_start": str(start_ts),
        "trade_end_exclusive": str(end_ts),
        "starting_balance": starting_balance,
        "value_per_price_unit_per_lot": value_per_price_unit_per_lot,
        "ending_balance": balance,
        "ending_equity": ending_equity,
        "unrealized_pnl": unrealized_pnl,
        "net_profit": ending_equity - starting_balance,
        "trades": len(trades),
        "wins": wins,
        "win_rate": wins / len(trades) if trades else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "expectancy_per_trade": expectancy,
        "average_win": average_win,
        "average_loss": average_loss,
        "max_consecutive_losses": max_loss_streak,
        "max_drawdown": max_drawdown,
        "daily_loss_limit_hit": daily_loss_limit_ever_hit,
        "max_drawdown_limit_hit": trading_halted_drawdown,
        "trade_log": trades,
        "open_position_at_end": position is not None,
        "note": (
            "Offline research only. Ending equity marks any open position to the final close; "
            "open trades are not counted as closed wins/losses. Spread+slippage are treated "
            "as total round-trip price-unit costs. Set value_per_price_unit_per_lot "
            "from verified symbol/account-currency specifications; the default 1.0 is "
            "a placeholder, not an Aron Groups calibration. Commission, swap, margin, "
            "lot steps and broker execution rules are not modeled."
        ),
    }
