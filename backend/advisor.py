"""The trading advisor: combines technical indicators computed across
several timeframes at once, fundamentals, analyst/news/insider context,
and broad market conditions into a buy/sell recommendation with tiered
price zones. A single Investment Horizon selection drives everything --
which timeframes get analyzed and blended, how much weight technicals vs.
fundamentals carry, and how far out the price targets are spaced.

This is a transparent, rule-based scoring engine -- not a prediction
model. Every score contributing to the verdict is returned in the
response so the UI can show exactly why it said what it said. Not
financial advice.
"""
from datetime import date

import numpy as np
from scipy.signal import argrelextrema

from . import indicators, patterns

TIMEFRAME_LABELS = {"15m": "15m", "1h": "1H", "1d": "1D", "1wk": "1W"}

# Everything a horizon needs: which timeframes to pull and how much each
# contributes to the blended technical read, which timeframe's candles
# price the buy/sell zones off of, and how much weight each factor group
# (technical / fundamental / analyst-news / market) carries in the final
# score. Shorter horizons lean on price action; longer horizons lean on
# the business and the macro backdrop.
HORIZON_CONFIG = {
    "short": {
        "timeframes": [("15m", 0.30), ("1h", 0.45), ("1d", 0.25)],
        "zone_tf": "1h",
        "weights": {"technical": 0.60, "fundamental": 0.10, "street": 0.15, "macro": 0.15},
        "label": "Short-term (days)",
    },
    "medium": {
        "timeframes": [("1h", 0.25), ("1d", 0.50), ("1wk", 0.25)],
        "zone_tf": "1d",
        "weights": {"technical": 0.40, "fundamental": 0.27, "street": 0.16, "macro": 0.17},
        "label": "Medium-term (weeks–months)",
    },
    "long": {
        "timeframes": [("1d", 0.35), ("1wk", 0.65)],
        "zone_tf": "1wk",
        "weights": {"technical": 0.20, "fundamental": 0.45, "street": 0.15, "macro": 0.20},
        "label": "Long-term (6+ months)",
    },
}
HORIZONS = set(HORIZON_CONFIG)
HORIZON_LABELS = {k: v["label"] for k, v in HORIZON_CONFIG.items()}

# ATR multipliers per tier for price-zone spacing. "chain" is the minimum
# extra ATR distance enforced between adjacent sell tiers so they can
# never collapse onto the same price (see _price_zones).
HORIZON_MULTIPLIERS = {
    "short":  {"buy_strong": 1.0, "buy_mid": 0.2, "sell_light": 0.4, "sell_mid": 1.2, "sell_stretch": 2.0, "chain": 0.6},
    "medium": {"buy_strong": 1.5, "buy_mid": 0.3, "sell_light": 0.5, "sell_mid": 2.0, "sell_stretch": 3.5, "chain": 1.0},
    "long":   {"buy_strong": 3.0, "buy_mid": 0.6, "sell_light": 1.5, "sell_mid": 4.5, "sell_stretch": 8.0, "chain": 2.0},
}


def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


# --- technical scoring -------------------------------------------------------

def _detect_rsi_divergence(closes: list[float], rsi_vals: list[float | None]):
    """Looks for a *live* (recent) divergence between price's last two
    swing lows/highs and RSI's value at those same bars: price making a
    lower low while RSI makes a higher low (or the mirror at swing highs)
    is one of the more reliable reversal signals in technical analysis,
    and isn't captured by any single-bar indicator. Returns
    (direction, strength) or None."""
    n = len(closes)
    if n < 40:
        return None
    arr = np.asarray(closes, dtype=float)
    order = 3

    def _valid(idxs):
        return [i for i in sorted(set(idxs.tolist())) if rsi_vals[i] is not None]

    lows_idx = _valid(argrelextrema(arr, np.less_equal, order=order)[0])
    highs_idx = _valid(argrelextrema(arr, np.greater_equal, order=order)[0])

    if len(lows_idx) >= 2:
        recent, prior = lows_idx[-1], lows_idx[-2]
        if n - 1 - recent <= 8 and arr[recent] < arr[prior] and rsi_vals[recent] > rsi_vals[prior]:
            price_diff = (arr[prior] - arr[recent]) / max(arr[prior], 1e-9)
            rsi_diff = (rsi_vals[recent] - rsi_vals[prior]) / 40
            strength = _clamp((price_diff * 8 + rsi_diff) / 2, 0, 1)
            if strength >= 0.15:
                return ("bullish", strength)

    if len(highs_idx) >= 2:
        recent, prior = highs_idx[-1], highs_idx[-2]
        if n - 1 - recent <= 8 and arr[recent] > arr[prior] and rsi_vals[recent] < rsi_vals[prior]:
            price_diff = (arr[recent] - arr[prior]) / max(arr[prior], 1e-9)
            rsi_diff = (rsi_vals[prior] - rsi_vals[recent]) / 40
            strength = _clamp((price_diff * 8 + rsi_diff) / 2, 0, 1)
            if strength >= 0.15:
                return ("bearish", strength)

    return None


