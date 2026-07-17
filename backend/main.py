import asyncio
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import (
    advisor, alerts, config, db, econ_calendar, finnhub_feed, fundamentals, history,
    indicators, macro, market_status, news, options, patterns, settings, symbols, version,
)
from .candles import store

PERIODS = {"LIVE", *history.RANGE_INTERVAL_PRESETS.keys()}

# Set by the edition-specific desktop_app.py *before* importing this module
# (e.g. "sxkttt/tohtoes-stock-predictions") to enable the auto-update check
# against that repo's GitHub releases. Left unset, the check just reports
# itself disabled -- this is how PulseChart (not published anywhere) opts
# out without needing its own code path.
UPDATE_REPO = os.environ.get("UPDATE_REPO")

# How long each horizon's price call needs to "play out" before it's fair
# to check whether it was right -- mirrors the horizon labels in advisor.py.
HORIZON_WINDOW_DAYS = {"short": 5, "medium": 21, "long": 90}

logging.basicConfig(level=logging.INFO)

_feed_task: asyncio.Task | None = None
_symbols_task: asyncio.Task | None = None
_alerts_task: asyncio.Task | None = None
FRONTEND_DIR = config.FRONTEND_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    global _feed_task, _symbols_task, _alerts_task
    _feed_task = asyncio.create_task(finnhub_feed.run_feed())
    _symbols_task = asyncio.create_task(symbols.ensure_loaded())
    _alerts_task = asyncio.create_task(alerts.run_alerts_loop())
    yield
    if _feed_task:
        _feed_task.cancel()
    if _symbols_task:
        _symbols_task.cancel()
    if _alerts_task:
        _alerts_task.cancel()
    await db.close_db()


app = FastAPI(lifespan=lifespan)


async def restart_feed():
    """Cancel the current Finnhub feed task (whatever state it's in --
    connected, reconnecting, or already exited due to a missing key) and
    start a fresh one so a newly-saved API key takes effect immediately."""
    global _feed_task
    if _feed_task and not _feed_task.done():
        _feed_task.cancel()
        try:
            await _feed_task
        except (asyncio.CancelledError, Exception):
            pass
    _feed_task = asyncio.create_task(finnhub_feed.run_feed())


