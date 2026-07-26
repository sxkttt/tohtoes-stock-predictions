"""Indicator math, checked against hand-computable cases and known
reference behaviour rather than against the implementation itself."""
import pytest

from backend import indicators
from conftest import candle, make_candles


# --- EMA / SMA ---------------------------------------------------------------

def test_ema_of_constant_series_is_that_constant():
    assert indicators.ema([5.0] * 50, 10) == pytest.approx(5.0)


def test_ema_seeds_on_first_value_and_tracks_alpha():
    # alpha = 2/(period+1) = 0.5 for period 3
    # out[0]=0, out[1]=0.5*10+0.5*0=5, out[2]=0.5*10+0.5*5=7.5
    series = indicators.ema_series([0.0, 10.0, 10.0], 3)
    assert list(series) == pytest.approx([0.0, 5.0, 7.5])


def test_ema_weights_recent_values_more_than_sma():
    closes = [1.0] * 20 + [100.0] * 5
    assert indicators.ema(closes, 10) > indicators.sma(closes, 10)


def test_sma_is_mean_of_last_period_values():
    assert indicators.sma([1, 2, 3, 4, 100], 4) == pytest.approx((2 + 3 + 4 + 100) / 4)


def test_sma_returns_none_when_not_enough_data():
    assert indicators.sma([1, 2], 5) is None


def test_ema_of_empty_series_is_none():
    assert indicators.ema([], 10) is None


# --- RSI ---------------------------------------------------------------------

def test_rsi_is_100_when_every_bar_gains():
    # No losses at all -> avg_loss 0 -> RSI pinned at 100.
    assert indicators.rsi([float(i) for i in range(40)], 14) == 100.0


def test_rsi_is_0_when_every_bar_loses():
    assert indicators.rsi([float(40 - i) for i in range(40)], 14) == pytest.approx(0.0)


def test_rsi_of_flat_series_is_100_by_convention():
    # Wilder's formula has avg_loss == 0 here; the guard returns 100 rather
    # than dividing by zero. Pinning the behaviour so it can't drift silently.
    assert indicators.rsi([50.0] * 40, 14) == 100.0


def test_rsi_needs_period_plus_one_bars():
    assert indicators.rsi([1.0] * 14, 14) is None
    assert indicators.rsi([float(i) for i in range(15)], 14) is not None


def test_rsi_stays_within_bounds_on_mixed_data():
    closes = [100, 102, 101, 105, 103, 108, 107, 110, 108, 112,
              111, 115, 113, 118, 116, 120, 119, 122, 120, 125]
    value = indicators.rsi(closes, 14)
    assert 0.0 <= value <= 100.0


# --- MACD --------------------------------------------------------------------

def test_macd_histogram_equals_macd_minus_signal():
    closes = [100 + i * 0.7 for i in range(80)]
    result = indicators.macd(closes)
    assert result["histogram"] == pytest.approx(result["macd"] - result["signal"])


def test_macd_is_positive_in_an_uptrend_and_negative_in_a_downtrend():
    up = indicators.macd([100 + i for i in range(80)])
    down = indicators.macd([180 - i for i in range(80)])
    assert up["macd"] > 0
    assert down["macd"] < 0


def test_macd_returns_none_fields_when_series_too_short():
    result = indicators.macd([1.0] * 10)
    assert result == {"macd": None, "signal": None, "histogram": None}


# --- Bollinger ---------------------------------------------------------------

def test_bollinger_bands_straddle_the_middle_band():
    closes = [100 + i * 0.3 for i in range(60)]
    b = indicators.bollinger(closes, 20, 2)
    assert b["lower"] < b["middle"] < b["upper"]


def test_bollinger_percent_b_is_half_when_bands_collapse():
    # Zero variance would divide by zero; the guard returns 0.5.
    b = indicators.bollinger([100.0] * 40, 20, 2)
    assert b["upper"] == b["lower"] == b["middle"] == 100.0
    assert b["percent_b"] == 0.5


def test_bollinger_percent_b_exceeds_one_above_the_upper_band():
    closes = [100.0] * 19 + [200.0]
    b = indicators.bollinger(closes, 20, 2)
    assert b["percent_b"] > 1.0


