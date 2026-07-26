"""Advisor scoring engine.

The most important property here is the price-ladder ordering invariant:
buy tiers must sit at or below the current price, sell tiers at or above it,
and each ladder must be monotonic. An ordering bug there is not cosmetic --
it would tell someone to sell below their own stop-loss.
"""
import pytest

from backend import advisor
from conftest import candle, make_candles


def zones(candles, overlay=None, price=None, horizon="medium"):
    price = price if price is not None else candles[-1]["close"]
    return advisor._price_zones(candles, overlay or {"levels": []}, price, horizon)


# --- price ladder ordering ---------------------------------------------------

@pytest.mark.parametrize("horizon", ["short", "medium", "long"])
def test_buy_ladder_is_ordered_and_at_or_below_current_price(rising_candles, horizon):
    price = rising_candles[-1]["close"]
    result = zones(rising_candles, price=price, horizon=horizon)
    prices = [t["price"] for t in result["buy"]]
    assert prices == sorted(prices), "buy tiers must ascend strong -> mid -> light"
    assert all(p <= price + 0.01 for p in prices)


@pytest.mark.parametrize("horizon", ["short", "medium", "long"])
def test_sell_ladder_is_strictly_increasing_and_above_current_price(rising_candles, horizon):
    price = rising_candles[-1]["close"]
    result = zones(rising_candles, price=price, horizon=horizon)
    prices = [t["price"] for t in result["sell"]]
    assert prices == sorted(prices)
    # Distinct tiers: a collapsed ladder (all three equal) is the bug that
    # shipped once already, so equality is explicitly rejected here.
    assert len(set(prices)) == 3, f"sell tiers collapsed onto each other: {prices}"
    assert all(p >= price - 0.01 for p in prices)


@pytest.mark.parametrize("horizon", ["short", "medium", "long"])
def test_stop_loss_sits_below_the_strongest_buy(rising_candles, horizon):
    result = zones(rising_candles, horizon=horizon)
    assert result["stop_loss"] < result["buy"][0]["price"]


def test_a_distant_resistance_cannot_collapse_the_sell_ladder(rising_candles):
    """Regression: one far-away resistance level used to dominate all three
    max() calls, making every sell tier identical."""
    price = rising_candles[-1]["close"]
    overlay = {"levels": [price + 500.0]}
    prices = [t["price"] for t in zones(rising_candles, overlay, price)["sell"]]
    assert len(set(prices)) == 3


def test_longer_horizons_widen_the_sell_ladder(rising_candles):
    price = rising_candles[-1]["close"]
    short = zones(rising_candles, price=price, horizon="short")["sell"][-1]["price"]
    medium = zones(rising_candles, price=price, horizon="medium")["sell"][-1]["price"]
    long_ = zones(rising_candles, price=price, horizon="long")["sell"][-1]["price"]
    assert short < medium < long_


def test_longer_horizons_deepen_the_buy_ladder(rising_candles):
    price = rising_candles[-1]["close"]
    short = zones(rising_candles, price=price, horizon="short")["buy"][0]["price"]
    long_ = zones(rising_candles, price=price, horizon="long")["buy"][0]["price"]
    # buy_strong is min(support, price - mult*ATR): when a nearby support
    # level dominates both, the tiers legitimately coincide, so the
    # guarantee is that a longer horizon never buys *shallower*.
    assert long_ <= short


def test_unknown_horizon_falls_back_to_medium(rising_candles):
    price = rising_candles[-1]["close"]
    assert zones(rising_candles, price=price, horizon="nonsense") == \
           zones(rising_candles, price=price, horizon="medium")


def test_flat_prices_still_produce_a_separated_ladder(flat_candles):
    """A zero ATR would collapse every tier onto the current price; the
    implementation floors ATR at 0.1% of price to prevent that."""
    price = flat_candles[-1]["close"]
    result = zones(flat_candles, price=price)
    sells = [t["price"] for t in result["sell"]]
    assert len(set(sells)) == 3
    assert result["stop_loss"] < price


