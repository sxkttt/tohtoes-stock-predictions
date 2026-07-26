"""Measure what actually happened after each candlestick pattern fired.

The pattern list tells you a Bullish Engulfing appeared and calls it
bullish. This asks the only question that matters: on this symbol, over
this history, did price actually rise afterwards -- and more often than it
rose on an average bar?

That last comparison is the point. In a stock that drifted up all year,
*every* bullish pattern will look like it "worked". Each pattern's follow-
through is therefore reported against the base rate of the same series, so
a pattern only shows an edge if it beat simply being long at random.
"""
import logging

from . import history, patterns

log = logging.getLogger(__name__)

# Bars measured forward from the pattern's own bar.
LOOKAHEAD_BARS = 5

# Moves smaller than this count as "flat" rather than as follow-through in
# either direction.
FLAT_BAND_PCT = 0.5

# A pattern needs at least this many occurrences before a percentage is
# worth showing; below it the number is noise dressed as a statistic.
MIN_OCCURRENCES = 5


def _forward_move_pct(candles: list[dict], i: int, lookahead: int) -> float | None:
    if i + lookahead >= len(candles):
        return None
    entry = candles[i]["close"]
    if entry <= 0:
        return None
    return (candles[i + lookahead]["close"] - entry) / entry * 100


def _base_rates(candles: list[dict], lookahead: int) -> dict:
    """How often price rose over the same lookahead across every bar --
    the yardstick each pattern has to beat."""
    moves = []
    for i in range(len(candles) - lookahead):
        move = _forward_move_pct(candles, i, lookahead)
        if move is not None:
            moves.append(move)
    if not moves:
        return {"up_rate": None, "avg_move_pct": None, "samples": 0}

    ups = [m for m in moves if m > FLAT_BAND_PCT]
    downs = [m for m in moves if m < -FLAT_BAND_PCT]
    decided = len(ups) + len(downs)
    return {
        "up_rate": round(len(ups) / decided * 100, 1) if decided else None,
        "avg_move_pct": round(sum(moves) / len(moves), 2),
        "samples": len(moves),
    }


def analyse(candles: list[dict], lookahead: int = LOOKAHEAD_BARS) -> dict:
    markers = patterns.detect_candlestick_patterns(candles)
    time_to_index = {c["time"]: i for i, c in enumerate(candles)}

    grouped: dict[str, dict] = {}
    for marker in markers:
        i = time_to_index.get(marker["time"])
        if i is None:
            continue
        move = _forward_move_pct(candles, i, lookahead)
        if move is None:
            continue   # too close to the end of the series to have an outcome

        entry = grouped.setdefault(marker["pattern"], {
            "pattern": marker["pattern"],
            "direction": marker["direction"],
            "moves": [],
        })
        entry["moves"].append(move)

    base = _base_rates(candles, lookahead)
    results = []
    for entry in grouped.values():
        moves = entry["moves"]
        ups = [m for m in moves if m > FLAT_BAND_PCT]
        downs = [m for m in moves if m < -FLAT_BAND_PCT]
        decided = len(ups) + len(downs)
        up_rate = round(len(ups) / decided * 100, 1) if decided else None
        avg_move = round(sum(moves) / len(moves), 2)

        # "Followed through" means price moved the way the pattern's own
        # label predicted. Neutral patterns signal indecision, so they are
        # scored on whether price stayed put.
        if entry["direction"] == "bullish":
            followed = len(ups)
        elif entry["direction"] == "bearish":
            followed = len(downs)
        else:
            followed = len(moves) - decided
        follow_rate = round(followed / len(moves) * 100, 1) if moves else None

        edge = None
        if up_rate is not None and base["up_rate"] is not None:
            if entry["direction"] == "bullish":
                edge = round(up_rate - base["up_rate"], 1)
            elif entry["direction"] == "bearish":
                edge = round((100 - up_rate) - (100 - base["up_rate"]), 1)

        results.append({
            "pattern": entry["pattern"],
            "direction": entry["direction"],
            "occurrences": len(moves),
            "follow_through_rate": follow_rate,
            "up_rate": up_rate,
            "avg_move_pct": avg_move,
            "best_pct": round(max(moves), 2),
            "worst_pct": round(min(moves), 2),
            "edge_vs_base": edge,
            "reliable": len(moves) >= MIN_OCCURRENCES,
        })

    # Most-seen first, but always sink the small samples so a 100% rate
    # from two occurrences never tops the table.
    results.sort(key=lambda r: (r["reliable"], r["occurrences"]), reverse=True)

    return {
        "lookahead_bars": lookahead,
        "base_rate": base,
        "min_occurrences": MIN_OCCURRENCES,
        "patterns": results,
    }


async def run(symbol: str, period: str = "5Y", lookahead: int = LOOKAHEAD_BARS) -> dict:
    try:
        candles = await history.fetch_candles(symbol, period)
    except Exception as exc:
        log.warning("pattern_stats: candle fetch failed for %s: %s", symbol, exc)
        return {"error": f"Could not load history for {symbol}."}

    if len(candles) < lookahead + 30:
        return {"error": f"Not enough history to measure pattern outcomes for {symbol}."}

    result = analyse(candles, lookahead)
    result["symbol"] = symbol
    result["period"] = period
    result["bars_analyzed"] = len(candles)
    result["method"] = (
        f"Each pattern's next {lookahead} bars measured across {len(candles)} bars of "
        f"{period} history, compared against how often this same series rose over any "
        f"{lookahead} bars. Past behaviour on one symbol; not a prediction."
    )
    return result
