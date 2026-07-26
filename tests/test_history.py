"""Symbol translation and interval-compatibility clamping.

Network calls are not exercised here -- only the pure routing logic that
decides which Yahoo range/interval pair a request maps to. Asking Yahoo for
an interval it does not retain for a given range returns an empty chart, so
the clamp is what keeps the UI from silently rendering nothing.
"""
import pytest

from backend import history


# --- symbol translation ------------------------------------------------------

def test_binance_crypto_symbols_are_translated_to_yahoo_form():
    assert history.to_yahoo_symbol("BINANCE:BTCUSDT") == "BTC-USD"
    assert history.to_yahoo_symbol("BINANCE:ETHUSDT") == "ETH-USD"


def test_equity_symbols_pass_through_untouched():
    assert history.to_yahoo_symbol("AAPL") == "AAPL"
    assert history.to_yahoo_symbol("BRK.B") == "BRK.B"


def test_translation_is_case_insensitive_for_the_binance_prefix():
    assert history.to_yahoo_symbol("binance:btcusdt") == "BTC-USD"


# --- preset tables -----------------------------------------------------------

def test_every_display_period_has_a_range_interval_preset():
    assert set(history.RANGE_INTERVAL_PRESETS) == {"1D", "1W", "1M", "3M", "1Y", "5Y"}


def test_every_period_default_interval_is_in_its_own_compat_list():
    """The clamp falls back to the period's default, so that default must
    itself be a legal choice or the fallback would produce an empty chart."""
    for period, (_rng, default) in history.RANGE_INTERVAL_PRESETS.items():
        assert default in history.INTERVAL_COMPAT[period], \
            f"{period} default {default!r} missing from its compat list"


def test_every_period_has_a_compat_list():
    assert set(history.INTERVAL_COMPAT) == set(history.RANGE_INTERVAL_PRESETS)


def test_advisor_intervals_cover_the_selectable_set():
    assert set(history.ADVISOR_INTERVALS) == {"5m", "15m", "1h", "1d", "1wk"}


def test_long_ranges_exclude_intraday_intervals_yahoo_will_not_serve():
    # 1m is only retained ~7 days and 5m ~60 days, so neither may appear on
    # the 3M/1Y/5Y ranges.
    for period in ("3M", "1Y", "5Y"):
        assert "1m" not in history.INTERVAL_COMPAT[period]
        assert "5m" not in history.INTERVAL_COMPAT[period]


def test_five_year_range_only_offers_daily_or_coarser():
    assert history.INTERVAL_COMPAT["5Y"] == ["1d", "1wk"]


# --- the clamp itself --------------------------------------------------------

def resolve(period, interval):
    """Mirror of the branch inside fetch_candles_custom that picks the
    interval, isolated so it can be checked without touching the network."""
    _rng, default = history.RANGE_INTERVAL_PRESETS[period]
    allowed = history.INTERVAL_COMPAT.get(period, [default])
    return interval if interval in allowed else default


@pytest.mark.parametrize("period,requested,expected", [
    ("3M", "1h", "1h"),      # compatible -> honoured
    ("3M", "5m", "1d"),      # too fine for a 3-month range -> clamped
    ("1D", "1m", "1m"),      # compatible
    ("5Y", "1m", "1wk"),     # far too fine -> clamped to the preset default
    ("1Y", "1wk", "1wk"),
    ("1M", "30m", "30m"),
    ("1M", "1m", "1d"),      # 1m not retained 30 days back
])
def test_incompatible_intervals_clamp_to_the_period_default(period, requested, expected):
    assert resolve(period, requested) == expected


def test_an_unknown_interval_clamps_rather_than_being_passed_through():
    assert resolve("1D", "nonsense") == history.RANGE_INTERVAL_PRESETS["1D"][1]


@pytest.mark.parametrize("period", list(history.RANGE_INTERVAL_PRESETS))
def test_clamping_always_yields_a_servable_interval(period):
    for interval in ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "bogus"]:
        assert resolve(period, interval) in history.INTERVAL_COMPAT[period]
