"""Company fundamentals, analyst sentiment, earnings schedule/surprises,
insider sentiment, and recent news tone -- all sourced from Finnhub.
(Yahoo's quoteSummary endpoint now requires crumb/cookie auth that isn't
worth fighting; Finnhub's free tier covers all of this with the key we
already have.)"""
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import config

log = logging.getLogger("fundamentals")

BASE_URL = "https://finnhub.io/api/v1"
_CACHE_TTL_SECONDS = 15 * 60  # fundamentals/context don't meaningfully change minute to minute
_cache: dict[str, tuple[float, dict]] = {}

_POSITIVE_WORDS = {
    "beat", "beats", "surge", "soar", "record", "upgrade", "growth", "profit",
    "gain", "rally", "strong", "outperform", "raise", "bullish", "win", "expand",
    "jump", "climb", "boost", "robust", "exceed", "exceeds", "top", "tops",
    "accelerate", "expansion", "buyback", "partnership", "launch", "launches",
    "innovation", "breakthrough", "upbeat", "soars", "surges", "rallies",
}
_NEGATIVE_WORDS = {
    "miss", "misses", "plunge", "slump", "downgrade", "loss", "cut", "cuts",
    "lawsuit", "sues", "sued", "probe", "investigation", "recall", "weak",
    "bearish", "fall", "falls", "decline", "warn", "warns", "layoff", "layoffs",
    "selloff", "sell-off", "crash", "tumble", "tumbles", "concern", "concerns",
    "risk", "risks", "delay", "delays", "fraud", "scandal", "resign", "resigns",
    "fine", "fined", "default", "bankruptcy", "plunges", "slumps", "tumbling",
}


async def _get(client: httpx.AsyncClient, path: str, params: dict):
    params = {**params, "token": config.FINNHUB_API_KEY}
    resp = await client.get(f"{BASE_URL}{path}", params=params)
    resp.raise_for_status()
    return resp.json()


def _news_tone(news_items: list[dict]) -> float:
    """Keyword-based tone over recent headlines, -1..+1. Headlines from the
    last 48h are weighted 2x (fresh news moves price more than week-old
    coverage), near-duplicate headlines collapse to one so a single wire
    story reprinted by five outlets doesn't get counted five times, and
    each headline's contribution is capped so one outlier can't dominate."""
    if not news_items:
        return 0.0
    now = time.time()
    seen = set()
    total = 0.0
    weight_sum = 0.0
    for item in news_items:
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue
        key = headline.lower()[:50]
        if key in seen:
            continue
        seen.add(key)
        low = headline.lower()
        raw = sum(1 for w in _POSITIVE_WORDS if w in low) - sum(1 for w in _NEGATIVE_WORDS if w in low)
        raw = max(-3, min(3, raw))
        ts = item.get("datetime") or 0
        age_hours = (now - ts) / 3600 if ts else 999
        weight = 2.0 if age_hours <= 48 else 1.0
        total += raw * weight
        weight_sum += weight
    if weight_sum == 0:
        return 0.0
    return max(-1.0, min(1.0, total / weight_sum / 2))


async def _fetch_earnings_surprises(client: httpx.AsyncClient, symbol: str) -> dict | None:
    """Last 4 reported quarters' EPS actual-vs-estimate. Consistent beats
    are one of the more reliable "is this company executing" signals --
    much more concrete than sentiment-scored news."""
    try:
        data = await _get(client, "/stock/earnings", {"symbol": symbol})
    except Exception:
        log.warning("fundamentals earnings-surprise fetch failed for %s", symbol)
        return None
    if not data:
        return None
    surprises = []
    for e in data[:4]:
        pct = e.get("surprisePercent")
        if pct is None and e.get("estimate") not in (None, 0) and e.get("actual") is not None:
            pct = (e["actual"] - e["estimate"]) / abs(e["estimate"]) * 100
        if pct is not None:
            surprises.append(pct)
    if not surprises:
        return None
    beats = sum(1 for s in surprises if s > 0)
    return {"beats": beats, "total": len(surprises), "avg_surprise_pct": sum(surprises) / len(surprises)}


