"""Candlestick pattern detection and support/resistance geometry.

Each detector is fed a textbook example of its own shape and checked that it
fires; the trend-sensitive ones are also checked that they do *not* fire in
the wrong trend context (a Hammer and a Hanging Man are the same shape --
only the preceding trend distinguishes them).
"""
import pytest

from backend import patterns
from conftest import candle, make_candles


def names_in(candles):
    return {p["pattern"] for p in patterns.detect_candlestick_patterns(candles)}


def downtrend(n=8, start=140.0, step=4.0):
    """A clean run of falling candles to use as leading context."""
    out = []
    price = start
    for _ in range(n):
        out.append(candle(o=price, h=price + 0.4, l=price - step - 0.4, c=price - step))
        price -= step
    return out


def uptrend(n=8, start=100.0, step=4.0):
    out = []
    price = start
    for _ in range(n):
        out.append(candle(o=price, h=price + step + 0.4, l=price - 0.4, c=price + step))
        price += step
    return out


# The hammer family needs a small-but-real body (a doji-sized body is
# classified as a Dragonfly/Gravestone Doji instead, which is a different
# signal), one shadow at least twice the body, and a negligible shadow on
# the far side. These builders produce exactly that geometry: range 10,
# body 2, long shadow 7.5, short shadow 0.5.

def hammer_candle(base):
    """Small real body at the top of the range, long lower shadow."""
    return candle(o=base - 2.5, h=base, l=base - 10, c=base - 0.5)


def star_candle(base):
    """Small real body at the bottom of the range, long upper shadow."""
    return candle(o=base + 2.5, h=base + 10, l=base, c=base + 0.5)


# --- individual shapes -------------------------------------------------------

def test_doji_is_detected_when_open_and_close_coincide():
    series = make_candles([100.0] * 6)
    series.append(candle(o=100, h=104, l=96, c=100.05))
    assert any("Doji" in n for n in names_in(series))


def test_marubozu_is_detected_on_a_full_bodied_candle():
    series = make_candles([100.0] * 6)
    series.append(candle(o=100, h=110.05, l=99.95, c=110))
    assert "Bullish Marubozu" in names_in(series)


def test_hammer_is_detected_after_a_downtrend():
    series = downtrend()
    series.append(hammer_candle(series[-1]["close"]))
    assert "Hammer" in names_in(series)


def test_the_same_shape_after_an_uptrend_is_a_hanging_man_not_a_hammer():
    series = uptrend()
    # Offset so the small body clears the prior candle's body -- otherwise
    # the candle is genuinely a Harami first, and the detector (correctly)
    # reports the two-candle pattern rather than the single-candle one.
    series.append(hammer_candle(series[-1]["close"] + 3))
    found = names_in(series)
    assert "Hanging Man" in found
    assert "Hammer" not in found


def test_shooting_star_is_detected_after_an_uptrend():
    series = uptrend()
    series.append(star_candle(series[-1]["close"]))
    assert "Shooting Star" in names_in(series)


def test_the_same_shape_after_a_downtrend_is_an_inverted_hammer():
    series = downtrend()
    series.append(star_candle(series[-1]["close"] - 3))
    found = names_in(series)
    assert "Inverted Hammer" in found
    assert "Shooting Star" not in found


def test_a_doji_sized_body_with_a_long_lower_shadow_is_not_a_hammer():
    """The hammer detector deliberately excludes doji-level bodies so
    'indecision' and 'reversal candle' stay distinct signals."""
    series = downtrend()
    last = series[-1]["close"]
    series.append(candle(o=last - 2.5, h=last, l=last - 10, c=last - 2.45))
    found = names_in(series)
    assert "Hammer" not in found
    assert any("Doji" in n for n in found)


def test_bullish_engulfing_requires_the_body_to_swallow_the_previous_one():
    series = make_candles([100.0] * 5)
    series.append(candle(o=100, h=100.5, l=97, c=97.5))     # small bearish
    series.append(candle(o=97, h=102.5, l=96.5, c=102))     # larger bullish engulfing it
    assert "Bullish Engulfing" in names_in(series)


def test_bearish_engulfing_is_detected():
    series = make_candles([100.0] * 5)
    series.append(candle(o=100, h=103, l=99.5, c=102.5))
    series.append(candle(o=103, h=103.5, l=99, c=99.5))
    assert "Bearish Engulfing" in names_in(series)


def test_three_white_soldiers_needs_three_rising_closes():
    series = make_candles([100.0] * 5)
    series.append(candle(o=100, h=105.2, l=99.8, c=105))
    series.append(candle(o=103, h=110.2, l=102.8, c=110))
    series.append(candle(o=108, h=115.2, l=107.8, c=115))
    assert "Three White Soldiers" in names_in(series)


def test_three_black_crows_needs_three_falling_closes():
    series = make_candles([130.0] * 5)
    series.append(candle(o=130, h=130.2, l=124.8, c=125))
    series.append(candle(o=127, h=127.2, l=119.8, c=120))
    series.append(candle(o=122, h=122.2, l=114.8, c=115))
    assert "Three Black Crows" in names_in(series)


# --- detector contract -------------------------------------------------------

def test_no_pattern_falls_below_the_strength_floor():
    series = make_candles([100 + (i % 5) for i in range(80)])
    for p in patterns.detect_candlestick_patterns(series):
        assert p["strength"] >= patterns.MIN_STRENGTH


def test_every_pattern_carries_the_fields_the_ui_renders():
    series = downtrend()
    series.append(hammer_candle(series[-1]["close"]))
    found = patterns.detect_candlestick_patterns(series)
    assert found, "expected at least one pattern from a textbook hammer"
    for p in found:
        assert set(p) >= {"pattern", "direction", "strength", "confidence", "time"}
        assert p["direction"] in {"bullish", "bearish", "neutral"}
        assert p["confidence"] in {"high", "medium", "low"}


def test_confidence_tiers_follow_strength_thresholds():
    assert patterns._tier(0.9) == "high"
    assert patterns._tier(0.5) == "medium"
    assert patterns._tier(0.2) == "low"


def test_detection_on_empty_and_tiny_inputs_does_not_raise():
    assert patterns.detect_candlestick_patterns([]) == []
    assert isinstance(patterns.detect_candlestick_patterns([candle(1, 2, 0, 1)]), list)


def test_patterns_are_returned_in_chronological_order():
    series = make_candles([100 + (i % 7) * 2 for i in range(120)])
    found = patterns.detect_candlestick_patterns(series)
    times = [p["time"] for p in found]
    assert times == sorted(times)


# --- support / resistance / trend --------------------------------------------

def test_trend_is_up_for_a_rising_series(rising_candles):
    result = patterns.support_resistance_and_trend(rising_candles)
    assert result["trend"]["direction"] == "up"


def test_trend_is_down_for_a_falling_series(falling_candles):
    result = patterns.support_resistance_and_trend(falling_candles)
    assert result["trend"]["direction"] == "down"


def test_levels_lie_within_the_observed_price_range(rising_candles):
    result = patterns.support_resistance_and_trend(rising_candles)
    lo = min(c["low"] for c in rising_candles)
    hi = max(c["high"] for c in rising_candles)
    for level in result.get("levels") or []:
        assert lo <= level <= hi


def test_analyze_returns_both_overlay_and_markers(rising_candles):
    result = patterns.analyze(rising_candles)
    assert set(result) == {"overlay", "candlestick_markers"}
    assert "trend" in result["overlay"]


def test_support_resistance_handles_a_short_series_without_raising():
    result = patterns.support_resistance_and_trend(make_candles([100.0, 101.0, 102.0]))
    assert isinstance(result, dict)
