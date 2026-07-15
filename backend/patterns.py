"""Pattern detection: swing-based trend lines / support & resistance,
plus classic single/multi-candle pattern recognition with a confidence
score (low / medium / high) for how strongly each match fits the ideal
textbook shape."""
import numpy as np
from scipy.signal import argrelextrema


def _swings(closes: np.ndarray, order: int = 3):
    highs_idx = argrelextrema(closes, np.greater_equal, order=order)[0]
    lows_idx = argrelextrema(closes, np.less_equal, order=order)[0]
    # de-duplicate consecutive equal-value plateaus
    highs_idx = np.array(sorted(set(highs_idx.tolist())))
    lows_idx = np.array(sorted(set(lows_idx.tolist())))
    return highs_idx, lows_idx


def _fit_line(idx: np.ndarray, vals: np.ndarray):
    if len(idx) < 2:
        return None
    slope, intercept = np.polyfit(idx, vals, 1)
    return float(slope), float(intercept)


def support_resistance_and_trend(candles: list[dict], order: int = 3):
    """candles: list of {time, open, high, low, close, volume} oldest->newest.
    Returns a dict describing overlay lines the frontend can draw."""
    n = len(candles)
    if n < max(10, order * 3):
        return {"resistance": None, "support": None, "trend": None, "levels": []}

    closes = np.array([c["close"] for c in candles], dtype=float)
    times = [c["time"] for c in candles]

    highs_idx, lows_idx = _swings(closes, order=order)

    result = {"resistance": None, "support": None, "trend": None, "levels": []}

    # Resistance line: fit through swing highs (most recent 6)
    if len(highs_idx) >= 2:
        recent_highs_idx = highs_idx[-6:]
        fit = _fit_line(recent_highs_idx, closes[recent_highs_idx])
        if fit:
            slope, intercept = fit
            result["resistance"] = {
                "start": {"time": times[int(recent_highs_idx[0])], "value": float(slope * recent_highs_idx[0] + intercept)},
                "end": {"time": times[n - 1], "value": float(slope * (n - 1) + intercept)},
            }

    # Support line: fit through swing lows (most recent 6)
    if len(lows_idx) >= 2:
        recent_lows_idx = lows_idx[-6:]
        fit = _fit_line(recent_lows_idx, closes[recent_lows_idx])
        if fit:
            slope, intercept = fit
            result["support"] = {
                "start": {"time": times[int(recent_lows_idx[0])], "value": float(slope * recent_lows_idx[0] + intercept)},
                "end": {"time": times[n - 1], "value": float(slope * (n - 1) + intercept)},
            }

    # Overall trend line: linear regression over all closes
    all_idx = np.arange(n)
    slope, intercept = np.polyfit(all_idx, closes, 1)
    result["trend"] = {
        "start": {"time": times[0], "value": float(intercept)},
        "end": {"time": times[n - 1], "value": float(slope * (n - 1) + intercept)},
        "direction": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
    }

    # Horizontal support/resistance levels: cluster swing high/low price values
    swing_prices = np.concatenate([closes[highs_idx], closes[lows_idx]]) if len(highs_idx) or len(lows_idx) else np.array([])
    levels = []
    if len(swing_prices) > 0:
        sorted_p = np.sort(swing_prices)
        cluster = [sorted_p[0]]
        tol = max(closes) * 0.0015 if len(closes) else 0.01
        for p in sorted_p[1:]:
            if p - cluster[-1] <= tol:
                cluster.append(p)
            else:
                if len(cluster) >= 2:
                    levels.append(float(np.mean(cluster)))
                cluster = [p]
        if len(cluster) >= 2:
            levels.append(float(np.mean(cluster)))
    result["levels"] = levels[:6]

    return result


# --- candle geometry helpers ---------------------------------------------

def _o(c): return c["open"]
def _h(c): return c["high"]
def _l(c): return c["low"]
def _cl(c): return c["close"]
def _body(c): return abs(_cl(c) - _o(c))
def _range(c): return max(_h(c) - _l(c), 1e-9)
def _upper_wick(c): return _h(c) - max(_o(c), _cl(c))
def _lower_wick(c): return min(_o(c), _cl(c)) - _l(c)
def _is_bullish(c): return _cl(c) > _o(c)
def _is_bearish(c): return _cl(c) < _o(c)
def _body_ratio(c): return _body(c) / _range(c)
def _mid(c): return (_o(c) + _cl(c)) / 2


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _is_doji(c): return _body_ratio(c) <= 0.1
def _is_bullish_marubozu(c): return _is_bullish(c) and _body_ratio(c) >= 0.9
def _is_bearish_marubozu(c): return _is_bearish(c) and _body_ratio(c) >= 0.9


