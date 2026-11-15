from AlgorithmImports import *
from datetime import timedelta


class AtrMtfSignalDiagnostics(QCAlgorithm):
    """Signal-only LEAN port for closed-bar synchronization checks.

    No orders are submitted in this phase. M15 ATR breakout signals are
    confirmed by the latest fully closed H1 and H4 EMA trend states.
    """

    def Initialize(self):
        self.SetStartDate(2025, 9, 1)
        self.SetEndDate(2025, 9, 8)
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
        self.h1_fast = ExponentialMovingAverage(50)
        self.h1_slow = ExponentialMovingAverage(200)
        self.h4_fast = ExponentialMovingAverage(50)
        self.h4_slow = ExponentialMovingAverage(200)

        self.RegisterIndicator(self.symbol, self.atr, self.m15)
        self.RegisterIndicator(self.symbol, self.h1_fast, self.h1)
        self.RegisterIndicator(self.symbol, self.h1_slow, self.h1)
        self.RegisterIndicator(self.symbol, self.h4_fast, self.h4)
        self.RegisterIndicator(self.symbol, self.h4_slow, self.h4)

        self.m15.DataConsolidated += self.OnM15
        self.h1.DataConsolidated += self.OnH1
        self.h4.DataConsolidated += self.OnH4

        self.last_h1_end = None
        self.last_h4_end = None
        self.previous_m15_high = None
        self.previous_m15_low = None
        self.SetWarmUp(timedelta(days=45))

    def OnH1(self, sender, bar):
        # The consolidator callback receives a completed H1 TradeBar.
        self.last_h1_end = bar.EndTime

    def OnH4(self, sender, bar):
        # The consolidator callback receives a completed H4 TradeBar.
        self.last_h4_end = bar.EndTime

    def OnM15(self, sender, bar):
        if self.IsWarmingUp or not self.atr.IsReady:
            self._remember_m15(bar)
            return

        # Reject context bars that are not already closed at this M15 end.
        if self.last_h1_end is None or self.last_h4_end is None:
            self._remember_m15(bar)
            return
        if self.last_h1_end > bar.EndTime or self.last_h4_end > bar.EndTime:
            self._remember_m15(bar)
            return
        if not all(x.IsReady for x in (self.h1_fast, self.h1_slow,
                                       self.h4_fast, self.h4_slow)):
            self._remember_m15(bar)
            return
        if self.previous_m15_high is None or self.previous_m15_low is None:
            self._remember_m15(bar)
            return

        bullish_context = (self.h1_fast.Current.Value > self.h1_slow.Current.Value
                           and self.h4_fast.Current.Value > self.h4_slow.Current.Value)
        bearish_context = (self.h1_fast.Current.Value < self.h1_slow.Current.Value
                           and self.h4_fast.Current.Value < self.h4_slow.Current.Value)

        # Diagnostic only. Exact ATR breakout threshold is not ported yet.
        bullish_breakout = bar.Close > self.previous_m15_high
        bearish_breakout = bar.Close < self.previous_m15_low

        if bullish_context and bullish_breakout:
            self.Debug(f"DIAGNOSTIC LONG {bar.EndTime} close={bar.Close} ATR={self.atr.Current.Value}")
        elif bearish_context and bearish_breakout:
            self.Debug(f"DIAGNOSTIC SHORT {bar.EndTime} close={bar.Close} ATR={self.atr.Current.Value}")

        self._remember_m15(bar)

    def _remember_m15(self, bar):
        self.previous_m15_high = bar.High
        self.previous_m15_low = bar.Low
