"""Pattern outcome statistics.

The headline property: a pattern's follow-through must be reported against
the base rate of the same series. In a series that only ever rose, a bullish
pattern showing 100% follow-through has zero edge, and the numbers must say
so rather than flattering the pattern.
"""
import pytest

from backend import pattern_stats
from conftest import candle, make_candles


def rising(n=300, step=0.4):
    return make_candles([100 + i * step for i in range(n)])


def choppy(n=300):
    return make_candles([100 + (i % 9) * 1.5 for i in range(n)])


# --- forward move ------------------------------------------------------------

def test_forward_move_is_a_percentage_of_the_entry_close():
    candles = make_candles([100.0, 100.0, 110.0])
    assert pattern_stats._forward_move_pct(candles, 0, 2) == pytest.approx(10.0)


def test_forward_move_is_none_past_the_end_of_the_series():
    candles = make_candles([100.0, 101.0])
    assert pattern_stats._forward_move_pct(candles, 1, 5) is None


def test_forward_move_handles_a_zero_entry_price():
    candles = [candle(0, 0, 0, 0), candle(1, 1, 1, 1)]
    assert pattern_stats._forward_move_pct(candles, 0, 1) is None


# --- base rate ---------------------------------------------------------------

def test_base_up_rate_is_100_percent_for_a_series_that_only_rises():
    base = pattern_stats._base_rates(rising(), 5)
    assert base["up_rate"] == 100.0
    assert base["avg_move_pct"] > 0


def test_base_up_rate_is_0_percent_for_a_series_that_only_falls():
    falling = make_candles([200 - i * 0.4 for i in range(300)])
    base = pattern_stats._base_rates(falling, 5)
    assert base["up_rate"] == 0.0


def test_base_rate_of_a_flat_series_has_no_decided_direction(flat_candles):
    base = pattern_stats._base_rates(flat_candles, 5)
    assert base["up_rate"] is None
    assert base["avg_move_pct"] == 0.0


# --- edge vs base rate -------------------------------------------------------

def test_a_bullish_pattern_in_a_relentless_uptrend_shows_no_edge():
    """The whole reason base rates are computed: 100% follow-through in a
    series that always rose is not an edge, and edge_vs_base must be 0."""
    result = pattern_stats.analyse(rising(), lookahead=5)
    bullish = [p for p in result["patterns"]
               if p["direction"] == "bullish" and p["edge_vs_base"] is not None]
    for p in bullish:
        assert p["edge_vs_base"] == 0.0, f"{p['pattern']} claimed edge in a pure uptrend"


def test_edge_is_reported_relative_to_the_base_rate_not_absolutely():
    result = pattern_stats.analyse(choppy(), lookahead=5)
    base = result["base_rate"]["up_rate"]
    for p in result["patterns"]:
        if p["direction"] == "bullish" and p["edge_vs_base"] is not None:
            assert p["edge_vs_base"] == pytest.approx(round(p["up_rate"] - base, 1))


# --- per-pattern arithmetic --------------------------------------------------

def test_rates_stay_within_bounds_and_extremes_bracket_the_average():
    result = pattern_stats.analyse(choppy(), lookahead=5)
    assert result["patterns"], "expected some patterns in a choppy series"
    for p in result["patterns"]:
        assert 0.0 <= p["follow_through_rate"] <= 100.0
        assert p["up_rate"] is None or 0.0 <= p["up_rate"] <= 100.0
        assert p["worst_pct"] <= p["avg_move_pct"] <= p["best_pct"]
        assert p["occurrences"] >= 1


def test_small_samples_are_flagged_unreliable():
    result = pattern_stats.analyse(choppy(), lookahead=5)
    for p in result["patterns"]:
        assert p["reliable"] == (p["occurrences"] >= pattern_stats.MIN_OCCURRENCES)


def test_unreliable_patterns_never_outrank_reliable_ones():
    """A 100% rate from two occurrences must not top the table."""
    result = pattern_stats.analyse(choppy(), lookahead=5)
    flags = [p["reliable"] for p in result["patterns"]]
    assert flags == sorted(flags, reverse=True)


def test_patterns_too_close_to_the_end_are_excluded():
    """A pattern on the final bar has no outcome yet and must not be
    counted as though it did."""
    candles = choppy(60)
    total_from_detector = len(
        pattern_stats.patterns.detect_candlestick_patterns(candles)
    )
    counted = sum(p["occurrences"] for p in pattern_stats.analyse(candles, 5)["patterns"])
    assert counted <= total_from_detector


def test_lookahead_is_echoed_back_in_the_result():
    result = pattern_stats.analyse(choppy(), lookahead=7)
    assert result["lookahead_bars"] == 7


def test_a_longer_lookahead_changes_the_measured_moves():
    short = pattern_stats.analyse(rising(), lookahead=2)
    long_ = pattern_stats.analyse(rising(), lookahead=10)
    assert short["base_rate"]["avg_move_pct"] < long_["base_rate"]["avg_move_pct"]


def test_analyse_of_an_empty_series_does_not_raise():
    result = pattern_stats.analyse([], lookahead=5)
    assert result["patterns"] == []


def test_neutral_patterns_are_scored_on_staying_put():
    """Indecision patterns claim no direction, so follow-through means
    price went nowhere -- in a strong trend they should score poorly."""
    result = pattern_stats.analyse(rising(300, step=1.0), lookahead=5)
    neutral = [p for p in result["patterns"] if p["direction"] == "neutral"]
    for p in neutral:
        assert p["follow_through_rate"] == 0.0