def _is_hammer_shape(c):
    # Textbook hammer/shooting-star geometry: small-but-real body, one shadow
    # at least 2x the body (not just a range-relative ratio -- this is what
    # actually distinguishes a hammer from an ordinary small-bodied candle),
    # and a negligible shadow on the opposite side. Doji-level bodies are
    # excluded here so they fall through to the doji detector instead, since
    # "indecision" and "reversal candle" are different signals.
    rng = _range(c)
    body = _body(c)
    if _body_ratio(c) <= 0.1:
        return False
    return (
        body <= rng * 0.35
        and _lower_wick(c) >= rng * 0.5
        and _upper_wick(c) <= rng * 0.15
        and _lower_wick(c) >= body * 2
    )


def _is_star_shape(c):
    rng = _range(c)
    body = _body(c)
    if _body_ratio(c) <= 0.1:
        return False
    return (
        body <= rng * 0.35
        and _upper_wick(c) >= rng * 0.5
        and _lower_wick(c) <= rng * 0.15
        and _upper_wick(c) >= body * 2
    )


def _trend_before(candles, i, lookback=5):
    """Rough local trend using closes in the lookback window strictly before i."""
    lo = max(0, i - lookback)
    window = [_cl(c) for c in candles[lo:i]]
    if len(window) < 2:
        return "flat"
    span = max(window) - min(window)
    if span <= 0:
        return "flat"
    slope = window[-1] - window[0]
    if slope > span * 0.2:
        return "up"
    if slope < -span * 0.2:
        return "down"
    return "flat"


def _tier(strength: float) -> str:
    if strength >= 0.66:
        return "high"
    if strength >= 0.33:
        return "medium"
    return "low"


# --- single-candle patterns -------------------------------------------------

def _detect_doji_variants(candles, i):
    c = candles[i]
    if not _is_doji(c):
        return None
    rng = _range(c)
    doji_strength = _clamp(1 - _body_ratio(c) / 0.1)
    if _upper_wick(c) <= rng * 0.1 and _lower_wick(c) >= rng * 0.6:
        wick_strength = _clamp((_lower_wick(c) / rng - 0.6) / 0.4)
        return ("Dragonfly Doji", "bullish", (doji_strength + wick_strength) / 2)
    if _lower_wick(c) <= rng * 0.1 and _upper_wick(c) >= rng * 0.6:
        wick_strength = _clamp((_upper_wick(c) / rng - 0.6) / 0.4)
        return ("Gravestone Doji", "bearish", (doji_strength + wick_strength) / 2)
    if _upper_wick(c) >= rng * 0.3 and _lower_wick(c) >= rng * 0.3:
        wick_strength = _clamp((min(_upper_wick(c), _lower_wick(c)) / rng - 0.3) / 0.3)
        return ("Long-Legged Doji", "neutral", (doji_strength + wick_strength) / 2)
    return ("Doji", "neutral", doji_strength)


def _detect_marubozu(candles, i):
    c = candles[i]
    strength = _clamp((_body_ratio(c) - 0.9) / 0.1)
    if _is_bullish_marubozu(c):
        return ("Bullish Marubozu", "bullish", strength)
    if _is_bearish_marubozu(c):
        return ("Bearish Marubozu", "bearish", strength)
    return None