class NoCacheStaticFiles(StaticFiles):
    """Always revalidate static assets (index.html/app.js/style.css) with
    the server instead of letting the browser serve a stale cached copy --
    otherwise a code change can silently not take effect after a reload."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


@app.get("/")
async def index():
    response = FileResponse(FRONTEND_DIR / "index.html")
    response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", NoCacheStaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/api/history/{symbol}")
async def history_endpoint(
    symbol: str, response: Response, period: str = "LIVE", interval: str = "", prepost: bool = False
):
    # Historical/live candle data must always be fetched fresh -- never let
    # the browser's HTTP cache serve yesterday's "1D" window after midnight.
    response.headers["Cache-Control"] = "no-store"
    symbol = symbol.upper()
    period = period.upper()
    if period not in PERIODS:
        period = "LIVE"
    interval = interval.lower().strip()
    # Pre/post-market candles only make sense on an intraday view -- Yahoo
    # ignores the flag on daily+ ranges anyway, but keep it explicit here.
    prepost = prepost and period in ("LIVE", "1D", "1W")

    used_interval = None
    if period == "LIVE":
        state = store.get(symbol)
        live_history = state.history()
        if len(live_history) >= 20:
            candles = live_history
        else:
            candles = await db.get_recent_candles(symbol, config.CANDLE_HISTORY_LEN)
        source = "live"
    else:
        try:
            if interval:
                candles, used_interval = await history.fetch_candles_custom(symbol, period, interval, prepost)
            else:
                candles = await history.fetch_candles(symbol, period, prepost)
                used_interval = history.RANGE_INTERVAL_PRESETS[period][1]
        except Exception:
            logging.getLogger("main").exception("Yahoo history fetch failed for %s/%s/%s", symbol, period, interval)
            candles = []
        source = "yahoo"

    analysis = patterns.analyze(candles) if candles else {"overlay": {}, "candlestick_markers": []}
    return {
        "symbol": symbol, "period": period, "interval": used_interval,
        "source": source, "candles": candles, **analysis,
    }


@app.get("/api/indicators/{symbol}")
async def indicators_endpoint(symbol: str, response: Response, period: str = "LIVE", interval: str = ""):
    """RSI/MACD/ADX series aligned bar-for-bar with /api/history's candles
    for the same period+interval, so the frontend can draw indicator
    sub-panes synced to the main chart."""
    response.headers["Cache-Control"] = "no-store"
    symbol = symbol.upper()
    period = period.upper()
    if period not in PERIODS:
        period = "LIVE"
    interval = interval.lower().strip()

    if period == "LIVE":
        state = store.get(symbol)
        live_history = state.history()
        candles = live_history if len(live_history) >= 20 else await db.get_recent_candles(symbol, config.CANDLE_HISTORY_LEN)
    else:
        try:
            if interval:
                candles, _ = await history.fetch_candles_custom(symbol, period, interval)
            else:
                candles = await history.fetch_candles(symbol, period)
        except Exception:
            logging.getLogger("main").exception("Yahoo history fetch failed for indicators %s/%s/%s", symbol, period, interval)
            candles = []

    if not candles:
        return {"symbol": symbol, "series": []}

    closes = [c["close"] for c in candles]
    rsi_vals = indicators.rsi_series(closes, 14)
    macd_vals = indicators.macd_full(closes)
    adx_vals = indicators.adx_full(candles, 14)

    def _at(arr, i):
        return arr[i] if i < len(arr) else None

    series = [
        {
            "time": c["time"],
            "rsi": _at(rsi_vals, i),
            "macd": _at(macd_vals["macd"], i),
            "signal": _at(macd_vals["signal"], i),
            "hist": _at(macd_vals["histogram"], i),
            "adx": _at(adx_vals["adx"], i),
        }
        for i, c in enumerate(candles)
    ]
    return {"symbol": symbol, "series": series}


@app.get("/api/symbols/search")
async def symbols_search(q: str = ""):
    return {"results": symbols.search(q)}


@app.get("/api/advisor/{symbol}")
async def advisor_endpoint(symbol: str, response: Response, horizon: str = ""):
    # Always fresh -- a stale cached recommendation would be actively harmful.
    response.headers["Cache-Control"] = "no-store"
    symbol = symbol.upper()
    horizon = horizon.lower()
    if horizon not in advisor.HORIZONS:
        horizon = "medium"

    log = logging.getLogger("main")
    cfg = advisor.HORIZON_CONFIG[horizon]
    timeframe_keys = [tf for tf, _ in cfg["timeframes"]]

    fetches = [history.fetch_candles_interval(symbol, tf) for tf in timeframe_keys]
    fetches.append(fundamentals.fetch_context(symbol))
    fetches.append(macro.fetch_macro())
    fetches.append(options.fetch_options_sentiment(symbol))
    results = await asyncio.gather(*fetches, return_exceptions=True)

    candles_by_tf: dict[str, list[dict]] = {}
    for tf, res in zip(timeframe_keys, results[:len(timeframe_keys)]):
        if isinstance(res, Exception):
            log.exception("advisor candle fetch failed for %s/%s", symbol, tf)
            candles_by_tf[tf] = []
        else:
            candles_by_tf[tf] = res

    context = results[len(timeframe_keys)]
    if isinstance(context, Exception):
        log.exception("advisor fundamentals fetch failed for %s", symbol)
        context = None

    macro_data = results[len(timeframe_keys) + 1]
    if isinstance(macro_data, Exception):
        log.exception("advisor macro fetch failed")
        macro_data = None

    options_data = results[len(timeframe_keys) + 2]
    if isinstance(options_data, Exception):
        log.exception("advisor options fetch failed for %s", symbol)
        options_data = None

    industry = ((context or {}).get("profile") or {}).get("industry") if isinstance(context, dict) else None
    try:
        sector_data = await macro.fetch_sector_trend(industry)
    except Exception:
        log.exception("advisor sector trend fetch failed for industry=%s", industry)
        sector_data = None

    result = advisor.analyze(candles_by_tf, context, macro_data, sector_data, horizon, options_data)
    if "error" not in result:
        await db.insert_advisor_run(
            symbol, horizon, result["verdict"], result["score"], result["confidence"], result["current_price"]
        )
        result["options"] = options_data or {"available": False, "reason": "Options data unavailable."}
    return {"symbol": symbol, "horizon": horizon, **result}


@app.get("/api/advisor-history/{symbol}")
async def advisor_history_endpoint(symbol: str, limit: int = 30):
    return {"symbol": symbol.upper(), "runs": await db.get_advisor_history(symbol.upper(), limit)}


async def _score_pending_advisor_runs():
    """Backfills outcome_hit for advisor_runs whose horizon window has
    elapsed, by comparing the price at call-time to a fresh daily close.
    A Buy/Strong Buy "hits" if price is now higher, Sell/Strong Sell if
    lower, Hold if price stayed within 2%."""
    log = logging.getLogger("main")
    now = int(time.time())
    shortest_window = min(HORIZON_WINDOW_DAYS.values())
    pending = await db.get_unscored_runs_before(now - shortest_window * 86400)

    for run in pending:
        window_days = HORIZON_WINDOW_DAYS.get(run["horizon"], 21)
        if now - run["ts"] < window_days * 86400:
            continue  # this run's own horizon window hasn't elapsed yet

        try:
            candles = await history.fetch_candles_interval(run["symbol"], "1d")
            if not candles:
                continue
            current_price = candles[-1]["close"]
        except Exception:
            log.warning("accuracy backtrack: price fetch failed for %s", run["symbol"])
            continue

        verdict = run["verdict"]
        if verdict in ("Strong Buy", "Buy"):
            hit = current_price > run["price"]
        elif verdict in ("Strong Sell", "Sell"):
            hit = current_price < run["price"]
        else:
            hit = abs(current_price - run["price"]) / run["price"] <= 0.02

        await db.set_run_outcome(run["id"], current_price, hit)


@app.get("/api/advisor-accuracy")
async def advisor_accuracy_endpoint():
    await _score_pending_advisor_runs()
    return {"stats": await db.get_accuracy_stats()}


# --- market context: sector heatmap, economic calendar, options -----------------

@app.get("/api/sectors")
async def sectors_endpoint():
    return {"sectors": await macro.fetch_sector_heatmap()}


@app.get("/api/calendar/{symbol}")
async def calendar_endpoint(symbol: str):
    symbol = symbol.upper()
    log = logging.getLogger("main")
    try:
        context = await fundamentals.fetch_context(symbol)
    except Exception:
        log.exception("calendar fundamentals fetch failed for %s", symbol)
        context = None

    events = list(econ_calendar.upcoming_events(10))
    earnings_date = (context or {}).get("next_earnings_date")
    if earnings_date:
        events.append({"date": earnings_date, "type": "earnings", "label": f"{symbol} Earnings"})
    events.sort(key=lambda e: e["date"])
    return {"symbol": symbol, "events": events[:8]}


@app.get("/api/options/{symbol}")
async def options_endpoint(symbol: str):
    return await options.fetch_options_sentiment(symbol.upper())


@app.get("/api/news/{symbol}")
async def news_endpoint(symbol: str):
    return await news.fetch_news(symbol.upper())


@app.get("/api/market-status")
async def market_status_endpoint(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return market_status.get_market_status()


# --- watchlist ----------------------------------------------------------------

@app.get("/api/watchlist")
async def get_watchlist_endpoint():
    return {"watchlist": await db.get_watchlist()}


@app.post("/api/watchlist/{symbol}")
async def add_watchlist_endpoint(symbol: str):
    await db.add_watchlist(symbol.upper())
    return {"ok": True}


@app.delete("/api/watchlist/{symbol}")
async def remove_watchlist_endpoint(symbol: str):
    await db.remove_watchlist(symbol.upper())
    return {"ok": True}


async def _quote_for_watchlist(symbol: str) -> dict:
    try:
        candles = await history.fetch_candles(symbol, "1D")
    except Exception:
        candles = []
    if not candles:
        return {"symbol": symbol, "price": None, "change_pct": None, "sparkline": []}
    first, last = candles[0]["close"], candles[-1]["close"]
    change_pct = (last - first) / first * 100 if first else None
    step = max(1, len(candles) // 20)
    sparkline = [c["close"] for c in candles[::step]]
    return {"symbol": symbol, "price": last, "change_pct": change_pct, "sparkline": sparkline}


@app.get("/api/watchlist/quotes")
async def watchlist_quotes_endpoint():
    """Price, day % change, a thinned sparkline series, and the most
    recent stored advisor verdict for every watchlisted symbol."""
    entries = await db.get_watchlist()
    symbols_list = [e["symbol"] for e in entries]
    quotes = await asyncio.gather(*[_quote_for_watchlist(s) for s in symbols_list], return_exceptions=True)

    results = []
    for sym, q in zip(symbols_list, quotes):
        if isinstance(q, Exception):
            logging.getLogger("main").exception("watchlist quote failed for %s", sym)
            results.append({"symbol": sym, "price": None, "change_pct": None, "sparkline": []})
        else:
            results.append(q)

    for r in results:
        recent = await db.get_advisor_history(r["symbol"], limit=1)
        r["last_verdict"] = recent[-1]["verdict"] if recent else None

    return {"quotes": results}


# --- alerts ---------------------------------------------------------------------

class AlertPayload(BaseModel):
    symbol: str
    kind: str
    params: dict = {}


class SeenPayload(BaseModel):
    ids: list[int]


@app.post("/api/alerts")
async def create_alert_endpoint(payload: AlertPayload):
    alert_id = await db.create_alert(payload.symbol.upper(), payload.kind, json.dumps(payload.params))
    return {"ok": True, "id": alert_id}


@app.get("/api/alerts")
async def get_alerts_endpoint(symbol: str = ""):
    return {"alerts": await db.get_alerts(symbol.upper() if symbol else None)}


@app.delete("/api/alerts/{alert_id}")
async def delete_alert_endpoint(alert_id: int):
    await db.delete_alert(alert_id)
    return {"ok": True}


@app.get("/api/alerts/pending")
async def pending_alerts_endpoint():
    return {"events": await db.get_pending_alert_events()}


@app.post("/api/alerts/seen")
async def mark_alerts_seen_endpoint(payload: SeenPayload):
    await db.mark_alert_events_seen(payload.ids)
    return {"ok": True}


# --- paper trading portfolio ----------------------------------------------------

class TradePayload(BaseModel):
    symbol: str
    side: str
    qty: float
    price: float
    note: str = ""


@app.post("/api/portfolio/trades")
async def add_trade_endpoint(payload: TradePayload):
    if payload.side not in ("buy", "sell"):
        return {"ok": False, "message": "side must be 'buy' or 'sell'."}
    if payload.qty <= 0 or payload.price <= 0:
        return {"ok": False, "message": "qty and price must be positive."}
    trade_id = await db.add_paper_trade(payload.symbol.upper(), payload.side, payload.qty, payload.price, payload.note)
    return {"ok": True, "id": trade_id}


@app.get("/api/portfolio/trades")
async def get_trades_endpoint(symbol: str = ""):
    return {"trades": await db.get_paper_trades(symbol.upper() if symbol else None)}


@app.delete("/api/portfolio/trades/{trade_id}")
async def delete_trade_endpoint(trade_id: int):
    await db.delete_paper_trade(trade_id)
    return {"ok": True}


@app.get("/api/portfolio")
async def get_portfolio_endpoint():
    """Aggregates paper trades into open positions on an average-cost
    basis, with realized P&L from closes and unrealized P&L from a fresh
    quote on whatever's still open."""
    trades = await db.get_paper_trades()
    by_symbol: dict[str, list[dict]] = {}
    for t in trades:
        by_symbol.setdefault(t["symbol"], []).append(t)

    positions = []
    realized_total = 0.0
    for sym, sym_trades in by_symbol.items():
        qty = 0.0
        avg_cost = 0.0
        realized = 0.0
        for t in sym_trades:  # already ts ASC from db.get_paper_trades
            if t["side"] == "buy":
                new_qty = qty + t["qty"]
                avg_cost = (avg_cost * qty + t["price"] * t["qty"]) / new_qty if new_qty else 0.0
                qty = new_qty
            else:
                sell_qty = min(t["qty"], qty)
                realized += (t["price"] - avg_cost) * sell_qty
                qty -= sell_qty
                if qty <= 1e-9:
                    qty = 0.0
                    avg_cost = 0.0
        realized_total += realized

        current_price = None
        unrealized = 0.0
        if qty > 0:
            try:
                candles = await history.fetch_candles(sym, "1D")
                current_price = candles[-1]["close"] if candles else avg_cost
            except Exception:
                current_price = avg_cost
            unrealized = (current_price - avg_cost) * qty

        positions.append({
            "symbol": sym, "qty": round(qty, 6), "avg_cost": round(avg_cost, 4),
            "current_price": current_price, "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(realized, 2),
        })

    return {"positions": positions, "realized_total": round(realized_total, 2)}