def _score_technicals_single_tf(candles: list[dict], tf_label: str) -> dict:
    """Scores one timeframe's candles. Each factor is paired with an
    importance weight (not just averaged flat) so a high-conviction signal
    like an RSI divergence or an established EMA200 trend structure counts
    for more than a marginal Bollinger-band nudge."""
    closes = [c["close"] for c in candles]
    factors = []
    weighted: list[tuple[float, float]] = []
    warnings = []

    # ADX first -- gates how much weight the trend-following factors
    # (MACD, EMA cross) get below. A crossover means little in a
    # directionless, choppy market (low ADX) and a lot in a confirmed
    # trend (high ADX).
    adx_vals = indicators.adx(candles, 14)
    adx_val = adx_vals["adx"]
    trend_mult = 1.0
    if adx_val is not None:
        trend_mult = 1.25 if adx_val >= 25 else (0.85 if adx_val >= 20 else 0.5)
        dir_score = _clamp((adx_vals["plus_di"] - adx_vals["minus_di"]) / 25)
        s = _clamp(dir_score * min(trend_mult, 1.0))
        if adx_val >= 25:
            note = f"ADX {adx_val:.0f} — a real, tradeable trend; trend-following signals below carry extra weight."
        elif adx_val >= 20:
            note = f"ADX {adx_val:.0f} — a developing trend."
        else:
            note = f"ADX {adx_val:.0f} — no real trend, price is chopping sideways; trend-following signals are de-weighted."
            warnings.append(f"ADX {adx_val:.0f} on the {tf_label} timeframe — range-bound, not trending; breakout/trend signals here are less reliable.")
        weighted.append((1.1, s))
        factors.append({"name": "ADX trend strength", "score": round(s, 2), "detail": note})

    rsi_val = indicators.rsi(closes, 14)
    if rsi_val is not None:
        if rsi_val >= 70:
            s = -_clamp((rsi_val - 70) / 15)
            note = f"RSI {rsi_val:.0f} — overbought, favors waiting for a pullback."
        elif rsi_val <= 30:
            s = _clamp((30 - rsi_val) / 15)
            note = f"RSI {rsi_val:.0f} — oversold, favors a bounce."
        else:
            s = _clamp((50 - rsi_val) / 40)
            note = f"RSI {rsi_val:.0f} — neutral range."
        weighted.append((0.8, s))
        factors.append({"name": "RSI (14)", "score": round(s, 2), "detail": note})

    macd_vals = indicators.macd(closes)
    if macd_vals["histogram"] is not None:
        hist = macd_vals["histogram"]
        ref = abs(macd_vals["macd"]) or 1e-9
        s = _clamp(_clamp(hist / ref) * trend_mult)
        if hist > 0:
            note = "MACD histogram positive — bullish momentum."
        elif hist < 0:
            note = "MACD histogram negative — bearish momentum."
        else:
            note = "MACD flat — no clear momentum."
        weighted.append((1.0, s))
        factors.append({"name": "MACD", "score": round(s, 2), "detail": note})

    ema20 = indicators.ema(closes, 20)
    ema50 = indicators.ema(closes, 50) if len(closes) >= 50 else None
    ema200 = indicators.ema(closes, 200) if len(closes) >= 200 else None
    if ema20 is not None and ema50 is not None:
        s = _clamp(_clamp((ema20 - ema50) / ema50 * 20) * trend_mult)
        note = ("EMA20 above EMA50 — short-term uptrend." if ema20 > ema50
                else "EMA20 below EMA50 — short-term downtrend.")
        weighted.append((1.0, s))
        factors.append({"name": "EMA 20/50 trend", "score": round(s, 2), "detail": note})

    if ema200 is not None and ema20 is not None and ema50 is not None:
        price = closes[-1]
        if ema20 > ema50 > ema200:
            s = 0.6
            note = "Bullish EMA stack: EMA20 > EMA50 > EMA200 — established uptrend structure."
        elif ema20 < ema50 < ema200:
            s = -0.6
            note = "Bearish EMA stack: EMA20 < EMA50 < EMA200 — established downtrend structure."
        else:
            s = _clamp((price - ema200) / ema200 * 8)
            note = f"Mixed EMA stack (not cleanly aligned); price is {'above' if price > ema200 else 'below'} its 200-period average."
        weighted.append((1.4, s))
        factors.append({"name": "Trend structure (EMA200)", "score": round(s, 2), "detail": note})
    elif ema200 is not None:
        price = closes[-1]
        s = _clamp((price - ema200) / ema200 * 8)
        weighted.append((1.2, s))
        factors.append({"name": "Trend structure (EMA200)", "score": round(s, 2),
                         "detail": f"Price is {'above' if price > ema200 else 'below'} its 200-period average ({ema200:.2f})."})

    stoch = indicators.stochastic(candles, 14, 3)
    if stoch["k"] is not None:
        k, d = stoch["k"], stoch["d"]
        base = _clamp((50 - k) / 40)
        cross = 0.0 if d is None else (0.12 if k > d else (-0.12 if k < d else 0.0))
        s = _clamp(base + cross)
        if k >= 80:
            note = f"Stochastic %K {k:.0f} — overbought" + (", but still rising." if cross > 0 else ".")
        elif k <= 20:
            note = f"Stochastic %K {k:.0f} — oversold" + (", and turning up." if cross > 0 else ".")
        else:
            note = f"Stochastic %K {k:.0f} — mid-range."
        weighted.append((0.7, s))
        factors.append({"name": "Stochastic (14,3)", "score": round(s, 2), "detail": note})

    boll = indicators.bollinger(closes, 20, 2)
    if boll["percent_b"] is not None:
        pb = boll["percent_b"]
        s = _clamp((0.5 - pb) * 2)
        if pb <= 0.15:
            note = f"Price near the lower Bollinger Band ({pb:.0%} of band width) — potentially oversold."
        elif pb >= 0.85:
            note = f"Price near the upper Bollinger Band ({pb:.0%} of band width) — potentially overbought."
        else:
            note = f"Price sits mid-band ({pb:.0%}) — no extreme."
        weighted.append((0.7, s))
        factors.append({"name": "Bollinger position", "score": round(s, 2), "detail": note})

    overlay = patterns.support_resistance_and_trend(candles)
    if overlay.get("trend"):
        direction = overlay["trend"]["direction"]
        s = 0.3 if direction == "up" else -0.3 if direction == "down" else 0.0
        weighted.append((0.9, s))
        factors.append({
            "name": "Overall trend", "score": round(s, 2),
            "detail": f"Regression trend across the loaded window is {direction}.",
        })

    # Candlestick patterns only count as a live signal within the last 5
    # bars -- previously the *last* medium/high-confidence match anywhere
    # in the whole window counted, even one from weeks or months ago.
    recent_time_cutoff = {c["time"] for c in candles[-5:]}
    recent_patterns = [
        p for p in patterns.detect_candlestick_patterns(candles)
        if p["confidence"] in ("medium", "high") and p["time"] in recent_time_cutoff
    ]
    if recent_patterns:
        last = recent_patterns[-1]
        if last["direction"] == "bullish":
            s = 0.4 * last["strength"]
        elif last["direction"] == "bearish":
            s = -0.4 * last["strength"]
        else:
            s = 0.0
        weighted.append((0.8, s))
        factors.append({
            "name": "Latest pattern", "score": round(s, 2),
            "detail": f"{last['pattern']} ({last['confidence']} confidence, within the last 5 bars) — {last['direction']}.",
        })

    rsi_vals = indicators.rsi_series(closes, 14)
    divergence = _detect_rsi_divergence(closes, rsi_vals)
    if divergence:
        direction, strength = divergence
        s = (0.55 if direction == "bullish" else -0.55) * strength
        weighted.append((1.3, s))
        factors.append({
            "name": "RSI divergence", "score": round(s, 2),
            "detail": (f"Price made a {'lower low' if direction == 'bullish' else 'higher high'} while RSI made a "
                       f"{'higher low' if direction == 'bullish' else 'lower high'} — {direction} divergence, "
                       "a classic early reversal signal."),
        })

    volumes = [c.get("volume") or 0 for c in candles]
    if len(candles) >= 20 and any(v > 0 for v in volumes):
        obv = indicators.obv_series(candles)
        lookback = min(20, len(candles) - 1)
        price_change = closes[-1] - closes[-1 - lookback]
        obv_change = obv[-1] - obv[-1 - lookback]
        price_dir = 1 if price_change > 0 else (-1 if price_change < 0 else 0)
        obv_dir = 1 if obv_change > 0 else (-1 if obv_change < 0 else 0)
        if price_dir != 0:
            if price_dir == obv_dir:
                s = 0.3 * price_dir
                note = ("Volume (OBV) is rising alongside price — the move is backed by real participation."
                        if price_dir > 0 else
                        "Volume (OBV) is falling alongside price — selling is backed by real participation.")
            elif obv_dir == -price_dir:
                s = -0.3 * price_dir
                note = ("Price is rising but volume (OBV) is falling — the rally looks unconfirmed, watch for a reversal."
                        if price_dir > 0 else
                        "Price is falling but volume (OBV) is rising — possible quiet accumulation under the decline.")
            else:
                s = 0.0
                note = "Volume is flat relative to the recent price move — no strong confirmation either way."
            weighted.append((1.0, s))
            factors.append({"name": "Volume confirmation (OBV)", "score": round(s, 2), "detail": note})
    else:
        factors.append({"name": "Volume confirmation (OBV)", "score": 0.0,
                         "detail": "No usable volume data for this symbol/timeframe."})

    if tf_label in ("15m", "1h"):
        vwap_window = candles[-60:] if len(candles) >= 60 else candles
        vwap_val = indicators.vwap(vwap_window)
        if vwap_val:
            current_price = closes[-1]
            dev_pct = (current_price - vwap_val) / vwap_val * 100
            if abs(dev_pct) <= 0.1:
                note = "Price is sitting right on VWAP."
                s = 0.0
            else:
                s = _clamp(dev_pct / 3)
                note = (f"Price is {abs(dev_pct):.1f}% above VWAP — trading with intraday strength."
                        if dev_pct > 0 else
                        f"Price is {abs(dev_pct):.1f}% below VWAP — trading with intraday weakness.")
            weighted.append((0.6, s))
            factors.append({"name": "VWAP position", "score": round(s, 2), "detail": note})

    atr_val = indicators.atr(candles, 14)
    atr_pct = None
    if atr_val is not None and closes[-1]:
        atr_pct = atr_val / closes[-1] * 100
        prior_slice = candles[:-14] if len(candles) >= 28 else None
        prior_atr = indicators.atr(prior_slice, 14) if prior_slice else None
        detail = f"ATR(14) is {atr_pct:.1f}% of price."
        if prior_atr and prior_atr > 0:
            ratio = atr_val / prior_atr
            if ratio >= 1.4:
                detail += f" Volatility is expanding sharply ({ratio:.1f}x the prior window) — expect wider swings."
                warnings.append(f"Volatility is expanding sharply on the {tf_label} timeframe ({ratio:.1f}x the prior window).")
            elif ratio <= 0.7:
                detail += f" Volatility is contracting ({ratio:.1f}x the prior window) — tighter range, watch for a breakout."
        factors.append({"name": "Volatility (ATR)", "score": 0.0, "detail": detail})

    score = _clamp(sum(w * s for w, s in weighted) / sum(w for w, _ in weighted)) if weighted else 0.0
    return {"score": score, "factors": factors, "raw_scores": weighted, "warnings": warnings, "atr_pct": atr_pct}


