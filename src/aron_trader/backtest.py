"""Conservative single-position OHLCV backtester (offline research only)."""
from __future__ import annotations

import pandas as pd
from .core import add_indicators, generate_signal, validate_ohlcv
from .smc import add_smc_features


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
                 max_drawdown_limit: float = 0.06) -> dict:
    """Run a price-unit research simulation; costs are total round-trip price units.

    The instrument's contract size, account-currency conversion, margin, swap,
    commissions and broker-specific execution rules are not inferred here.
    """
    if starting_balance <= 0 or not 0 < risk_fraction <= 0.02:
        raise ValueError("Invalid balance or risk fraction")
    if spread < 0 or slippage < 0 or reward_risk < 1:
        raise ValueError("Invalid trading costs or reward/risk")
    if not 0 < max_daily_loss <= 0.10 or not 0 < max_drawdown_limit <= 0.50:
        raise ValueError("Invalid daily loss or drawdown limit")
    if strategy not in {"ema_rsi", "smc"}:
        raise ValueError("strategy must be 'ema_rsi' or 'smc'")

    data = add_indicators(validate_ohlcv(frame))
    if strategy == "smc":
        data = add_smc_features(data)

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
    for i in range(1, len(data)):
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
                pnl = direction * (exit_price - position["entry"]) * position["units"]
                pnl -= round_trip_cost * position["units"]
                balance += pnl
                trades.append({
                    "side": position["side"], "pnl": pnl,
                    "entry": position["entry"], "exit": exit_price,
                    "exit_reason": exit_reason, "units": position["units"],
                })
                position = None

        # Mark current equity at this candle close, including open P/L and
        # estimated full round-trip price costs for conservative risk checks.
        unrealized = 0.0
        if position is not None:
            direction = 1 if position["side"] == "BUY" else -1
            unrealized = direction * (float(bar["close"]) - position["entry"]) * position["units"]
            unrealized -= round_trip_cost * position["units"]
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
            pnl = direction * (exit_price - position["entry"]) * position["units"]
            pnl -= round_trip_cost * position["units"]
            balance += pnl
            trades.append({
                "side": position["side"], "pnl": pnl,
                "entry": position["entry"], "exit": exit_price,
                "exit_reason": ("max_drawdown_halt" if trading_halted_drawdown
                                else "daily_loss_halt"),
                "units": position["units"],
            })
            position = None
            last_equity = balance

        if position is None and not trading_halted_daily and not trading_halted_drawdown:
            signal = (str(prev["smc_signal"]) if strategy == "smc"
                      else generate_signal(prev))
            atr = prev.get("atr")
            if signal in ("BUY", "SELL") and pd.notna(atr) and atr > 0 and equity > 0:
                entry = float(bar["open"])
                stop_distance = float(atr)
                risk_cash = equity * risk_fraction
                units = risk_cash / stop_distance
                direction = 1 if signal == "BUY" else -1
                stop = entry - direction * stop_distance
                target = entry + direction * stop_distance * reward_risk
                position = {"side": signal, "entry": entry, "stop": stop,
                            "target": target, "units": units}

    final_close = float(data.iloc[-1]["close"])
    unrealized_pnl = 0.0
    if position is not None:
        direction = 1 if position["side"] == "BUY" else -1
        unrealized_pnl = direction * (final_close - position["entry"]) * position["units"]
        unrealized_pnl -= round_trip_cost * position["units"]
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
        "starting_balance": starting_balance,
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
            "as total round-trip price-unit costs. Contract conversion, commission, swap, "
            "margin and broker execution rules are not modeled."
        ),
    }
