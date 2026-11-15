"""Pure, engine-independent rules shared by LEAN and unit tests."""
from statistics import mean


def atr_breakout_direction(close, current_atr, prior_highs, prior_lows,
                            prior_atrs, expansion=1.10):
    """Return +1/-1/0 using only the 20 prior bars and 50 prior ATR values."""
    if len(prior_highs) != 20 or len(prior_lows) != 20 or len(prior_atrs) != 50:
        return 0
    if expansion <= 1.0:
        raise ValueError("expansion must be greater than 1")
    if current_atr <= mean(prior_atrs) * expansion:
        return 0
    if close > max(prior_highs):
        return 1
    if close < min(prior_lows):
        return -1
    return 0


def mtf_context_agrees(direction, h1_bias, h4_bias,
                       h1_end, h4_end, decision_end):
    """Require matching H1/H4 direction and timestamps no later than M15 close."""
    if direction not in (-1, 1) or h1_end is None or h4_end is None:
        return False
    if h1_end > decision_end or h4_end > decision_end:
        return False
    return h1_bias == direction and h4_bias == direction


def is_selected_utc_hour(hour):
    """Exploratory session variant: only 07:00 and 15:00 UTC."""
    return hour in (7, 15)
