"""Options-market sentiment: nearest-expiry implied volatility (ATM),
put/call ratios (volume + open interest), and a short list of contracts
showing unusual activity (volume far exceeding open interest -- a classic
"someone knows something" signal). Sourced from Yahoo's public
options-chain endpoint, which is NOT guaranteed stable (it may eventually
require the same crumb/cookie auth some other Yahoo endpoints do) -- every
failure mode here degrades to {"available": False} rather than raising,
so the advisor and UI simply skip this signal when it's unavailable."""
import logging
import time

import httpx

log = logging.getLogger("options")

YAHOO_OPTIONS_URL = "https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_CACHE_TTL_SECONDS = 900

_cache: dict[str, tuple[float, dict]] = {}


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def _unusual_contracts(contracts: list[dict], kind: str) -> list[dict]:
    out = []
    for c in contracts:
        vol = c.get("volume") or 0
        oi = c.get("openInterest") or 0
        if vol >= 500 and oi > 0 and vol / oi >= 3:
            out.append({
                "contract": c.get("contractSymbol"), "strike": c.get("strike"),
                "type": kind, "volume": vol, "open_interest": oi,
            })
    return out


async def fetch_options_sentiment(symbol: str) -> dict:
    cached = _cache.get(symbol)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(YAHOO_OPTIONS_URL.format(symbol=symbol), headers=_HEADERS)
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        log.warning("options fetch failed for %s", symbol)
        result = _unavailable("Options data unavailable for this symbol.")
        _cache[symbol] = (time.time(), result)
        return result

    results = (payload.get("optionChain") or {}).get("result") or []
    if not results:
        result = _unavailable("No options chain returned for this symbol.")
        _cache[symbol] = (time.time(), result)
        return result

    chain = results[0]
    quote = chain.get("quote") or {}
    current_price = quote.get("regularMarketPrice")
    option_lists = chain.get("options") or []
    if not option_lists:
        result = _unavailable("No option expirations available.")
        _cache[symbol] = (time.time(), result)
        return result

    nearest = option_lists[0]
    calls = nearest.get("calls") or []
    puts = nearest.get("puts") or []

    call_volume = sum(c.get("volume") or 0 for c in calls)
    put_volume = sum(p.get("volume") or 0 for p in puts)
    call_oi = sum(c.get("openInterest") or 0 for c in calls)
    put_oi = sum(p.get("openInterest") or 0 for p in puts)

    atm_iv = None
    if current_price and calls:
        atm_call = min(calls, key=lambda c: abs((c.get("strike") or 0) - current_price))
        atm_iv = atm_call.get("impliedVolatility")

    unusual = _unusual_contracts(calls, "call") + _unusual_contracts(puts, "put")
    unusual.sort(key=lambda u: u["volume"], reverse=True)

    result = {
        "available": True,
        "expiration": nearest.get("expirationDate"),
        "atm_iv": atm_iv,
        "put_call_volume_ratio": (put_volume / call_volume) if call_volume else None,
        "put_call_oi_ratio": (put_oi / call_oi) if call_oi else None,
        "unusual_activity": unusual[:5],
    }
    _cache[symbol] = (time.time(), result)
    return result