def _score_technicals(candles_by_tf: dict[str, list[dict]], timeframes: list[tuple[str, float]]) -> dict:
    """Blends the technical read across every timeframe the current
    horizon calls for, weighted the way that horizon specifies. Also
    tracks how well the timeframes *agree* -- a setup where 15m, 1h and
    1D all point the same way is worth more than one where they conflict,
    even if they average out to the same headline score."""
    tf_results = []
    for tf, tf_weight in timeframes:
        candles = candles_by_tf.get(tf) or []
        if len(candles) < 20:
            continue
        tf_results.append((tf, tf_weight, _score_technicals_single_tf(candles, tf)))

    if not tf_results:
        return {"score": 0.0, "factors": [], "raw_scores": [], "warnings": [], "atr_pct": None,
                "timeframes": [], "alignment": 1.0}

    total_w = sum(w for _, w, _ in tf_results)
    blended_score = _clamp(sum(w * r["score"] for _, w, r in tf_results) / total_w)

    factors = []
    raw_scores: list[tuple[float, float]] = []
    warnings = []
    timeframes_summary = []
    for tf, tf_weight, result in tf_results:
        label = TIMEFRAME_LABELS.get(tf, tf)
        for item in result["factors"]:
            factors.append({**item, "name": f"[{label}] {item['name']}"})
        for item_weight, s in result["raw_scores"]:
            raw_scores.append((item_weight * tf_weight, s))
        warnings.extend(result["warnings"])
        tf_dir = "up" if result["score"] > 0.08 else ("down" if result["score"] < -0.08 else "flat")
        timeframes_summary.append({"label": label, "direction": tf_dir, "score": round(result["score"], 2)})

    overall_dir = 1 if blended_score > 0.08 else (-1 if blended_score < -0.08 else 0)
    align_w = 0.0
    for tf, tf_weight, result in tf_results:
        tf_dir = 1 if result["score"] > 0.08 else (-1 if result["score"] < -0.08 else 0)
        if overall_dir == 0 or tf_dir == 0 or tf_dir == overall_dir:
            align_w += tf_weight
    alignment = align_w / total_w if total_w else 1.0

    factors.append({
        "name": "Timeframe alignment", "score": 0.0,
        "detail": (f"All analyzed timeframes agree on direction." if alignment >= 0.99 else
                   f"Most timeframes agree on direction ({alignment:.0%} weighted agreement)." if alignment >= 0.6 else
                   f"Timeframes disagree on direction (only {alignment:.0%} weighted agreement)."),
    })
    if alignment < 0.6:
        warnings.append(f"Timeframes disagree on direction (only {alignment:.0%} weighted agreement) — signal quality is reduced; consider waiting for confirmation.")

    ordered_atr = [r["atr_pct"] for _, _, r in tf_results if r.get("atr_pct") is not None]
    zone_atr_pct = ordered_atr[-1] if ordered_atr else None

    return {
        "score": blended_score, "factors": factors, "raw_scores": raw_scores,
        "warnings": warnings, "atr_pct": zone_atr_pct,
        "timeframes": timeframes_summary, "alignment": alignment,
    }


