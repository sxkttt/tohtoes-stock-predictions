"""Backtest replay.

The property that matters most here is the absence of lookahead bias: a
signal at bar i must be computed from bars 0..i only. If future bars leaked
in, the hit rate would be meaninglessly high and the whole feature would be
worse than not having it.
"""
import pytest

from backend import backtest
from conftest import make_candles


def series(n=200, start=100.0, step=0.4):
    return make_candles([start + i * step for i in range(n)])


# --- verdict thresholds ------------------------------------------------------

@pytest.mark.parametrize("score,expected", [
    (0.9, "Strong Buy"),
    (0.5, "Strong Buy"),
    (0.3, "Buy"),
    (0.15, "Buy"),
    (0.0, "Hold"),
    (-0.14, "Hold"),
    (-0.15, "Sell"),
    (-0.6, "Strong Sell"),
])
def test_verdict_thresholds(score, expected):
    assert backtest._verdict_from_score(score) == expected


# --- outcome classification --------------------------------------------------

def test_a_buy_that_rose_is_a_hit():
    result, move = backtest._outcome("Buy", 100.0, 110.0)
    assert result == "hit"
    assert move == pytest.approx(10.0)


def test_a_buy_that_fell_is_a_miss():
    assert backtest._outcome("Buy", 100.0, 90.0)[0] == "miss"


def test_a_sell_that_fell_is_a_hit():
    assert backtest._outcome("Sell", 100.0, 90.0)[0] == "hit"


def test_a_sell_that_rose_is_a_miss():
    assert backtest._outcome("Strong Sell", 100.0, 110.0)[0] == "miss"


def test_moves_inside_the_flat_band_are_not_scored_either_way():
    result, _ = backtest._outcome("Buy", 100.0, 100.2)   # +0.2%, band is 0.5%
    assert result == "flat"


def test_a_hold_is_flat_when_price_barely_moved():
    assert backtest._outcome("Hold", 100.0, 100.1)[0] == "flat"


def test_a_hold_is_a_miss_when_price_moved_a_lot():
    assert backtest._outcome("Hold", 100.0, 120.0)[0] == "miss"


def test_a_zero_entry_price_does_not_divide_by_zero():
    assert backtest._outcome("Buy", 0.0, 10.0) == ("flat", 0.0)


# --- no lookahead ------------------------------------------------------------

def test_signals_only_use_bars_that_had_already_closed(monkeypatch):
    """Every scoring call must receive a window ending at the signal bar --
    never one that includes later bars."""
    candles = series(200)
    seen_lengths = []
    real = backtest.advisor._score_technicals_single_tf

    def spy(window, tf):
        seen_lengths.append(len(window))
        return real(window, tf)

    monkeypatch.setattr(backtest.advisor, "_score_technicals_single_tf", spy)
    backtest._replay(candles, "medium")

    hold = backtest.HOLD_BARS["medium"]
    last_index = len(candles) - hold - 1
    # windows run from WARMUP_BARS..last_index inclusive, length = index + 1
    assert seen_lengths[0] == backtest.WARMUP_BARS + 1
    assert max(seen_lengths) == last_index + 1
    assert max(seen_lengths) < len(candles), "a window reached the end of the series"


def test_every_signal_leaves_a_full_holding_window_ahead_of_it():
    candles = series(200)
    result = backtest._replay(candles, "short")
    hold = backtest.HOLD_BARS["short"]
    times = [c["time"] for c in candles]
    for signal in result["signals"]:
        i = times.index(signal["time"])
        assert i + hold < len(candles)


# --- summary arithmetic ------------------------------------------------------

def test_replay_reports_a_hit_rate_between_0_and_100():
    result = backtest._replay(series(200), "medium")
    assert result["hit_rate"] is None or 0.0 <= result["hit_rate"] <= 100.0


def test_scored_signals_never_exceed_directional_signals():
    result = backtest._replay(series(200), "medium")
    assert result["scored_signals"] <= result["directional_signals"] <= result["total_signals"]


def test_a_relentless_uptrend_makes_buy_signals_pay_off():
    """Sanity check on the plumbing: if price only ever rises, a Buy must
    not come out as a losing call."""
    result = backtest._replay(series(200, step=1.0), "medium")
    buys = result["by_verdict"]["Buy"]
    strong = result["by_verdict"]["Strong Buy"]
    for group in (buys, strong):
        if group["scored"]:
            assert group["hit_rate"] == 100.0


def test_verdict_breakdown_counts_sum_to_the_total():
    result = backtest._replay(series(200), "medium")
    assert sum(v["count"] for v in result["by_verdict"].values()) == result["total_signals"]


def test_edge_is_the_difference_between_hit_rate_and_baseline():
    result = backtest._replay(series(200), "medium")
    if result["edge"] is not None:
        assert result["edge"] == pytest.approx(
            round(result["hit_rate"] - result["baseline_up_rate"], 1)
        )


def test_result_carries_its_own_method_caveats():
    result = backtest._replay(series(200), "medium")
    assert "hold_bars" in result and "interval" in result


def test_every_horizon_has_a_hold_window_and_replay_interval():
    from backend import advisor
    for horizon in advisor.HORIZONS:
        assert horizon in backtest.HOLD_BARS
        assert horizon in backtest.REPLAY_INTERVAL


def test_longer_horizons_hold_for_more_bars():
    assert (backtest.HOLD_BARS["short"]
            < backtest.HOLD_BARS["medium"]
            < backtest.HOLD_BARS["long"])


def test_replay_of_a_flat_series_scores_nothing_as_a_hit(flat_candles):
    """Nothing moves, so every outcome falls inside the flat band and no
    hit rate can be claimed."""
    padded = flat_candles * 2   # enough bars to clear warm-up + hold
    result = backtest._replay(padded, "short")
    assert all(s["result"] == "flat" for s in result["signals"])
    assert result["hit_rate"] is None