def _detect_hammer_family(candles, i):
    # Hammer / Hanging Man / Inverted Hammer / Shooting Star are defined by
    # their preceding trend as much as by their shape -- the same candle
    # shape means "reversal" after a trend and means nothing in a flat
    # market. Require a real trend; otherwise this isn't a valid signal.
    c = candles[i]
    rng = _range(c)
    trend = _trend_before(candles, i)
    if trend == "flat":
        return None

    if _is_hammer_shape(c):
        lw = _clamp((_lower_wick(c) / rng - 0.5) / 0.5)
        body_s = _clamp((0.35 - _body(c) / rng) / 0.35)
        uw = _clamp((0.15 - _upper_wick(c) / rng) / 0.15)
        strength = _clamp((lw + body_s + uw) / 3 + 0.15)
        if trend == "up":
            return ("Hanging Man", "bearish", strength)
        return ("Hammer", "bullish", strength)

    if _is_star_shape(c):
        uw = _clamp((_upper_wick(c) / rng - 0.5) / 0.5)
        body_s = _clamp((0.35 - _body(c) / rng) / 0.35)
        lw = _clamp((0.15 - _lower_wick(c) / rng) / 0.15)
        strength = _clamp((uw + body_s + lw) / 3 + 0.15)
        if trend == "down":
            return ("Inverted Hammer", "bullish", strength)
        return ("Shooting Star", "bearish", strength)

    return None


def _detect_spinning_top(candles, i):
    # Distinct from a Doji (body must be clearly non-trivial, not just
    # "small") and requires genuinely balanced wicks on both sides --
    # otherwise it's really a hammer/star-shaped candle that just missed
    # those thresholds, not an indecision candle.
    c = candles[i]
    rng = _range(c)
    body = _body(c)
    upper, lower = _upper_wick(c), _lower_wick(c)
    if not (rng * 0.15 < body <= rng * 0.35):
        return None
    if upper < body * 0.5 or lower < body * 0.5:
        return None
    if min(upper, lower) < max(upper, lower) * 0.4:
        return None
    body_ratio = body / rng
    center_strength = _clamp(1 - abs(body_ratio - 0.25) / 0.1)
    symmetry = _clamp(1 - abs(upper - lower) / rng)
    return ("Spinning Top", "neutral", (center_strength + symmetry) / 2)


# --- two-candle patterns -----------------------------------------------------

def _detect_engulfing(candles, i):
    if i < 1:
        return None
    p, c = candles[i - 1], candles[i]
    if _is_bearish(p) and _is_bullish(c) and _cl(c) >= _o(p) and _o(c) <= _cl(p) and _body(c) > _body(p):
        strength = _clamp((_body(c) / _body(p) - 1) / 1.5)
        return ("Bullish Engulfing", "bullish", strength)
    if _is_bullish(p) and _is_bearish(c) and _o(c) >= _cl(p) and _cl(c) <= _o(p) and _body(c) > _body(p):
        strength = _clamp((_body(c) / _body(p) - 1) / 1.5)
        return ("Bearish Engulfing", "bearish", strength)
    return None


def _detect_harami(candles, i):
    if i < 1:
        return None
    p, c = candles[i - 1], candles[i]
    p_hi, p_lo = max(_o(p), _cl(p)), min(_o(p), _cl(p))
    c_hi, c_lo = max(_o(c), _cl(c)), min(_o(c), _cl(c))
    if _body(p) <= _range(p) * 0.5 or c_hi > p_hi or c_lo < p_lo or _body(c) > _body(p) * 0.6:
        return None
    ratio = _body(c) / _body(p)
    strength = _clamp((0.6 - ratio) / 0.6)
    if _is_doji(c):
        strength = _clamp(strength + 0.15)
        return ("Harami Cross", "bearish" if _is_bullish(p) else "bullish", strength)
    return ("Bearish Harami", "bearish", strength) if _is_bullish(p) else ("Bullish Harami", "bullish", strength)


def _detect_piercing_dark_cloud(candles, i):
    if i < 1:
        return None
    p, c = candles[i - 1], candles[i]
    if _is_bearish(p) and _is_bullish(c) and _o(c) < _l(p) and _mid(p) < _cl(c) < _o(p):
        strength = _clamp((_cl(c) - _mid(p)) / max(_o(p) - _mid(p), 1e-9))
        return ("Piercing Line", "bullish", strength)
    if _is_bullish(p) and _is_bearish(c) and _o(c) > _h(p) and _o(p) < _cl(c) < _mid(p):
        strength = _clamp((_mid(p) - _cl(c)) / max(_mid(p) - _o(p), 1e-9))
        return ("Dark Cloud Cover", "bearish", strength)
    return None


