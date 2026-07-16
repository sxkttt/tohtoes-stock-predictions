"""Background loop that evaluates active alerts and writes alert_events for
anything that fires. Runs as an asyncio task started in main.py's lifespan,
the same pattern as the Finnhub feed task. Keyless (Yahoo + stored advisor
history only) so it doesn't compete with the advisor for Finnhub quota."""
import asyncio
import json
import logging
import time
from datetime import date

from . import db, fundamentals, history, patterns
from .candles import store

log = logging.getLogger("alerts")

CHECK_INTERVAL_SECONDS = 60
MIN_REFIRE_SECONDS = 3600  # don't re-notify the same alert more than once an hour


async def _current_price(symbol: str) -> float | None:
    live = store.get(symbol).history()
    if live:
        return live[-1]["close"]
    try:
        candles = await history.fetch_candles_interval(symbol, "1d")
        return candles[-1]["close"] if candles else None
    except Exception:
        return None


async def _check_alert(alert: dict) -> str | None:
    """Returns a human-readable message if the alert should fire now, else None."""
    symbol = alert["symbol"]
    kind = alert["kind"]
    params = json.loads(alert["params_json"])

    if kind == "price_above":
        price = await _current_price(symbol)
        if price is not None and price >= params["price"]:
            return f"{symbol} crossed above {params['price']:g} (now {price:.2f})"
        return None

    if kind == "price_below":
        price = await _current_price(symbol)
        if price is not None and price <= params["price"]:
            return f"{symbol} crossed below {params['price']:g} (now {price:.2f})"
        return None

    if kind == "pattern":
        try:
            candles = await history.fetch_candles_interval(symbol, "1d")
        except Exception:
            return None
        if len(candles) < 5:
            return None
        recent_cutoff = {c["time"] for c in candles[-2:]}
        markers = [m for m in patterns.detect_candlestick_patterns(candles)
                   if m["confidence"] in ("medium", "high") and m["time"] in recent_cutoff]
        if markers:
            m = markers[-1]
            return f"{symbol}: {m['pattern']} ({m['confidence']} confidence, {m['direction']})"
        return None

    if kind == "earnings_reminder":
        context = await fundamentals.fetch_context(symbol)
        next_date = (context or {}).get("next_earnings_date")
        if not next_date:
            return None
        days_away = (date.fromisoformat(next_date) - date.today()).days
        if 0 <= days_away <= 2:
            return f"{symbol} reports earnings on {next_date} ({days_away} day{'s' if days_away != 1 else ''} away)"
        return None

    if kind == "verdict_change":
        runs = await db.get_advisor_history(symbol, limit=2)
        if len(runs) < 2:
            return None
        prev, latest = runs[-2], runs[-1]
        if prev["verdict"] != latest["verdict"]:
            return f"{symbol} advisor verdict changed: {prev['verdict']} → {latest['verdict']}"
        return None

    return None


async def _run_once():
    alerts = await db.get_active_alerts()
    now = time.time()
    for alert in alerts:
        last_fired = alert.get("last_fired_ts")
        if last_fired and now - last_fired < MIN_REFIRE_SECONDS:
            continue
        try:
            message = await _check_alert(alert)
        except Exception:
            log.exception("alert check failed for alert id=%s", alert["id"])
            continue
        if message:
            await db.create_alert_event(alert["id"], alert["symbol"], message)
            await db.mark_alert_fired(alert["id"])


async def run_alerts_loop():
    while True:
        try:
            await _run_once()
        except Exception:
            log.exception("alerts loop iteration failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