async def _fetch_insider_sentiment(client: httpx.AsyncClient, symbol: str) -> float | None:
    """Average Monthly Share Purchase Ratio (MSPR) over the last 3 reported
    months. Positive = insiders net buying their own stock, negative = net
    selling -- people with the best information about the business putting
    their own money where their knowledge is."""
    try:
        today = datetime.now(timezone.utc).date()
        frm = (today - timedelta(days=100)).isoformat()
        data = await _get(client, "/stock/insider-sentiment", {"symbol": symbol, "from": frm, "to": today.isoformat()})
    except Exception:
        log.warning("fundamentals insider-sentiment fetch failed for %s", symbol)
        return None
    rows = data.get("data") or []
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: (r.get("year", 0), r.get("month", 0)))[-3:]
    msprs = [r["mspr"] for r in rows if r.get("mspr") is not None]
    if not msprs:
        return None
    return sum(msprs) / len(msprs)


async def fetch_context(symbol: str) -> dict:
    """Fundamentals + street/context data for the advisor. Any individual
    piece that fails is simply set to None (never raises) so the advisor
    can still run with partial data."""
    if not config.FINNHUB_API_KEY:
        return {"available": False, "reason": "No Finnhub API key configured."}

    cached = _cache.get(symbol)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    result: dict = {"available": True}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            data = await _get(client, "/stock/metric", {"symbol": symbol, "metric": "all"})
            m = data.get("metric") or {}
            result["metrics"] = {
                "pe_ttm": m.get("peTTM"),
                "forward_pe": m.get("forwardPE"),
                "ps_ttm": m.get("psTTM"),
                "price_to_book": m.get("pbQuarterly"),
                "revenue_growth_ttm_yoy": m.get("revenueGrowthTTMYoy"),
                "revenue_growth_3y": m.get("revenueGrowth3Y"),
                "eps_growth_ttm_yoy": m.get("epsGrowthTTMYoy"),
                "eps_growth_3y": m.get("epsGrowth3Y"),
                "net_margin_ttm": m.get("netProfitMarginTTM"),
                "gross_margin_ttm": m.get("grossMarginTTM"),
                "operating_margin_ttm": m.get("operatingMarginTTM"),
                "roe_ttm": m.get("roeTTM"),
                "roa_ttm": m.get("roaTTM"),
                "current_ratio": m.get("currentRatioQuarterly"),
                "quick_ratio": m.get("quickRatioQuarterly"),
                "debt_to_equity": m.get("totalDebt/totalEquityQuarterly"),
                "payout_ratio_ttm": m.get("payoutRatioTTM"),
                "dividend_yield": m.get("dividendYieldIndicatedAnnual"),
                "beta": m.get("beta"),
                "week52_high": m.get("52WeekHigh"),
                "week52_low": m.get("52WeekLow"),
            }
        except Exception:
            log.warning("fundamentals metrics fetch failed for %s", symbol)
            result["metrics"] = None

        try:
            profile = await _get(client, "/stock/profile2", {"symbol": symbol})
            result["profile"] = {
                "name": profile.get("name"),
                "industry": profile.get("finnhubIndustry"),
                "market_cap": profile.get("marketCapitalization"),
            } if profile else None
        except Exception:
            log.warning("fundamentals profile fetch failed for %s", symbol)
            result["profile"] = None

        try:
            recs = await _get(client, "/stock/recommendation", {"symbol": symbol})
            result["analyst"] = recs[0] if recs else None
        except Exception:
            log.warning("fundamentals recommendation fetch failed for %s", symbol)
            result["analyst"] = None

        try:
            today = datetime.now(timezone.utc).date()
            frm = (today - timedelta(days=120)).isoformat()
            to = (today + timedelta(days=120)).isoformat()
            cal = await _get(client, "/calendar/earnings", {"symbol": symbol, "from": frm, "to": to})
            events = sorted(cal.get("earningsCalendar") or [], key=lambda e: e["date"])
            next_event = next((e for e in events if e["date"] >= today.isoformat()), None)
            result["next_earnings_date"] = next_event["date"] if next_event else None
        except Exception:
            log.warning("fundamentals earnings calendar fetch failed for %s", symbol)
            result["next_earnings_date"] = None

        result["earnings_surprises"] = await _fetch_earnings_surprises(client, symbol)
        result["insider_mspr"] = await _fetch_insider_sentiment(client, symbol)

        try:
            today = datetime.now(timezone.utc).date()
            frm = (today - timedelta(days=10)).isoformat()
            news = await _get(client, "/company-news", {"symbol": symbol, "from": frm, "to": today.isoformat()})
            news_items = news[:30]
            result["news_tone"] = _news_tone(news_items)
            result["news_count"] = len(news_items)
        except Exception:
            log.warning("fundamentals news fetch failed for %s", symbol)
            result["news_tone"] = None
            result["news_count"] = 0

    _cache[symbol] = (time.time(), result)
    return result