# --- fundamentals scoring -----------------------------------------------------

_NO_FUNDAMENTALS = {
    "score": 0.0,
    "factors": [{"name": "Fundamentals", "score": 0.0,
                 "detail": "No fundamentals data available for this symbol (e.g. crypto)."}],
    "raw_scores": [],
}


def _score_fundamentals(context: dict | None, current_price: float) -> dict:
    m = (context or {}).get("metrics") or {}
    factors = []
    weighted: list[tuple[float, float]] = []

    pe = m.get("pe_ttm")
    if pe is not None and pe > 0:
        s = _clamp((25 - pe) / 25)
        factors.append({"name": "P/E (TTM)", "score": round(s, 2), "detail": f"Trailing P/E of {pe:.1f}."})
        weighted.append((1.0, s))

    ps = m.get("ps_ttm")
    if ps is not None and ps > 0:
        s = _clamp((6 - ps) / 6)
        factors.append({"name": "P/S (TTM)", "score": round(s, 2), "detail": f"Price-to-sales of {ps:.1f}x."})
        weighted.append((0.8, s))

    pb = m.get("price_to_book")
    if pb is not None and pb > 0:
        s = _clamp((4 - pb) / 4)
        factors.append({"name": "Price / book", "score": round(s, 2), "detail": f"Price-to-book of {pb:.1f}x."})
        weighted.append((1.0, s))

    rev_growth = m.get("revenue_growth_ttm_yoy")
    if rev_growth is not None:
        s = _clamp(rev_growth / 20)
        factors.append({"name": "Revenue growth (YoY)", "score": round(s, 2), "detail": f"Revenue grew {rev_growth:.1f}% YoY."})
        weighted.append((1.0, s))

    rev_growth_3y = m.get("revenue_growth_3y")
    if rev_growth_3y is not None:
        s = _clamp(rev_growth_3y / 20)
        factors.append({"name": "Revenue growth (3Y CAGR)", "score": round(s, 2), "detail": f"Revenue grew {rev_growth_3y:.1f}%/yr over 3 years."})
        weighted.append((0.9, s))

    eps_growth = m.get("eps_growth_ttm_yoy")
    if eps_growth is not None:
        s = _clamp(eps_growth / 25)
        factors.append({"name": "EPS growth (YoY)", "score": round(s, 2), "detail": f"EPS grew {eps_growth:.1f}% YoY."})
        weighted.append((1.0, s))

    eps_growth_3y = m.get("eps_growth_3y")
    if eps_growth_3y is not None:
        s = _clamp(eps_growth_3y / 25)
        factors.append({"name": "EPS growth (3Y CAGR)", "score": round(s, 2), "detail": f"EPS grew {eps_growth_3y:.1f}%/yr over 3 years."})
        weighted.append((0.9, s))

    margin = m.get("net_margin_ttm")
    if margin is not None:
        s = _clamp((margin - 10) / 20)
        factors.append({"name": "Net margin (TTM)", "score": round(s, 2), "detail": f"Net margin of {margin:.1f}%."})
        weighted.append((1.0, s))

    gross_margin = m.get("gross_margin_ttm")
    if gross_margin is not None:
        s = _clamp((gross_margin - 35) / 30)
        factors.append({"name": "Gross margin (TTM)", "score": round(s, 2), "detail": f"Gross margin of {gross_margin:.1f}%."})
        weighted.append((0.8, s))

    op_margin = m.get("operating_margin_ttm")
    if op_margin is not None:
        s = _clamp((op_margin - 12) / 20)
        factors.append({"name": "Operating margin (TTM)", "score": round(s, 2), "detail": f"Operating margin of {op_margin:.1f}%."})
        weighted.append((0.9, s))

    roe = m.get("roe_ttm")
    if roe is not None:
        s = _clamp((roe - 10) / 20)
        factors.append({"name": "Return on equity (TTM)", "score": round(s, 2), "detail": f"ROE of {roe:.1f}%."})
        weighted.append((1.0, s))

    roa = m.get("roa_ttm")
    if roa is not None:
        s = _clamp((roa - 5) / 10)
        factors.append({"name": "Return on assets (TTM)", "score": round(s, 2), "detail": f"ROA of {roa:.1f}%."})
        weighted.append((0.7, s))

    debt_eq = m.get("debt_to_equity")
    if debt_eq is not None:
        s = _clamp(-((debt_eq - 1) / 2))
        factors.append({"name": "Debt / equity", "score": round(s, 2), "detail": f"Debt-to-equity of {debt_eq:.2f}."})
        weighted.append((1.0, s))

    current_ratio = m.get("current_ratio")
    if current_ratio is not None:
        s = _clamp((current_ratio - 1) / 1.5)
        factors.append({"name": "Current ratio", "score": round(s, 2),
                         "detail": f"Current ratio of {current_ratio:.2f} (ability to cover short-term liabilities)."})
        weighted.append((0.7, s))

    quick_ratio = m.get("quick_ratio")
    if quick_ratio is not None:
        s = _clamp((quick_ratio - 0.8) / 1.2)
        factors.append({"name": "Quick ratio", "score": round(s, 2), "detail": f"Quick ratio of {quick_ratio:.2f}."})
        weighted.append((0.5, s))

    payout = m.get("payout_ratio_ttm")
    if payout is not None and payout > 0:
        if payout > 90:
            s, note = -0.4, f"Payout ratio of {payout:.0f}% — very high, dividend sustainability risk."
        elif payout > 60:
            s, note = -0.1, f"Payout ratio of {payout:.0f}% — on the higher side."
        else:
            s, note = 0.15, f"Payout ratio of {payout:.0f}% — comfortably covered."
        factors.append({"name": "Payout ratio", "score": round(s, 2), "detail": note})
        weighted.append((0.4, s))

    div_yield = m.get("dividend_yield")
    if div_yield is not None and div_yield > 0:
        s = _clamp(div_yield / 5)
        factors.append({"name": "Dividend yield", "score": round(s, 2), "detail": f"Indicated dividend yield of {div_yield:.1f}%."})
        weighted.append((0.6, s))

    week_hi, week_lo = m.get("week52_high"), m.get("week52_low")
    if week_hi and week_lo and current_price and week_hi > week_lo:
        pos = (current_price - week_lo) / (week_hi - week_lo)
        s = _clamp((pos - 0.5) * 1.2)
        if pos >= 0.9:
            note = f"Trading at {pos:.0%} of its 52-week range — near the 52-week high, showing strong momentum."
        elif pos <= 0.1:
            note = f"Trading at {pos:.0%} of its 52-week range — near the 52-week low."
        else:
            note = f"Trading at {pos:.0%} of its 52-week range."
        factors.append({"name": "52-week range position", "score": round(s, 2), "detail": note})
        weighted.append((0.9, s))

    # Whether the metrics dict was missing entirely (fetch failed) or came
    # back with every field None (e.g. a crypto pair queried against a
    # stock-fundamentals API), the outcome for the advisor is the same:
    # nothing usable -- so both cases share one clear message.
    if not factors:
        return dict(_NO_FUNDAMENTALS)

    score = _clamp(sum(w * s for w, s in weighted) / sum(w for w, _ in weighted)) if weighted else 0.0
    return {"score": score, "factors": factors, "raw_scores": weighted}