def _detect_tweezer(candles, i):
    # Require real bodies on both candles -- without this, two adjacent
    # near-doji candles can "match" highs/lows by pure noise and get
    # mislabeled as a Tweezer, which is meant to be two decisive opposite
    # candles that both reject the same price level.
    if i < 1:
        return None
    p, c = candles[i - 1], candles[i]
    if _is_bullish(p) == _is_bullish(c):
        return None
    if _body_ratio(p) <= 0.12 or _body_ratio(c) <= 0.12:
        return None
    tol = _range(p) * 0.05
    if abs(_h(p) - _h(c)) <= tol:
        strength = _clamp(1 - abs(_h(p) - _h(c)) / max(tol, 1e-9))
        return ("Tweezer Top", "bearish", strength)
    if abs(_l(p) - _l(c)) <= tol:
        strength = _clamp(1 - abs(_l(p) - _l(c)) / max(tol, 1e-9))
        return ("Tweezer Bottom", "bullish", strength)
    return None


def _detect_kicker(candles, i):
    if i < 1:
        return None
    p, c = candles[i - 1], candles[i]
    if _is_bearish_marubozu(p) and _is_bullish_marubozu(c) and _o(c) >= max(_o(p), _cl(p)):
        gap = (_o(c) - max(_o(p), _cl(p))) / max(_range(p), _range(c))
        return ("Bullish Kicker", "bullish", _clamp(gap * 2))
    if _is_bullish_marubozu(p) and _is_bearish_marubozu(c) and _o(c) <= min(_o(p), _cl(p)):
        gap = (min(_o(p), _cl(p)) - _o(c)) / max(_range(p), _range(c))
        return ("Bearish Kicker", "bearish", _clamp(gap * 2))
    return None


# --- three-candle patterns ----------------------------------------------------

def _detect_star(candles, i):
    if i < 2:
        return None
    a, b, c = candles[i - 2], candles[i - 1], candles[i]
    if (_is_bearish(a) and _body(a) > _range(a) * 0.4 and _body(b) <= _range(b) * 0.3
            and max(_o(b), _cl(b)) < _cl(a) and _is_bullish(c) and _cl(c) > _mid(a)):
        a_s = _clamp((_body(a) / _range(a) - 0.4) / 0.3)
        b_s = _clamp((0.3 - _body(b) / _range(b)) / 0.3)
        pen = _clamp((_cl(c) - _mid(a)) / max(_o(a) - _mid(a), 1e-9))
        strength = (a_s + b_s + pen) / 3
        if _is_doji(b):
            return ("Morning Doji Star", "bullish", _clamp(strength + 0.1))
        return ("Morning Star", "bullish", strength)
    if (_is_bullish(a) and _body(a) > _range(a) * 0.4 and _body(b) <= _range(b) * 0.3
            and min(_o(b), _cl(b)) > _cl(a) and _is_bearish(c) and _cl(c) < _mid(a)):
        a_s = _clamp((_body(a) / _range(a) - 0.4) / 0.3)
        b_s = _clamp((0.3 - _body(b) / _range(b)) / 0.3)
        pen = _clamp((_mid(a) - _cl(c)) / max(_mid(a) - _o(a), 1e-9))
        strength = (a_s + b_s + pen) / 3
        if _is_doji(b):
            return ("Evening Doji Star", "bearish", _clamp(strength + 0.1))
        return ("Evening Star", "bearish", strength)
    return None


def _detect_abandoned_baby(candles, i):
    if i < 2:
        return None
    a, b, c = candles[i - 2], candles[i - 1], candles[i]
    if _is_bearish(a) and _is_doji(b) and _h(b) < _l(a) and _is_bullish(c) and _l(c) > _h(b):
        gap1 = (_l(a) - _h(b)) / _range(a)
        gap2 = (_l(c) - _h(b)) / _range(c)
        return ("Bullish Abandoned Baby", "bullish", _clamp((gap1 + gap2) / 2 * 4))
    if _is_bullish(a) and _is_doji(b) and _l(b) > _h(a) and _is_bearish(c) and _h(c) < _l(b):
        gap1 = (_l(b) - _h(a)) / _range(a)
        gap2 = (_l(b) - _h(c)) / _range(c)
        return ("Bearish Abandoned Baby", "bearish", _clamp((gap1 + gap2) / 2 * 4))
    return None


