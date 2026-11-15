from AlgorithmImports import *
from collections import deque
from datetime import timedelta
from strategy_rules import atr_breakout_direction, mtf_context_agrees, is_selected_utc_hour


class AtrMtfSignalDiagnostics(QCAlgorithm):
    """Signal-only LEAN port of the repository's fixed ATR + H1/H4 rules.

    ATR(14) Wilder, prior 20-bar channel, prior 50 ATR mean, 1.10 expansion.
    H1/H4 trend uses EMA20/EMA50 and ADX(14) >= 16. No orders are submitted.
    """

    def Initialize(self):
        self.SetStartDate(2025, 9, 1)
        self.SetEndDate(2025, 10, 1)
        self.SetCash(1000)
        self.SetTimeZone(TimeZones.Utc)
        self.symbol = self.AddForex("EURUSD", Resolution.Minute, Market.Oanda).Symbol

        self.m15 = TradeBarConsolidator(timedelta(minutes=15))
        self.h1 = TradeBarConsolidator(timedelta(hours=1))
        self.h4 = TradeBarConsolidator(timedelta(hours=4))
        self.SubscriptionManager.AddConsolidator(self.symbol, self.m15)
        self.SubscriptionManager.AddConsolidator(self.symbol, self.h1)
        self.SubscriptionManager.AddConsolidator(self.symbol, self.h4)

        self.atr = AverageTrueRange(14, MovingAverageType.Wilders)
        self.h1_fast = ExponentialMovingAverage(20)
        self.h1_slow = ExponentialMovingAverage(50)
        self.h1_adx = AverageDirectionalIndex(14)
        self.h4_fast = ExponentialMovingAverage(20)
        self.h4_slow = ExponentialMovingAverage(50)
        self.h4_adx = AverageDirectionalIndex(14)
        self.RegisterIndicator(self.symbol, self.atr, self.m15)
        for indicator in (self.h1_fast, self.h1_slow, self.h1_adx):
            self.RegisterIndicator(self.symbol, indicator, self.h1)
        for indicator in (self.h4_fast, self.h4_slow, self.h4_adx):
            self.RegisterIndicator(self.symbol, indicator, self.h4)

        self.m15.DataConsolidated += self.OnM15
        self.h1.DataConsolidated += self.OnH1
        self.h4.DataConsolidated += self.OnH4
        self.last_h1_end = None
        self.last_h4_end = None
        self.h1_bias = 0
        self.h4_bias = 0
        self.prior_highs = deque(maxlen=20)
        self.prior_lows = deque(maxlen=20)
        self.prior_atrs = deque(maxlen=50)
        self.signal_counts = {"baseline": 0, "h1_h4": 0, "h1_h4_hours_07_15_utc": 0}
        self.SetWarmUp(timedelta(days=45))

    def _bias(self, fast, slow, adx):
        if not (fast.IsReady and slow.IsReady and adx.IsReady):
            return 0
        if adx.Current.Value < 16:
            return 0
        if fast.Current.Value > slow.Current.Value:
            return 1
        if fast.Current.Value < slow.Current.Value:
            return -1
        return 0

    def OnH1(self, sender, bar):
        self.last_h1_end = bar.EndTime
        self.h1_bias = self._bias(self.h1_fast, self.h1_slow, self.h1_adx)

    def OnH4(self, sender, bar):
        self.last_h4_end = bar.EndTime
        self.h4_bias = self._bias(self.h4_fast, self.h4_slow, self.h4_adx)

    def OnM15(self, sender, bar):
        if self.atr.IsReady:
            direction = atr_breakout_direction(
                float(bar.Close), float(self.atr.Current.Value),
                list(self.prior_highs), list(self.prior_lows), list(self.prior_atrs),
            )
            # Warm-up bars build indicators/history but are excluded from reported counts.
            if direction and not self.IsWarmingUp:
                self.signal_counts["baseline"] += 1
                aligned = mtf_context_agrees(
                    direction, self.h1_bias, self.h4_bias,
                    self.last_h1_end, self.last_h4_end, bar.EndTime,
                )
                if aligned:
                    self.signal_counts["h1_h4"] += 1
                    if is_selected_utc_hour(bar.EndTime.hour):
                        self.signal_counts["h1_h4_hours_07_15_utc"] += 1
                    self.Debug(
                        f"ATR_MTF {'LONG' if direction == 1 else 'SHORT'} "
                        f"{bar.EndTime} close={bar.Close} "
                        f"atr={self.atr.Current.Value:.6g} "
                        f"h1={self.h1_bias} h4={self.h4_bias}"
                    )

        # Append after evaluation: current candle is excluded from its own thresholds.
        if self.atr.IsReady:
            self.prior_atrs.append(float(self.atr.Current.Value))
        self.prior_highs.append(float(bar.High))
        self.prior_lows.append(float(bar.Low))

    def OnEndOfAlgorithm(self):
        self.Debug(f"DIAGNOSTIC_SIGNAL_COUNTS {self.signal_counts}")