# --- street/context scoring (analysts, news, earnings, insiders) ---------------

def _score_street(context: dict | None) -> dict:
    if not context or not context.get("available"):
        return {"score": 0.0, "factors": [], "warnings": [], "raw_scores": []}

    factors = []
    weighted: list[tuple[float, float]] = []
    warnings = []

    analyst = context.get("analyst")
    if analyst:
        total = analyst["strongBuy"] + analyst["buy"] + analyst["hold"] + analyst["sell"] + analyst["strongSell"]
        if total:
            bullish = analyst["strongBuy"] * 2 + analyst["buy"]
            bearish = analyst["strongSell"] * 2 + analyst["sell"]
            s = _clamp((bullish - bearish) / (total * 1.5))
            factors.append({
                "name": "Analyst consensus", "score": round(s, 2),
                "detail": (f"{analyst['strongBuy']} strong buy / {analyst['buy']} buy / "
                           f"{analyst['hold']} hold / {analyst['sell']} sell / {analyst['strongSell']} strong sell."),
            })
            weighted.append((1.0, s))

    news_tone = context.get("news_tone")
    if news_tone is not None and context.get("news_count"):
        factors.append({
            "name": "Recent news tone", "score": round(news_tone, 2),
            "detail": f"Keyword tone across {context['news_count']} recent headlines (last 10 days, recency-weighted).",
        })
        weighted.append((0.9, news_tone))

    earnings_surprises = context.get("earnings_surprises")
    if earnings_surprises:
        beats, total_q, avg_pct = earnings_surprises["beats"], earnings_surprises["total"], earnings_surprises["avg_surprise_pct"]
        beat_ratio = beats / total_q
        s = _clamp((beat_ratio - 0.5) * 1.6 + _clamp(avg_pct / 20) * 0.3)
        factors.append({
            "name": "Earnings surprise history", "score": round(s, 2),
            "detail": f"Beat estimates in {beats}/{total_q} of the last reported quarters (avg surprise {avg_pct:+.1f}%).",
        })
        weighted.append((1.1, s))

    insider_mspr = context.get("insider_mspr")
    if insider_mspr is not None:
        s = _clamp(insider_mspr / 40)
        if insider_mspr > 5:
            note = f"Insiders have been net buyers over the last 3 months (MSPR {insider_mspr:+.1f}) — a bullish signal."
        elif insider_mspr < -5:
            note = f"Insiders have been net sellers over the last 3 months (MSPR {insider_mspr:+.1f})."
        else:
            note = f"Insider trading is roughly balanced (MSPR {insider_mspr:+.1f})."
        factors.append({"name": "Insider sentiment", "score": round(s, 2), "detail": note})
        weighted.append((1.0, s))

    next_earnings = context.get("next_earnings_date")
    if next_earnings:
        days_away = (date.fromisoformat(next_earnings) - date.today()).days
        if 0 <= days_away <= 7:
            warnings.append(
                f"Earnings report on {next_earnings} ({days_away} day{'s' if days_away != 1 else ''} away) — expect elevated volatility."
            )

    if not factors:
        factors.append({"name": "Street/context", "score": 0.0,
                         "detail": "No analyst coverage, news, earnings, or insider data available for this symbol."})

    score = _clamp(sum(w * s for w, s in weighted) / sum(w for w, _ in weighted)) if weighted else 0.0
    return {"score": score, "factors": factors, "warnings": warnings, "raw_scores": weighted}