def _detect_three_soldiers_crows(candles, i):
    if i < 2:
        return None
    a, b, c = candles[i - 2], candles[i - 1], candles[i]
    strong = all(_body(x) > _range(x) * 0.4 for x in (a, b, c))
    if not strong:
        return None
    avg_body_strength = sum(_clamp((_body(x) / _range(x) - 0.4) / 0.4) for x in (a, b, c)) / 3
    if (_is_bullish(a) and _is_bullish(b) and _is_bullish(c)
            and _o(a) < _o(b) < _cl(a) and _o(b) < _o(c) < _cl(b)
            and _cl(a) < _cl(b) < _cl(c)):
        return ("Three White Soldiers", "bullish", avg_body_strength)
    if (_is_bearish(a) and _is_bearish(b) and _is_bearish(c)
            and _cl(a) < _o(b) < _o(a) and _cl(b) < _o(c) < _o(b)
            and _cl(c) < _cl(b) < _cl(a)):
        return ("Three Black Crows", "bearish", avg_body_strength)
    return None


def _detect_three_inside(candles, i):
    if i < 2:
        return None
    a, b, c = candles[i - 2], candles[i - 1], candles[i]
    harami = _detect_harami(candles, i - 1)
    if not harami:
        return None
    h_name, _, h_strength = harami
    conf_margin = _clamp(abs(_cl(c) - _o(a)) / _range(a))
    strength = (h_strength + conf_margin) / 2
    if h_name in ("Bullish Harami", "Harami Cross") and _is_bearish(a) and _cl(c) > _o(a):
        return ("Three Inside Up", "bullish", strength)
    if h_name in ("Bearish Harami", "Harami Cross") and _is_bullish(a) and _cl(c) < _o(a):
        return ("Three Inside Down", "bearish", strength)
    return None


def _detect_three_outside(candles, i):
    if i < 2:
        return None
    a, b, c = candles[i - 2], candles[i - 1], candles[i]
    engulf = _detect_engulfing(candles, i - 1)
    if not engulf:
        return None
    e_name, _, e_strength = engulf
    conf_margin = _clamp(abs(_cl(c) - _cl(b)) / _range(b))
    strength = (e_strength + conf_margin) / 2
    if e_name == "Bullish Engulfing" and _cl(c) > _cl(b):
        return ("Three Outside Up", "bullish", strength)
    if e_name == "Bearish Engulfing" and _cl(c) < _cl(b):
        return ("Three Outside Down", "bearish", strength)
    return None


# Ordered most-specific/significant first; first match wins per candle so the
# chart shows one clear label instead of stacking overlapping patterns.
_DETECTORS = [
    _detect_abandoned_baby,
    _detect_three_soldiers_crows,
    _detect_three_outside,
    _detect_three_inside,
    _detect_star,
    _detect_kicker,
    _detect_engulfing,
    _detect_piercing_dark_cloud,
    _detect_harami,
    _detect_tweezer,
    _detect_marubozu,
    _detect_hammer_family,
    _detect_spinning_top,
    _detect_doji_variants,
]


# Matches below this strength are treated as noise -- geometry that
# technically satisfies a pattern's boolean conditions but so marginally
# that labeling it a real signal would just be a false positive -- and are
# dropped entirely rather than shown as "low confidence".
MIN_STRENGTH = 0.15


def detect_candlestick_patterns(candles: list[dict]):
    """Returns list of {time, pattern, direction, confidence, strength}
    markers across the full candle history passed in. confidence is one of
    "low" / "medium" / "high", derived from how closely the candle geometry
    matches the ideal textbook shape for that pattern."""
    markers = []
    n = len(candles)
    if n < 2:
        return markers

    for i in range(n):
        for detector in _DETECTORS:
            match = detector(candles, i)
            if not match:
                continue
            name, direction, strength = match
            strength = round(_clamp(strength), 2)
            if strength < MIN_STRENGTH:
                continue
            markers.append({
                "time": candles[i]["time"],
                "pattern": name,
                "direction": direction,
                "confidence": _tier(strength),
                "strength": strength,
            })
            break

    return markers


def analyze(candles: list[dict]):
    return {
        "overlay": support_resistance_and_trend(candles),
        "candlestick_markers": detect_candlestick_patterns(candles),
    }