def test_bollinger_returns_none_fields_when_too_short():
    b = indicators.bollinger([1.0] * 5, 20, 2)
    assert b["upper"] is None and b["percent_b"] is None


# --- ATR ---------------------------------------------------------------------

def test_atr_of_constant_range_equals_that_range():
    # Every bar spans exactly 4.0 and never gaps, so TR == 4.0 throughout.
    candles = [candle(o=100, h=102, l=98, c=100) for _ in range(30)]
    assert indicators.atr(candles, 14) == pytest.approx(4.0)


def test_atr_accounts_for_gaps_beyond_the_bar_range():
    # A bar that opens far above the prior close has a true range larger
    # than its own high-low span.
    candles = [candle(o=100, h=101, l=99, c=100) for _ in range(20)]
    candles.append(candle(o=150, h=151, l=149, c=150))
    assert indicators.atr(candles, 14) > 2.0


def test_atr_returns_none_when_not_enough_candles():
    assert indicators.atr([candle(1, 2, 0, 1)] * 10, 14) is None


def test_atr_of_zero_range_candles_is_zero():
    candles = [candle(o=100, h=100, l=100, c=100) for _ in range(30)]
    assert indicators.atr(candles, 14) == 0.0


# --- Stochastic / ADX / OBV / VWAP -------------------------------------------

def test_stochastic_is_100_at_the_top_of_its_range():
    closes = list(range(1, 41))
    candles = make_candles([float(c) for c in closes], spread=0.0)
    result = indicators.stochastic(candles, 14, 3)
    assert result["k"] == pytest.approx(100.0)


def test_stochastic_handles_a_flat_window_without_dividing_by_zero():
    candles = [candle(o=10, h=10, l=10, c=10) for _ in range(30)]
    result = indicators.stochastic(candles, 14, 3)
    assert result["k"] == 50.0


def test_adx_is_high_in_a_strong_trend_and_low_when_choppy(rising_candles, choppy_candles):
    trend = indicators.adx(rising_candles, 14)["adx"]
    chop = indicators.adx(choppy_candles, 14)["adx"]
    assert trend > chop


def test_adx_direction_indicators_agree_with_trend(rising_candles, falling_candles):
    up = indicators.adx(rising_candles, 14)
    down = indicators.adx(falling_candles, 14)
    assert up["plus_di"] > up["minus_di"]
    assert down["minus_di"] > down["plus_di"]


def test_adx_returns_none_when_not_enough_candles():
    assert indicators.adx(make_candles([1.0] * 10), 14)["adx"] is None


def test_obv_accumulates_on_up_closes_and_sheds_on_down_closes():
    candles = [
        candle(o=10, h=11, l=9, c=10, v=100),
        candle(o=10, h=12, l=10, c=11, v=50),   # up   -> +50
        candle(o=11, h=11, l=9, c=10, v=30),    # down -> -30
        candle(o=10, h=11, l=9, c=10, v=70),    # flat -> unchanged
    ]
    assert indicators.obv_series(candles) == [0.0, 50.0, 20.0, 20.0]


def test_vwap_is_volume_weighted_not_a_plain_average():
    candles = [
        candle(o=10, h=10, l=10, c=10, v=1),      # typical 10, weight 1
        candle(o=20, h=20, l=20, c=20, v=99),     # typical 20, weight 99
    ]
    result = indicators.vwap(candles)
    assert result == pytest.approx((10 * 1 + 20 * 99) / 100)
    assert result > 15  # a plain mean would be exactly 15


def test_vwap_is_none_without_volume():
    candles = [candle(o=10, h=10, l=10, c=10, v=0) for _ in range(5)]
    assert indicators.vwap(candles) is None


def test_rsi_series_has_one_entry_per_bar_with_warmup_nones():
    closes = [100 + i for i in range(40)]
    series = indicators.rsi_series(closes, 14)
    assert len(series) == len(closes)
    assert series[13] is None          # still warming up
    assert series[14] is not None      # first computable bar
    assert all(v is None or 0 <= v <= 100 for v in series)
