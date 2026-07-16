"""Macro market-condition proxies: VIX (risk/fear sentiment), the 10-year
Treasury yield (^TNX) and 13-week T-bill (^IRX, a Fed-policy-rate proxy)
plus the yield-curve spread between them, the S&P 500's own trend regime
(bull/bear/neutral off its 50/200-day SMAs -- "don't fight the tape"), and
a per-symbol sector ETF trend. These are the standard, measurable
stand-ins professionals use for "geopolitics / interest rates / macro
risk" -- there's no such thing as a literal geopolitics API, but a VIX
spike, an inverted yield curve, or a sharply rising 10-year yield is
exactly how that kind of risk shows up in markets. Sourced from Yahoo's
public chart endpoint (no key needed).
"""
import asyncio
import logging
import time

import httpx

from . import indicators

log = logging.getLogger("macro")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_CACHE_TTL_SECONDS = 3600  # macro conditions don't need to be fresher than this

_cache: dict | None = None
_cached_at: float = 0.0

# Finnhub's finnhubIndustry values aren't a fixed enum we can key an exact
# dict on, so this matches by keyword against the standard SPDR sector
# ETFs. Order matters -- more specific terms are checked first.
_SECTOR_ETF_KEYWORDS = [
    ("semiconductor", "XLK"), ("software", "XLK"), ("technology", "XLK"),
    ("hardware", "XLK"), ("it services", "XLK"), ("internet", "XLK"),
    ("bank", "XLF"), ("insurance", "XLF"), ("capital markets", "XLF"), ("financial", "XLF"),
    ("biotechnology", "XLV"), ("pharmaceutical", "XLV"), ("health", "XLV"),
    ("medical", "XLV"), ("life sciences", "XLV"),
    ("oil", "XLE"), ("gas", "XLE"), ("energy", "XLE"),
    ("industrial", "XLI"), ("aerospace", "XLI"), ("machinery", "XLI"),
    ("airline", "XLI"), ("transportation", "XLI"), ("defense", "XLI"),
    ("real estate", "XLRE"), ("reit", "XLRE"),
    ("retail", "XLY"), ("consumer cyclical", "XLY"), ("auto", "XLY"),
    ("hotel", "XLY"), ("leisure", "XLY"), ("apparel", "XLY"), ("homebuilding", "XLY"),
    ("consumer defensive", "XLP"), ("food", "XLP"), ("beverage", "XLP"),
    ("household", "XLP"), ("tobacco", "XLP"), ("grocery", "XLP"),
    ("material", "XLB"), ("chemical", "XLB"), ("mining", "XLB"), ("metal", "XLB"), ("paper", "XLB"),
    ("utilit", "XLU"),
    ("communication", "XLC"), ("media", "XLC"), ("telecom", "XLC"), ("entertainment", "XLC"),
]

_sector_cache: dict[str, tuple[float, dict | None]] = {}

SECTOR_ETF_NAMES = {
    "XLK": "Technology", "XLF": "Financials", "XLV": "Health Care", "XLE": "Energy",
    "XLI": "Industrials", "XLRE": "Real Estate", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLB": "Materials", "XLU": "Utilities", "XLC": "Communication Services",
}

_heatmap_cache: list[dict] | None = None
_heatmap_cached_at: float = 0.0
_HEATMAP_CACHE_TTL_SECONDS = 600  # market-wide breadth doesn't need to be fresher than 10 min


def _map_industry_to_etf(industry: str | None) -> str | None:
    if not industry:
        return None
    low = industry.lower()
    for keyword, etf in _SECTOR_ETF_KEYWORDS:
        if keyword in low:
            return etf
    return None