@app.get("/api/update-check")
async def update_check_endpoint():
    if not UPDATE_REPO:
        return {"enabled": False, "update_available": False, "current": version.APP_VERSION, "latest": None}

    latest = None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"https://raw.githubusercontent.com/{UPDATE_REPO}/main/backend/version.py")
            resp.raise_for_status()
            match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', resp.text)
            latest = match.group(1) if match else None
    except Exception:
        logging.getLogger("main").warning("update check fetch failed")

    return {
        "enabled": True,
        "current": version.APP_VERSION,
        "latest": latest,
        "update_available": bool(latest and latest != version.APP_VERSION),
        "download_url": {
            "win": f"https://github.com/{UPDATE_REPO}/releases/download/win-latest/TohtoeStockPredictions.exe",
            "mac": f"https://github.com/{UPDATE_REPO}/releases/download/mac-latest/TohtoeStockPredictionsForMac.dmg",
        },
    }


class ApiKeyPayload(BaseModel):
    api_key: str = ""


@app.get("/api/settings/api-key")
async def get_api_key_status():
    key = config.FINNHUB_API_KEY
    if len(key) >= 8:
        masked = f"{key[:4]}···{key[-4:]}"
    elif key:
        masked = "set"
    else:
        masked = ""
    return {"is_set": bool(key), "masked": masked}


@app.post("/api/settings/api-key/check")
async def check_api_key_endpoint(payload: ApiKeyPayload):
    valid, message = await settings.check_api_key(payload.api_key)
    return {"valid": valid, "message": message}


@app.post("/api/settings/api-key")
async def save_api_key_endpoint(payload: ApiKeyPayload):
    key = payload.api_key.strip()
    if not key:
        return {"ok": False, "message": "API key cannot be empty."}
    config.set_api_key(key)
    await restart_feed()
    return {"ok": True, "message": "API key saved. Reconnecting to Finnhub…"}


@app.websocket("/ws/{symbol}")
async def ws_endpoint(websocket: WebSocket, symbol: str):
    symbol = symbol.upper()
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    finnhub_feed.add_subscriber(symbol, queue)
    await finnhub_feed.ensure_symbol_subscribed(symbol)

    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        finnhub_feed.remove_subscriber(symbol, queue)