# --- market & external scoring ---------------------------------------------------

def _score_macro(macro: dict | None, sector: dict | None) -> dict:
    if not macro or not macro.get("available"):
        return {"score": 0.0, "factors": [], "warnings": [], "raw_scores": []}

    factors = []
    weighted: list[tuple[float, float]] = []
    warnings = []

    vix = macro.get("vix")
    if vix is not None:
        s = _clamp((20 - vix) / 15)
        if vix > 25:
            note = f"VIX at {vix:.1f} — elevated, market pricing in fear/uncertainty."
        elif vix < 15:
            note = f"VIX at {vix:.1f} — calm conditions."
        else:
            note = f"VIX at {vix:.1f} — normal range."
        factors.append({"name": "VIX (market risk)", "score": round(s, 2), "detail": note})
        weighted.append((1.0, s))
        if vix > 30:
            warnings.append(f"VIX at {vix:.1f} — markets are notably fearful; expect larger-than-usual swings.")

    tnx = macro.get("tnx_yield")
    tnx_trend = macro.get("tnx_trend")
    if tnx is not None:
        s = -0.2 if tnx_trend == "up" else 0.2 if tnx_trend == "down" else 0.0
        factors.append({
            "name": "10-year Treasury yield", "score": round(s, 2),
            "detail": f"10Y yield at {tnx:.2f}%, trending {tnx_trend}.",
        })
        weighted.append((0.8, s))

    irx_trend = macro.get("irx_trend")
    if irx_trend:
        s = -0.15 if irx_trend == "up" else (0.15 if irx_trend == "down" else 0.0)
        factors.append({
            "name": "Short-term rates (13-wk T-bill)", "score": round(s, 2),
            "detail": (f"13-week T-bill trending {irx_trend} — "
                       f"{'a mild headwind' if irx_trend == 'up' else 'a mild tailwind' if irx_trend == 'down' else 'no strong signal'} for risk assets."),
        })
        weighted.append((0.6, s))

    yield_curve_spread = macro.get("yield_curve_spread")
    if yield_curve_spread is not None:
        s = _clamp(yield_curve_spread / 1.5)
        if yield_curve_spread < 0:
            note = f"Yield curve inverted (10Y − 13wk = {yield_curve_spread:+.2f}pp) — a well-known recession-risk signal."
            warnings.append(f"Yield curve is inverted ({yield_curve_spread:+.2f}pp) — historically a leading recession indicator; macro risk is elevated.")
        else:
            note = f"Yield curve normal (10Y − 13wk = {yield_curve_spread:+.2f}pp)."
        factors.append({"name": "Yield curve (10Y − 13wk)", "score": round(s, 2), "detail": note})
        weighted.append((1.0, s))

    spx_regime = macro.get("spx_regime")
    if spx_regime and spx_regime != "unknown":
        s = 0.4 if spx_regime == "bull" else (-0.4 if spx_regime == "bear" else 0.0)
        factors.append({
            "name": "S&P 500 regime", "score": round(s, 2),
            "detail": (f"S&P 500 is in a {spx_regime} regime (price vs. 50/200-day averages) — broad market conditions "
                       f"{'support' if s > 0 else 'work against' if s < 0 else 'are neutral for'} this trade."),
        })
        weighted.append((1.2, s))

    if sector and sector.get("regime") and sector["regime"] != "unknown":
        s = 0.35 if sector["regime"] == "bull" else (-0.35 if sector["regime"] == "bear" else 0.0)
        factors.append({
            "name": f"Sector trend ({sector['etf']})", "score": round(s, 2),
            "detail": f"{sector['etf']} (this stock's sector) is in a {sector['regime']} regime (price vs. 50/200-day averages).",
        })
        weighted.append((1.1, s))

    score = _clamp(sum(w * s for w, s in weighted) / sum(w for w, _ in weighted)) if weighted else 0.0
    return {"score": score, "factors": factors, "warnings": warnings, "raw_scores": weighted}