async def _fetch_series(client: httpx.AsyncClient, yahoo_symbol: str) -> dict | None:
    resp = await client.get(
        YAHOO_CHART_URL.format(symbol=yahoo_symbol),
        params={"range": "1mo", "interval": "1d"},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    payload = resp.json()
    results = payload.get("chart", {}).get("result") or []
    if not results:
        return None
    r = results[0]
    closes = (r.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    closes = [c for c in closes if c is not None]
    if not closes:
        return None
    current = closes[-1]
    reference = closes[-6] if len(closes) >= 6 else closes[0]
    trend = "up" if current > reference * 1.01 else ("down" if current < reference * 0.99 else "flat")
    return {"value": current, "trend": trend}


async def _fetch_regime(client: httpx.AsyncClient, yahoo_symbol: str) -> dict | None:
    """Price vs its own 50-day and 200-day SMA -- the standard, unambiguous
    way to read whether an index/ETF is in a bull, bear, or neutral regime.
    Needs ~200 trading days of history, so this fetches a full year."""
    resp = await client.get(
        YAHOO_CHART_URL.format(symbol=yahoo_symbol),
        params={"range": "1y", "interval": "1d"},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    payload = resp.json()
    results = payload.get("chart", {}).get("result") or []
    if not results:
        return None
    r = results[0]
    closes = (r.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    closes = [c for c in closes if c is not None]
    if not closes:
        return None

    price = closes[-1]
    sma50 = indicators.sma(closes, 50)
    sma200 = indicators.sma(closes, 200)
    if sma50 is None:
        regime = "unknown"
    elif sma200 is None:
        regime = "bull" if price > sma50 else ("bear" if price < sma50 else "neutral")
    elif price > sma50 > sma200:
        regime = "bull"
    elif price < sma50 < sma200:
        regime = "bear"
    else:
        regime = "neutral"
    return {"price": price, "sma50": sma50, "sma200": sma200, "regime": regime}


async def fetch_macro() -> dict:
    global _cache, _cached_at
    if _cache is not None and time.time() - _cached_at < _CACHE_TTL_SECONDS:
        return _cache

    vix, tnx, irx, spx = None, None, None, None
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            vix = await _fetch_series(client, "^VIX")
        except Exception:
            log.warning("macro VIX fetch failed")
        try:
            tnx = await _fetch_series(client, "^TNX")
        except Exception:
            log.warning("macro TNX fetch failed")
        try:
            irx = await _fetch_series(client, "^IRX")
        except Exception:
            log.warning("macro IRX fetch failed")
        try:
            spx = await _fetch_regime(client, "^GSPC")
        except Exception:
            log.warning("macro S&P 500 regime fetch failed")

    tnx_yield = tnx["value"] if tnx else None
    irx_rate = irx["value"] if irx else None
    yield_curve_spread = (tnx_yield - irx_rate) if (tnx_yield is not None and irx_rate is not None) else None

    result = {
        "available": bool(vix or tnx or irx or spx),
        "vix": vix["value"] if vix else None,
        "vix_trend": vix["trend"] if vix else None,
        "tnx_yield": tnx_yield,
        "tnx_trend": tnx["trend"] if tnx else None,
        "irx_rate": irx_rate,
        "irx_trend": irx["trend"] if irx else None,
        "yield_curve_spread": yield_curve_spread,
        "spx_regime": spx["regime"] if spx else None,
        "spx_price": spx["price"] if spx else None,
        "spx_sma50": spx["sma50"] if spx else None,
        "spx_sma200": spx["sma200"] if spx else None,
    }

    _cache = result
    _cached_at = time.time()
    return result


async def fetch_sector_trend(industry: str | None) -> dict | None:
    """Sector-ETF trend regime for the given Finnhub industry string, or
    None if it doesn't map to a known sector (e.g. crypto) or the ETF fetch
    fails. Cached per-ETF for an hour, same as the rest of macro data."""
    etf = _map_industry_to_etf(industry)
    if not etf:
        return None

    cached = _sector_cache.get(etf)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            regime = await _fetch_regime(client, etf)
        except Exception:
            log.warning("macro sector ETF fetch failed for %s", etf)
            regime = None

    if regime:
        regime = {**regime, "etf": etf}
    _sector_cache[etf] = (time.time(), regime)
    return regime


async def _fetch_day_change(client: httpx.AsyncClient, etf: str) -> dict | None:
    resp = await client.get(
        YAHOO_CHART_URL.format(symbol=etf),
        params={"range": "5d", "interval": "1d"},
        headers=_HEADERS,
    )
    resp.raise_for_status()
    payload = resp.json()
    results = payload.get("chart", {}).get("result") or []
    if not results:
        return None
    r = results[0]
    closes = (r.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    closes = [c for c in closes if c is not None]
    if len(closes) < 2:
        return None
    current, prev = closes[-1], closes[-2]
    return {"price": current, "change_pct": (current - prev) / prev * 100 if prev else 0.0}


async def fetch_sector_heatmap() -> list[dict]:
    """Day % change for all 11 SPDR sector ETFs -- a market-wide "what's
    hot/cold today" breadth view. Cached for 10 minutes."""
    global _heatmap_cache, _heatmap_cached_at
    if _heatmap_cache is not None and time.time() - _heatmap_cached_at < _HEATMAP_CACHE_TTL_SECONDS:
        return _heatmap_cache

    etfs = list(SECTOR_ETF_NAMES)
    async with httpx.AsyncClient(timeout=10) as client:
        results = await asyncio.gather(*[_fetch_day_change(client, etf) for etf in etfs], return_exceptions=True)

    heatmap = []
    for etf, res in zip(etfs, results):
        if isinstance(res, Exception) or res is None:
            if isinstance(res, Exception):
                log.warning("macro sector heatmap fetch failed for %s", etf)
            heatmap.append({"etf": etf, "name": SECTOR_ETF_NAMES[etf], "price": None, "change_pct": None})
        else:
            heatmap.append({"etf": etf, "name": SECTOR_ETF_NAMES[etf], "price": res["price"], "change_pct": res["change_pct"]})

    _heatmap_cache = heatmap
    _heatmap_cached_at = time.time()
    return heatmap
