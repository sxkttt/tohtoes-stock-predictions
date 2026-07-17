"""Per-symbol news feed with a rule-based "likely effect" tag on each
headline. Reuses the same Finnhub /company-news data that fundamentals.py
already pulls for its aggregate news-tone score, but surfaces the actual
articles and classifies each one individually instead of collapsing
everything into a single number.

Classification is a keyword heuristic over well-known news categories
(earnings, analyst actions, guidance, M&A, legal/regulatory, buybacks,
executive changes) with a generic polarity-word fallback for anything
that doesn't match a category. This is pattern-matching, not a forecast --
same "informational purposes only" spirit as advisor.py, and every note
below is phrased as a tendency, not a promise."""
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import config
from .fundamentals import _NEGATIVE_WORDS, _POSITIVE_WORDS

log = logging.getLogger("news")

BASE_URL = "https://finnhub.io/api/v1"
_CACHE_TTL_SECONDS = 10 * 60
_cache: dict[str, tuple[float, dict]] = {}
_LOOKBACK_DAYS = 14
_MAX_ARTICLES = 25

# Ordered (first match wins) so more specific categories are checked before
# generic ones -- e.g. "cuts guidance" should win over the bare "cuts".
_CATEGORIES = [
    ("earnings_beat", ["beats estimates", "beat estimates", "tops estimates", "beat expectations",
                        "earnings beat", "beats profit"], "bullish",
     "Earnings beats often trigger a short-term pop, though the size of the reaction usually "
     "depends more on forward guidance than the beat itself."),
    ("earnings_miss", ["misses estimates", "miss estimates", "falls short", "earnings miss",
                        "misses profit"], "bearish",
     "Earnings misses tend to pressure the stock near-term, more so when paired with weak guidance."),
    ("guidance_cut", ["cuts guidance", "lowers guidance", "cuts forecast", "lowers forecast",
                       "cuts outlook", "lowers outlook", "guidance cut"], "bearish",
     "Guidance cuts are one of the more reliable bearish signals -- they reflect management's own "
     "view of the business, not just backward-looking results."),
    ("guidance_raise", ["raises guidance", "raises forecast", "raises outlook", "boosts guidance",
                         "guidance raise", "lifts outlook"], "bullish",
     "Raised guidance tends to be read bullishly since it's management signaling confidence in "
     "future results, not just a past quarter."),
    ("downgrade", ["downgrades", "downgraded", "cuts price target", "lowers price target",
                    "initiates.*sell", "initiates.*underperform"], "bearish",
     "Analyst downgrades and price-target cuts can pressure a stock, though the market has often "
     "partly priced in the same information already."),
    ("upgrade", ["upgrades", "upgraded", "raises price target", "lifts price target",
                 "initiates.*buy", "initiates.*outperform"], "bullish",
     "Analyst upgrades and price-target raises tend to support the stock short-term, especially "
     "from widely-followed firms."),
    ("merger_acquisition", ["to acquire", "acquisition of", "merger", "to buy ", "buyout",
                             "takeover", "acquires "], "neutral",
     "M&A news often moves the stock sharply in either direction -- the target usually jumps toward "
     "the deal price, while the acquirer's reaction depends on the price paid and financing."),
    ("regulatory_legal", ["lawsuit", "sues ", "sued", "probe", "investigation", "recall",
                           "sec charges", "antitrust", "fined", "settlement"], "bearish",
     "Legal and regulatory headlines typically weigh on sentiment, with the real impact depending "
     "on the financial exposure once details emerge."),
    ("buyback_dividend", ["share buyback", "share repurchase", "raises dividend", "special dividend",
                           "increases dividend", "authorizes buyback"], "bullish",
     "Buybacks and dividend increases are usually read as management signaling confidence and "
     "returning capital to shareholders."),
    ("executive_change", ["ceo resigns", "ceo steps down", "names new ceo", "appoints new ceo",
                           "cfo resigns", "executive departure"], "neutral",
     "Leadership changes create near-term uncertainty; the market's reaction depends heavily on "
     "the circumstances and the successor's track record."),
]


async def _get(client: httpx.AsyncClient, path: str, params: dict):
    params = {**params, "token": config.FINNHUB_API_KEY}
    resp = await client.get(f"{BASE_URL}{path}", params=params)
    resp.raise_for_status()
    return resp.json()


def _classify(headline: str, summary: str) -> tuple[str, str, str, str]:
    """Returns (category, category_label, direction, note)."""
    text = f"{headline} {summary}".lower()
    for category, keywords, direction, note in _CATEGORIES:
        for kw in keywords:
            matched = re.search(kw, text) if ".*" in kw else kw in text
            if matched:
                return category, category.replace("_", " ").title(), direction, note

    pos = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text)
    if pos > neg:
        return "general_positive", "General", "bullish", \
            "Positively-toned coverage; no specific catalyst category matched, so treat this as a mild signal."
    if neg > pos:
        return "general_negative", "General", "bearish", \
            "Negatively-toned coverage; no specific catalyst category matched, so treat this as a mild signal."
    return "general", "General", "neutral", \
        "No strong directional language detected in this headline."


async def fetch_news(symbol: str) -> dict:
    if not config.FINNHUB_API_KEY:
        return {"available": False, "reason": "No Finnhub API key configured.", "articles": []}

    cached = _cache.get(symbol)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    today = datetime.now(timezone.utc).date()
    frm = (today - timedelta(days=_LOOKBACK_DAYS)).isoformat()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            raw = await _get(client, "/company-news", {"symbol": symbol, "from": frm, "to": today.isoformat()})
    except Exception:
        log.warning("news fetch failed for %s", symbol)
        result = {"available": False, "reason": "News unavailable right now.", "articles": []}
        _cache[symbol] = (time.time(), result)
        return result

    seen = set()
    articles = []
    for item in sorted(raw, key=lambda x: x.get("datetime") or 0, reverse=True):
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue
        key = headline.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        summary = (item.get("summary") or "").strip()
        category, category_label, direction, note = _classify(headline, summary)
        articles.append({
            "headline": headline,
            "summary": summary[:220],
            "source": item.get("source"),
            "url": item.get("url"),
            "datetime": item.get("datetime"),
            "category": category,
            "category_label": category_label,
            "direction": direction,
            "note": note,
        })
        if len(articles) >= _MAX_ARTICLES:
            break

    result = {"available": True, "articles": articles}
    _cache[symbol] = (time.time(), result)
    return result