# --- confidence ------------------------------------------------------------------

def _confidence(overall: float, weights: dict, tech: dict, fund: dict, street: dict, macro_score: dict,
                 candle_counts: list[int], tf_alignment: float) -> float:
    """Confidence isn't just "how extreme is the score" -- it's how much
    the underlying evidence actually agrees, how much evidence there is,
    how reliable the conditions are, and now also whether the analyzed
    timeframes confirm each other. Two setups can produce the same overall
    score of +0.4: one where every factor mildly agrees across every
    timeframe, another where strong bulls and strong bears are canceling
    out, or where 15m and 1D are flatly fighting each other. Those deserve
    very different confidence."""
    groups = [
        (weights["technical"], tech.get("raw_scores", [])),
        (weights["fundamental"], fund.get("raw_scores", [])),
        (weights["street"], street.get("raw_scores", [])),
        (weights["macro"], macro_score.get("raw_scores", [])),
    ]
    agree_w = 0.0
    disagree_w = 0.0
    total_items = 0
    overall_sign = 1 if overall > 0.05 else (-1 if overall < -0.05 else 0)

    for group_weight, raw in groups:
        for item_weight, s in raw:
            total_items += 1
            w = group_weight * item_weight
            if overall_sign == 0 or abs(s) < 0.05:
                agree_w += w
            elif (s > 0) == (overall_sign > 0):
                agree_w += w
            else:
                disagree_w += w

    total_w = agree_w + disagree_w
    agreement = agree_w / total_w if total_w else 0.5

    base = 0.30 + 0.40 * abs(overall) + 0.25 * agreement + 0.10 * tf_alignment

    if total_items < 6:
        base -= 0.15
    elif total_items < 10:
        base -= 0.07

    min_candles = min(candle_counts) if candle_counts else 0
    if min_candles < 30:
        base -= 0.15
    elif min_candles < 50:
        base -= 0.06

    atr_pct = tech.get("atr_pct")
    if atr_pct is not None:
        if atr_pct > 8:
            base -= 0.12
        elif atr_pct > 5:
            base -= 0.06

    return round(_clamp(base, 0.05, 0.97), 2)


# --- price zones ----------------------------------------------------------------

def _price_zones(candles: list[dict], overlay: dict, current_price: float, horizon: str = "medium") -> dict:
    mult = HORIZON_MULTIPLIERS.get(horizon, HORIZON_MULTIPLIERS["medium"])
    atr_val = indicators.atr(candles, 14) or (current_price * 0.02)
    atr_val = max(atr_val, current_price * 0.001)  # avoid a zero/near-zero ATR collapsing every tier together
    closes = [c["close"] for c in candles]
    ema20 = indicators.ema(closes, 20) or current_price
    boll = indicators.bollinger(closes, 20, 2)

    levels = sorted(overlay.get("levels") or [])
    supports = [lv for lv in levels if lv < current_price]
    resistances = [lv for lv in levels if lv > current_price]

    support_level = max(supports) if supports else (boll["lower"] or current_price - 2 * atr_val)
    resistance_level = min(resistances) if resistances else (boll["upper"] or current_price + 2 * atr_val)

    # Tiers are built with explicit min/max clamps so the ladder is always
    # strictly ordered: buy_strong <= buy_mid <= buy_light (== current)
    # <= sell_light <= sell_mid <= sell_stretch. Without this, a distant
    # support/resistance level can otherwise land "out of order" relative
    # to the ATR-based tiers (e.g. sell_mid landing below sell_light).
    buy_strong = min(support_level, current_price - mult["buy_strong"] * atr_val)
    buy_mid = max(min(ema20, current_price - mult["buy_mid"] * atr_val), buy_strong)
    buy_light = current_price

    # Each tier is chained off the previous one (not just a shared floor) so
    # a distant resistance level can't collapse all three sell tiers onto
    # the same price -- every tier is guaranteed at least one horizon-scaled
    # ATR increment further out than the last.
    sell_light = max(resistance_level, current_price + mult["sell_light"] * atr_val)
    sell_mid = max(current_price + mult["sell_mid"] * atr_val, sell_light + mult["chain"] * atr_val)
    sell_stretch = max(current_price + mult["sell_stretch"] * atr_val, sell_mid + mult["chain"] * atr_val)

    buy = [
        {"tier": "strong", "price": round(buy_strong, 2),
         "rationale": "Near nearest support / lower volatility band — best risk/reward entry."},
        {"tier": "mid", "price": round(buy_mid, 2),
         "rationale": "Pullback to the 20-period average — a common moderate entry."},
        {"tier": "light", "price": round(buy_light, 2),
         "rationale": "Current market price — momentum entry, pay up for confirmation."},
    ]
    sell = [
        {"tier": "light", "price": round(sell_light, 2),
         "rationale": "Near nearest resistance — first place to take partial profit."},
        {"tier": "mid", "price": round(sell_mid, 2),
         "rationale": f"~{mult['sell_mid']:g}x ATR extension — typical target for this horizon."},
        {"tier": "stretch", "price": round(sell_stretch, 2),
         "rationale": "Stretch target if momentum continues strongly."},
    ]
    stop_loss = round(buy_strong - atr_val, 2)

    return {"buy": buy, "sell": sell, "stop_loss": stop_loss}


