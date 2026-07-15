import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import advisor, config, db, finnhub_feed, fundamentals, history, macro, patterns, settings, symbols
from .candles import store

PERIODS = {"LIVE", *history.RANGE_INTERVAL_PRESETS.keys()}

logging.basicConfig(level=logging.INFO)

_feed_task: asyncio.Task | None = None
_symbols_task: asyncio.Task | None = None
FRONTEND_DIR = config.FRONTEND_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    global _feed_task, _symbols_task
    _feed_task = asyncio.create_task(finnhub_feed.run_feed())
    _symbols_task = asyncio.create_task(symbols.ensure_loaded())
    yield
    if _feed_task:
        _feed_task.cancel()
    if _symbols_task:
        _symbols_task.cancel()
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
async def history_endpoint(symbol: str, response: Response, period: str = "LIVE", interval: str = ""):
    # Historical/live candle data must always be fetched fresh -- never let
    # the browser's HTTP cache serve yesterday's "1D" window after midnight.
    response.headers["Cache-Control"] = "no-store"
    symbol = symbol.upper()
    period = period.upper()
    if period not in PERIODS:
        period = "LIVE"
    interval = interval.lower().strip()

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
                candles, used_interval = await history.fetch_candles_custom(symbol, period, interval)
            else:
                candles = await history.fetch_candles(symbol, period)
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

    industry = ((context or {}).get("profile") or {}).get("industry") if isinstance(context, dict) else None
    try:
        sector_data = await macro.fetch_sector_trend(industry)
    except Exception:
        log.exception("advisor sector trend fetch failed for industry=%s", industry)
        sector_data = None

    result = advisor.analyze(candles_by_tf, context, macro_data, sector_data, horizon)
    return {"symbol": symbol, "horizon": horizon, **result}


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
