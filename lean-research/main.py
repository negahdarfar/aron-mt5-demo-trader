from AlgorithmImports import *
from collections import deque
from datetime import timedelta
from statistics import mean


class AtrMtfSignalDiagnostics(QCAlgorithm):
    """Signal-only LEAN port of the repository's fixed ATR + H1/H4 rules.

    Mirrors atr_breakout.py defaults: ATR(14), prior 20-bar channel,
    prior 50-value ATR mean and 1.10 expansion. H1/H4 bias mirrors
    mtf_strategy.py: EMA(20) versus EMA(50), gated by ADX(14) >= 16.
    The 07/15 UTC variant is diagnostic only. No orders are submitted.
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
        # Evaluate using prior 20 highs/lows and prior 50 ATR values.
        if (self.atr.IsReady and len(self.prior_highs) == 20
                and len(self.prior_atrs) == 50):
            atr_baseline = mean(self.prior_atrs)
            volatile = self.atr.Current.Value > atr_baseline * 1.10
            bullish_breakout = volatile and bar.Close > max(self.prior_highs)
            bearish_breakout = volatile and bar.Close < min(self.prior_lows)

            if bullish_breakout or bearish_breakout:
                side = "LONG" if bullish_breakout else "SHORT"
                self.signal_counts["baseline"] += 1

                context_is_closed = (
                    self.last_h1_end is not None
                    and self.last_h4_end is not None
                    and self.last_h1_end <= bar.EndTime
                    and self.last_h4_end <= bar.EndTime
                )
                aligned = context_is_closed and (
                    (bullish_breakout and self.h1_bias == 1 and self.h4_bias == 1)
                    or (bearish_breakout and self.h1_bias == -1 and self.h4_bias == -1)
                )
                if aligned:
                    self.signal_counts["h1_h4"] += 1
                    if bar.EndTime.hour in (7, 15):
                        self.signal_counts["h1_h4_hours_07_15_utc"] += 1
                    self.Debug(
                        f"ATR_MTF {side} {bar.EndTime} close={bar.Close} "
                        f"atr={self.atr.Current.Value:.6g} "
                        f"h1={self.h1_bias} h4={self.h4_bias}"
                    )

        # Add current bar only after evaluating it, preserving shifted features.
        if self.atr.IsReady:
            self.prior_atrs.append(self.atr.Current.Value)
        self.prior_highs.append(bar.High)
        self.prior_lows.append(bar.Low)

    def OnEndOfAlgorithm(self):
        self.Debug(f"DIAGNOSTIC_SIGNAL_COUNTS {self.signal_counts}")