# --- top-level entry point --------------------------------------------------------

def analyze(
    candles_by_tf: dict[str, list[dict]], fundamentals_context: dict | None, macro_data: dict | None,
    sector_data: dict | None, horizon: str = "medium",
) -> dict:
    if horizon not in HORIZON_CONFIG:
        horizon = "medium"
    cfg = HORIZON_CONFIG[horizon]

    if not any(candles_by_tf.get(tf) for tf, _ in cfg["timeframes"]):
        return {"error": "No candle data available for this symbol at any analyzed timeframe."}

    weights = cfg["weights"]
    tech = _score_technicals(candles_by_tf, cfg["timeframes"])

    zone_tf = cfg["zone_tf"]
    zone_candles = candles_by_tf.get(zone_tf) or next(
        (candles_by_tf[tf] for tf, _ in cfg["timeframes"] if candles_by_tf.get(tf)), []
    )
    current_price = zone_candles[-1]["close"]
    overlay = patterns.support_resistance_and_trend(zone_candles)

    fund = _score_fundamentals(fundamentals_context, current_price)
    street = _score_street(fundamentals_context)
    macro_score = _score_macro(macro_data, sector_data)

    overall = _clamp(
        tech["score"] * weights["technical"]
        + fund["score"] * weights["fundamental"]
        + street["score"] * weights["street"]
        + macro_score["score"] * weights["macro"]
    )

    if overall >= 0.5:
        verdict = "Strong Buy"
    elif overall >= 0.15:
        verdict = "Buy"
    elif overall <= -0.5:
        verdict = "Strong Sell"
    elif overall <= -0.15:
        verdict = "Sell"
    else:
        verdict = "Hold"

    candle_counts = [len(candles_by_tf[tf]) for tf, _ in cfg["timeframes"] if candles_by_tf.get(tf)]
    confidence = _confidence(overall, weights, tech, fund, street, macro_score, candle_counts, tech["alignment"])

    # A "Strong" verdict is a stronger claim than a plain one -- only make
    # it when confidence is actually high and the analyzed timeframes
    # aren't fighting each other; otherwise it quietly downgrades one notch
    # rather than overstating conviction the evidence doesn't support.
    if verdict in ("Strong Buy", "Strong Sell") and (confidence < 0.55 or tech["alignment"] < 0.6):
        verdict = "Buy" if verdict == "Strong Buy" else "Sell"

    zones = _price_zones(zone_candles, overlay, current_price, horizon)

    risk = current_price - zones["stop_loss"]
    reward = zones["sell"][1]["price"] - current_price
    risk_reward = round(reward / risk, 2) if risk > 0 else None

    warnings = (
        list(tech.get("warnings", []))
        + list(street.get("warnings", []))
        + list(macro_score.get("warnings", []))
    )
    if candle_counts and min(candle_counts) < 30:
        warnings.append("Limited candle history at one or more analyzed timeframes — indicators may be less reliable there.")
    if risk_reward is not None and risk_reward < 1.5:
        warnings.append(f"Risk/reward to the mid sell target is only {risk_reward:.1f}:1 — tighter than the 1.5:1 generally considered a reasonable setup.")

    return {
        "verdict": verdict,
        "score": round(overall, 3),
        "confidence": confidence,
        "current_price": current_price,
        "horizon": horizon,
        "horizon_label": HORIZON_LABELS[horizon],
        "timeframes": tech["timeframes"],
        "risk_reward": risk_reward,
        "buy": zones["buy"],
        "sell": zones["sell"],
        "stop_loss": zones["stop_loss"],
        "factors": {
            "technical": {"weight": weights["technical"], "score": round(tech["score"], 2), "items": tech["factors"]},
            "fundamental": {"weight": weights["fundamental"], "score": round(fund["score"], 2), "items": fund["factors"]},
            "street": {"weight": weights["street"], "score": round(street["score"], 2), "items": street["factors"]},
            "macro": {"weight": weights["macro"], "score": round(macro_score["score"], 2), "items": macro_score["factors"]},
        },
        "warnings": warnings,
    }