def test_ladder_holds_in_a_downtrend_too(falling_candles):
    price = falling_candles[-1]["close"]
    result = zones(falling_candles, price=price)
    buys = [t["price"] for t in result["buy"]]
    sells = [t["price"] for t in result["sell"]]
    assert buys == sorted(buys)
    assert sells == sorted(sells)
    assert buys[-1] <= sells[0]


def test_light_buy_tier_is_the_current_price(rising_candles):
    price = rising_candles[-1]["close"]
    result = zones(rising_candles, price=price)
    assert result["buy"][-1]["price"] == pytest.approx(round(price, 2))


# --- horizon configuration ---------------------------------------------------

def test_every_horizon_has_multipliers_and_a_label():
    for horizon in advisor.HORIZONS:
        assert horizon in advisor.HORIZON_MULTIPLIERS
        assert advisor.HORIZON_LABELS.get(horizon)


def test_horizon_multipliers_grow_monotonically_with_horizon_length():
    short = advisor.HORIZON_MULTIPLIERS["short"]
    medium = advisor.HORIZON_MULTIPLIERS["medium"]
    long_ = advisor.HORIZON_MULTIPLIERS["long"]
    for key in ("buy_strong", "sell_mid", "sell_stretch"):
        assert short[key] < medium[key] < long_[key], f"{key} not monotonic"


def test_clamp_bounds_scores_to_the_unit_interval():
    assert advisor._clamp(5.0) == 1.0
    assert advisor._clamp(-5.0) == -1.0
    assert advisor._clamp(0.25) == 0.25


# --- degraded inputs must not raise -----------------------------------------

def test_fundamentals_scoring_survives_missing_context():
    """Missing fundamentals must score neutral and say so, rather than
    silently contributing a real score or returning nothing at all."""
    result = advisor._score_fundamentals(None, 100.0)
    assert result["score"] == 0.0
    assert len(result["factors"]) == 1
    assert "No fundamentals data" in result["factors"][0]["detail"]


def test_fundamentals_scoring_survives_an_all_none_metrics_dict():
    """Crypto symbols return a populated dict whose every field is None --
    a 'is the dict present' check is not enough."""
    context = {"metrics": {k: None for k in
                           ("pe_ttm", "ps_ttm", "revenue_growth", "net_margin",
                            "debt_to_equity", "beta")}}
    result = advisor._score_fundamentals(context, 100.0)
    assert result["score"] == 0.0


def test_street_scoring_survives_missing_context():
    result = advisor._score_street(None, None)
    assert result["score"] == 0.0


def test_macro_scoring_survives_missing_data():
    result = advisor._score_macro(None, None)
    assert result["score"] == 0.0


def test_technical_scoring_survives_a_too_short_series():
    result = advisor._score_technicals_single_tf(make_candles([100.0, 101.0]), "1d")
    assert -1.0 <= result["score"] <= 1.0


def test_horizon_weights_each_sum_to_one():
    for horizon, cfg in advisor.HORIZON_CONFIG.items():
        assert sum(cfg["weights"].values()) == pytest.approx(1.0),             f"{horizon} weights do not sum to 1"


def test_horizon_timeframe_blends_each_sum_to_one():
    for horizon, cfg in advisor.HORIZON_CONFIG.items():
        total = sum(w for _tf, w in cfg["timeframes"])
        assert total == pytest.approx(1.0), f"{horizon} timeframe weights do not sum to 1"


def test_each_horizon_prices_zones_off_one_of_its_own_timeframes():
    for horizon, cfg in advisor.HORIZON_CONFIG.items():
        tfs = [tf for tf, _w in cfg["timeframes"]]
        assert cfg["zone_tf"] in tfs, f"{horizon} zone_tf {cfg['zone_tf']!r} not among {tfs}"
