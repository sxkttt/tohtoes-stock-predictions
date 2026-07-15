"""NASDAQ + NYSE symbol directory, used to power the symbol search box so
users can find any stock on those two exchanges by ticker or company name
(instead of needing to already know the exact ticker).

Finnhub's /stock/symbol?exchange=US listing is ~30k instruments across every
US venue and instrument type; we fetch it once, filter down to common
stocks + ADRs listed on NASDAQ (mic=XNAS) or NYSE (mic=XNYS), and cache the
result to disk so subsequent launches don't need to re-download ~7MB.
"""
import json
import logging
import time

import httpx

from . import config

log = logging.getLogger("symbols")

CACHE_PATH = config.ROOT_DIR / "data" / "us_symbols_cache.json"
CACHE_MAX_AGE_SECONDS = 7 * 24 * 3600  # refresh weekly
FINNHUB_SYMBOL_URL = "https://finnhub.io/api/v1/stock/symbol"
_INCLUDE_TYPES = {"Common Stock", "ADR"}
_INCLUDE_MICS = {"XNAS": "NASDAQ", "XNYS": "NYSE"}

_symbols: list[dict] = []  # [{symbol, description, exchange}]
_loaded_at: float = 0.0


def _load_cache_from_disk() -> list[dict] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return payload.get("symbols")
    except Exception:
        log.exception("Failed to read symbol cache")
        return None


def _save_cache_to_disk(symbols: list[dict]):
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps({"fetched_at": time.time(), "symbols": symbols}), encoding="utf-8"
        )
    except Exception:
        log.exception("Failed to write symbol cache")


def _cache_age_seconds() -> float:
    if not CACHE_PATH.exists():
        return float("inf")
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return time.time() - payload.get("fetched_at", 0)
    except Exception:
        return float("inf")


async def _fetch_from_finnhub() -> list[dict]:
    params = {"exchange": "US", "token": config.FINNHUB_API_KEY}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(FINNHUB_SYMBOL_URL, params=params)
        resp.raise_for_status()
        raw = resp.json()

    filtered = []
    for item in raw:
        mic = item.get("mic")
        itype = item.get("type")
        symbol = item.get("symbol")
        if mic in _INCLUDE_MICS and itype in _INCLUDE_TYPES and symbol and "." not in symbol:
            filtered.append({
                "symbol": symbol,
                "description": (item.get("description") or "").title(),
                "exchange": _INCLUDE_MICS[mic],
            })
    return filtered


async def ensure_loaded():
    """Populate the in-memory index: instantly from disk cache if present,
    then refresh from Finnhub in the background if the cache is stale/missing."""
    global _symbols, _loaded_at

    if not _symbols:
        cached = _load_cache_from_disk()
        if cached:
            _symbols = cached
            _loaded_at = time.time()
            log.info("Loaded %d NASDAQ/NYSE symbols from disk cache", len(_symbols))

    if _cache_age_seconds() > CACHE_MAX_AGE_SECONDS:
        if not config.FINNHUB_API_KEY:
            return
        try:
            fresh = await _fetch_from_finnhub()
            if fresh:
                _symbols = fresh
                _loaded_at = time.time()
                _save_cache_to_disk(fresh)
                log.info("Refreshed NASDAQ/NYSE symbol directory: %d symbols", len(fresh))
        except Exception:
            log.exception("Failed to refresh symbol directory from Finnhub")


def search(query: str, limit: int = 15) -> list[dict]:
    q = query.strip().upper()
    if not q or not _symbols:
        return []

    exact, symbol_starts, desc_starts, contains = [], [], [], []
    for item in _symbols:
        symbol = item["symbol"]
        desc = item["description"].upper()
        if symbol == q:
            exact.append(item)
        elif symbol.startswith(q):
            symbol_starts.append(item)
        elif desc.startswith(q):
            desc_starts.append(item)
        elif q in symbol or q in desc:
            contains.append(item)

    symbol_starts.sort(key=lambda d: len(d["symbol"]))
    desc_starts.sort(key=lambda d: d["description"])
    contains.sort(key=lambda d: d["description"])
    ranked = exact + symbol_starts + desc_starts + contains
    return ranked[:limit]
