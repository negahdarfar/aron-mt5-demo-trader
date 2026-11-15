import unittest
from datetime import datetime, timedelta, timezone
from strategy_rules import (
    atr_breakout_direction, mtf_context_agrees, is_selected_utc_hour,
)


class AtrRuleTests(unittest.TestCase):
    def setUp(self):
        self.highs = [1.10] * 20
        self.lows = [1.00] * 20
        self.atrs = [0.001] * 50

    def test_bullish_breakout_uses_prior_window(self):
        self.assertEqual(atr_breakout_direction(1.11, 0.00111, self.highs, self.lows, self.atrs), 1)

    def test_bearish_breakout(self):
        self.assertEqual(atr_breakout_direction(0.99, 0.00111, self.highs, self.lows, self.atrs), -1)

    def test_expansion_threshold_is_strict(self):
        self.assertEqual(atr_breakout_direction(1.11, 0.00110, self.highs, self.lows, self.atrs), 0)

    def test_incomplete_history_fails_closed(self):
        self.assertEqual(atr_breakout_direction(1.11, 0.01, self.highs[:-1], self.lows, self.atrs), 0)

    def test_no_breakout_inside_channel(self):
        self.assertEqual(atr_breakout_direction(1.05, 0.01, self.highs, self.lows, self.atrs), 0)


class MtfCausalityTests(unittest.TestCase):
    def setUp(self):
        self.decision = datetime(2025, 9, 1, 10, 15, tzinfo=timezone.utc)

    def test_closed_aligned_context_passes(self):
        self.assertTrue(mtf_context_agrees(
            1, 1, 1, self.decision - timedelta(minutes=15),
            self.decision - timedelta(hours=2), self.decision,
        ))

    def test_future_h1_context_is_rejected(self):
        self.assertFalse(mtf_context_agrees(
            1, 1, 1, self.decision + timedelta(minutes=15),
            self.decision - timedelta(hours=2), self.decision,
        ))

    def test_opposite_or_mixed_bias_is_rejected(self):
        self.assertFalse(mtf_context_agrees(
            1, 1, -1, self.decision, self.decision, self.decision,
        ))

    def test_session_hours(self):
        self.assertTrue(is_selected_utc_hour(7))
        self.assertTrue(is_selected_utc_hour(15))
        self.assertFalse(is_selected_utc_hour(8))


if __name__ == "__main__":
    unittest.main()
