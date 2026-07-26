"""Replay the advisor over historical candles to measure whether its
verdicts actually preceded the moves it implied.

The advisor asserts a confidence percentage on every call; without this,
that number is unfalsifiable. This module walks a historical series bar by
bar, asks the *same* technical scoring code what it would have said using
only the bars available at that point, then looks forward a fixed holding
window to see what price actually did.

Deliberate limitations, surfaced in the response rather than hidden:

* Only the technical factor group is replayed. Fundamentals, analyst
  ratings and macro readings are point-in-time series this app does not
  retain, and back-filling today's values would leak the future into past
  decisions -- the classic lookahead bias that makes naive backtests look
  brilliant. Technicals are the one group computable purely from bars that
  had already closed.
* Because of that, verdict thresholds are applied to the technical score
  alone, so these verdicts are not identical to a live call that also
  weighs the other three groups.
* No slippage, spread, or commission is modelled; entries are assumed at
  the close of the signal bar.

The result is an honest read on whether the technical engine has any edge
on this symbol and timeframe -- not a trading system.
"""
import logging

from . import advisor, history, indicators

log = logging.getLogger(__name__)

# Bars held after a signal before the outcome is scored, per horizon. These
# are expressed in bars rather than days so they stay meaningful whichever
# candle interval the caller replays.
HOLD_BARS = {"short": 5, "medium": 20, "long": 60}

# Candle interval used to replay each horizon, chosen so the holding window
# above spans a sensible amount of wall-clock time.
REPLAY_INTERVAL = {"short": "1h", "medium": "1d", "long": "1wk"}

# Bars of history the indicators need before the first signal can be
# trusted (slowest input is MACD's 26-period EMA plus its 9-period signal).
WARMUP_BARS = 60

# A move smaller than this is treated as "flat" rather than as a win or a
# loss for a directional call -- without it, noise decides the hit rate.
FLAT_BAND_PCT = 0.5


def _verdict_from_score(score: float) -> str:
    """Same thresholds analyze() applies, minus the confidence-based
    downgrade (which depends on factor groups this replay cannot compute)."""
    if score >= 0.5:
        return "Strong Buy"
    if score >= 0.15:
        return "Buy"
    if score <= -0.5:
        return "Strong Sell"
    if score <= -0.15:
        return "Sell"
    return "Hold"


def _outcome(verdict: str, entry: float, exit_price: float) -> tuple[str, float]:
    """Classify what happened. Returns (result, move_pct) where result is
    one of hit / miss / flat."""
    if entry <= 0:
        return "flat", 0.0
    move_pct = (exit_price - entry) / entry * 100

    if abs(move_pct) < FLAT_BAND_PCT:
        return "flat", move_pct
    if verdict in ("Strong Buy", "Buy"):
        return ("hit" if move_pct > 0 else "miss"), move_pct
    if verdict in ("Strong Sell", "Sell"):
        return ("hit" if move_pct < 0 else "miss"), move_pct
    # A Hold is "right" when price genuinely went nowhere, which the flat
    # band above has already caught -- so any sizeable move counts against it.
    return "miss", move_pct


def _replay(candles: list[dict], horizon: str) -> dict:
    hold = HOLD_BARS[horizon]
    signals = []

    # Step through every bar that has both enough history behind it and a
    # full holding window ahead of it.
    last_index = len(candles) - hold - 1
    for i in range(WARMUP_BARS, last_index + 1):
        window = candles[: i + 1]          # only bars that had already closed
        tech = advisor._score_technicals_single_tf(window, REPLAY_INTERVAL[horizon])
        score = tech["score"]
        verdict = _verdict_from_score(score)

        entry = candles[i]["close"]
        exit_price = candles[i + hold]["close"]
        result, move_pct = _outcome(verdict, entry, exit_price)

        signals.append({
            "time": candles[i]["time"],
            "verdict": verdict,
            "score": round(score, 3),
            "entry": round(entry, 2),
            "exit": round(exit_price, 2),
            "move_pct": round(move_pct, 2),
            "result": result,
        })

    return _summarise(signals, horizon, hold)


def _summarise(signals: list[dict], horizon: str, hold: int) -> dict:
    directional = [s for s in signals if s["verdict"] != "Hold"]
    scored = [s for s in directional if s["result"] in ("hit", "miss")]
    hits = [s for s in scored if s["result"] == "hit"]

    by_verdict = {}
    for verdict in ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"):
        group = [s for s in signals if s["verdict"] == verdict]
        group_scored = [s for s in group if s["result"] in ("hit", "miss")]
        group_hits = [s for s in group_scored if s["result"] == "hit"]
        by_verdict[verdict] = {
            "count": len(group),
            "scored": len(group_scored),
            "hit_rate": round(len(group_hits) / len(group_scored) * 100, 1) if group_scored else None,
            "avg_move_pct": round(sum(s["move_pct"] for s in group) / len(group), 2) if group else None,
        }

    # Baseline: what a coin flip would have produced on this same data. A
    # hit rate that merely matches the market's own drift is not an edge, so
    # the comparison is shown rather than left for the reader to guess.
    ups = [s for s in signals if s["move_pct"] > FLAT_BAND_PCT]
    downs = [s for s in signals if s["move_pct"] < -FLAT_BAND_PCT]
    moved = len(ups) + len(downs)
    baseline = round(len(ups) / moved * 100, 1) if moved else None

    hit_rate = round(len(hits) / len(scored) * 100, 1) if scored else None
    avg_win = round(sum(s["move_pct"] for s in hits) / len(hits), 2) if hits else None
    misses = [s for s in scored if s["result"] == "miss"]
    avg_loss = round(sum(s["move_pct"] for s in misses) / len(misses), 2) if misses else None

    return {
        "horizon": horizon,
        "horizon_label": advisor.HORIZON_LABELS[horizon],
        "interval": REPLAY_INTERVAL[horizon],
        "hold_bars": hold,
        "total_signals": len(signals),
        "directional_signals": len(directional),
        "scored_signals": len(scored),
        "hit_rate": hit_rate,
        "baseline_up_rate": baseline,
        "edge": round(hit_rate - baseline, 1) if (hit_rate is not None and baseline is not None) else None,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "by_verdict": by_verdict,
        "signals": signals[-60:],   # recent tail, for the equity/marker strip
    }


async def run(symbol: str, horizon: str = "medium") -> dict:
    if horizon not in HOLD_BARS:
        horizon = "medium"

    interval = REPLAY_INTERVAL[horizon]
    try:
        candles = await history.fetch_candles_interval(symbol, interval)
    except Exception as exc:
        log.warning("backtest: candle fetch failed for %s: %s", symbol, exc)
        return {"error": f"Could not load {interval} history for {symbol}."}

    needed = WARMUP_BARS + HOLD_BARS[horizon] + 10
    if len(candles) < needed:
        return {
            "error": (
                f"Not enough {interval} history to backtest {symbol} — "
                f"{len(candles)} bars available, {needed} needed."
            )
        }

    result = _replay(candles, horizon)
    result["symbol"] = symbol
    result["bars_analyzed"] = len(candles)
    result["first_time"] = candles[WARMUP_BARS]["time"]
    result["last_time"] = candles[-1]["time"]
    result["method"] = (
        "Technical score only, recomputed from bars available at each point. "
        "Fundamentals, analyst and macro inputs are excluded because this app "
        "keeps no point-in-time history for them, and back-filling today's "
        "values would leak the future into past decisions. No slippage or "
        "fees are modelled."
    )
    return result
