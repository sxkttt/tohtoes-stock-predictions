"""Connects to Finnhub's real-time trade websocket and fans out ticks
to the candle aggregator, the database, and connected frontend clients."""
import asyncio
import json
import logging
import time

import websockets

from . import config, db
from .candles import store
from . import patterns

logger = logging.getLogger("finnhub_feed")

# symbol -> set of asyncio.Queue for connected frontend websocket clients
_subscribers: dict[str, set[asyncio.Queue]] = {}
_watched_symbols: set[str] = set()
_upstream_ws = None
_upstream_lock = asyncio.Lock()


def add_subscriber(symbol: str, queue: asyncio.Queue):
    _subscribers.setdefault(symbol, set()).add(queue)
    _watched_symbols.add(symbol)


def remove_subscriber(symbol: str, queue: asyncio.Queue):
    subs = _subscribers.get(symbol)
    if subs and queue in subs:
        subs.remove(queue)


async def _broadcast(symbol: str, payload: dict):
    for q in list(_subscribers.get(symbol, [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def _subscribe_upstream(ws, symbol: str):
    await ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))


async def _handle_trade_message(msg: dict):
    for t in msg.get("data", []):
        symbol = t["s"]
        price = float(t["p"])
        volume = float(t.get("v", 0))
        ts_ms = int(t["t"])

        await db.insert_tick(symbol, price, volume, ts_ms)

        state = store.get(symbol)
        current, finalized = state.add_tick(price, volume, ts_ms)

        await _broadcast(symbol, {"type": "candle_update", "symbol": symbol, "candle": current})

        if finalized is not None:
            await db.upsert_candle(
                symbol, finalized["time"], finalized["open"], finalized["high"],
                finalized["low"], finalized["close"], finalized["volume"],
            )
            analysis = patterns.analyze(state.history())
            await _broadcast(symbol, {"type": "analysis", "symbol": symbol, **analysis})


async def run_feed():
    """Long-running background task: maintains the upstream Finnhub connection,
    reconnecting with backoff, and (re)subscribing to all watched symbols."""
    if not config.FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set; live feed disabled. Set it in .env")
        return

    backoff = 1
    while True:
        try:
            async with websockets.connect(config.FINNHUB_WS_URL, ping_interval=20) as ws:
                global _upstream_ws
                _upstream_ws = ws
                backoff = 1
                for sym in list(_watched_symbols):
                    await _subscribe_upstream(ws, sym)
                logger.info("Connected to Finnhub feed")

                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "trade":
                        await _handle_trade_message(msg)
                    elif msg.get("type") == "ping":
                        continue
        except Exception as e:
            logger.warning("Finnhub feed disconnected (%s); reconnecting in %ss", e, backoff)
            _upstream_ws = None
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


async def ensure_symbol_subscribed(symbol: str):
    _watched_symbols.add(symbol)
    if _upstream_ws is not None:
        async with _upstream_lock:
            await _subscribe_upstream(_upstream_ws, symbol)
