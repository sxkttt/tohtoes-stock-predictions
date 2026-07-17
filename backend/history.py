"""Historical OHLC candles from Yahoo Finance's public chart endpoint.

Used as a fallback for anything beyond the live in-memory/DB tick stream:
longer timeframes (1M/3M/1Y/5Y) and any view of the chart while the market
is closed and no live ticks are coming in. No API key required.
"""
import httpx

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0"}

# period label -> (Yahoo range, Yahoo interval)
RANGE_INTERVAL_PRESETS = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "15m"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "1Y": ("1y", "1wk"),
    "5Y": ("5y", "1wk"),
}

# advisor candle-interval label -> (Yahoo range, Yahoo interval)
# range is chosen to give enough bars for a 14/20/26-period indicator warm-up
# without asking Yahoo for more history than that interval actually retains.
ADVISOR_INTERVALS = {
    "5m": ("5d", "5m"),
    "15m": ("1mo", "15m"),
    "1h": ("3mo", "1h"),
    "1d": ("1y", "1d"),
    "1wk": ("5y", "1wk"),
}

# Which candle intervals Yahoo will actually serve for each display period's
# range, based on its documented intraday history limits: 1m data only goes
# back ~7 days, 5m/15m/30m only ~60 days, 60m/1h only ~730 days, and
# 1d/1wk are unlimited. A period's own default interval (RANGE_INTERVAL_PRESETS)
# is always included even if it wouldn't otherwise fit the pattern below.
INTERVAL_COMPAT = {
    "1D": ["1m", "5m", "15m", "30m", "1h", "1d"],
    "1W": ["1m", "5m", "15m", "30m", "1h", "1d"],
    "1M": ["5m", "15m", "30m", "1h", "1d"],
    "3M": ["1h", "1d"],
    "1Y": ["1h", "1d", "1wk"],
    "5Y": ["1d", "1wk"],
}


def to_yahoo_symbol(symbol: str) -> str:
    """Finnhub uses e.g. BINANCE:BTCUSDT for crypto; Yahoo uses BTC-USD."""
    upper = symbol.upper()
    if upper.startswith("BINANCE:") and upper.endswith("USDT"):
        base = upper.split(":", 1)[1][:-4]
        return f"{base}-USD"
    return symbol


async def _fetch(symbol: str, rng: str, interval: str, include_prepost: bool = False) -> list[dict]:
    yahoo_symbol = to_yahoo_symbol(symbol)

    url = YAHOO_CHART_URL.format(symbol=yahoo_symbol)
    params = {"range": rng, "interval": interval}
    if include_prepost:
        params["includePrePost"] = "true"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=_HEADERS)
        resp.raise_for_status()
        payload = resp.json()

    results = payload.get("chart", {}).get("result") or []
    if not results:
        return []

    r = results[0]
    timestamps = r.get("timestamp") or []
    quote_list = r.get("indicators", {}).get("quote") or []
    if not quote_list:
        return []
    quote = quote_list[0]
    opens, highs, lows, closes, volumes = (
        quote.get("open", []), quote.get("high", []),
        quote.get("low", []), quote.get("close", []), quote.get("volume", []),
    )

    candles = []
    for i, ts in enumerate(timestamps):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        if o is None or h is None or l is None or c is None:
            continue
        v = volumes[i] if i < len(volumes) and volumes[i] is not None else 0
        candles.append({"time": int(ts), "open": o, "high": h, "low": l, "close": c, "volume": v})
    return candles


async def fetch_candles(symbol: str, period: str, include_prepost: bool = False) -> list[dict]:
    if period not in RANGE_INTERVAL_PRESETS:
        raise ValueError(f"unknown period: {period}")
    rng, interval = RANGE_INTERVAL_PRESETS[period]
    return await _fetch(symbol, rng, interval, include_prepost)


async def fetch_candles_custom(
    symbol: str, period: str, interval: str, include_prepost: bool = False
) -> tuple[list[dict], str]:
    """Same range as the given display period, but with a user-chosen candle
    interval instead of that period's default -- lets the main chart show
    e.g. hourly candles over a 3-month window instead of only daily.

    Silently clamps to the period's default interval if the requested one
    isn't compatible with that range (Yahoo would just error otherwise).
    Returns (candles, interval_actually_used).
    """
    if period not in RANGE_INTERVAL_PRESETS:
        raise ValueError(f"unknown period: {period}")
    rng, default_interval = RANGE_INTERVAL_PRESETS[period]
    allowed = INTERVAL_COMPAT.get(period, [default_interval])
    if interval not in allowed:
        interval = default_interval
    candles = await _fetch(symbol, rng, interval, include_prepost)
    return candles, interval


async def fetch_candles_interval(symbol: str, interval_key: str) -> list[dict]:
    """Used by the advisor: candles at a specific technical-analysis interval
    (5m/15m/1h/1d/1wk) rather than one of the chart's display periods."""
    if interval_key not in ADVISOR_INTERVALS:
        raise ValueError(f"unknown advisor interval: {interval_key}")
    rng, interval = ADVISOR_INTERVALS[interval_key]
    return await _fetch(symbol, rng, interval)
