"""Technical indicator math used by the advisor: RSI, EMA, MACD, Bollinger
Bands, ATR. All take plain lists/candle-dicts (the same shape used
throughout the app) and return plain floats/lists -- no pandas dependency."""
import numpy as np


def ema_series(values: list[float], period: int) -> np.ndarray:
    """Full EMA series (not just the last value) -- needed so MACD can be
    computed from the difference of two EMA series."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return arr
    alpha = 2 / (period + 1)
    out = np.empty_like(arr)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def ema(values: list[float], period: int) -> float | None:
    if len(values) == 0:
        return None
    return float(ema_series(values, period)[-1])


def sma(values: list[float], period: int) -> float | None:
    """Simple moving average of the last `period` values. Used for regime
    checks (e.g. price/50d/200d) where a plain average, not an EMA's
    recency-weighted one, is the standard convention."""
    if len(values) < period:
        return None
    return float(np.mean(values[-period:]))


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's RSI. Returns None if there isn't enough data yet."""
    arr = np.asarray(closes, dtype=float)
    if len(arr) < period + 1:
        return None
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns {macd, signal, histogram} using the last value of each EMA
    series, or None fields if there isn't enough data."""
    if len(closes) < slow + signal:
        return {"macd": None, "signal": None, "histogram": None}
    fast_series = ema_series(closes, fast)
    slow_series = ema_series(closes, slow)
    macd_series = fast_series - slow_series
    signal_series = ema_series(macd_series.tolist(), signal)
    macd_val = float(macd_series[-1])
    signal_val = float(signal_series[-1])
    return {"macd": macd_val, "signal": signal_val, "histogram": macd_val - signal_val}


def bollinger(closes: list[float], period: int = 20, num_std: float = 2.0):
    """Returns {upper, middle, lower, percent_b} or all-None if insufficient data.
    percent_b: where price sits within the bands, 0 = lower band, 1 = upper band."""
    arr = np.asarray(closes, dtype=float)
    if len(arr) < period:
        return {"upper": None, "middle": None, "lower": None, "percent_b": None}
    window = arr[-period:]
    mid = float(np.mean(window))
    std = float(np.std(window))
    upper = mid + num_std * std
    lower = mid - num_std * std
    last = float(arr[-1])
    percent_b = (last - lower) / (upper - lower) if upper != lower else 0.5
    return {"upper": upper, "middle": mid, "lower": lower, "percent_b": percent_b}


def atr(candles: list[dict], period: int = 14) -> float | None:
    """Average True Range over the last `period` candles."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, prev_c = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    return float(np.mean(trs[-period:]))


def rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    """Same Wilder's RSI as rsi(), but returns a value for every bar (None
    during warm-up) instead of just the last one -- needed to compare RSI's
    swing highs/lows against price's swing highs/lows for divergence."""
    n = len(closes)
    out: list[float | None] = [None] * n
    if n < period + 1:
        return out
    arr = np.asarray(closes, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / max(avg_loss, 1e-12))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / max(avg_loss, 1e-12))
    return out


def stochastic(candles: list[dict], k_period: int = 14, d_period: int = 3) -> dict:
    """Fast %K / slow %D stochastic oscillator. Returns {k, d}, either None
    if there isn't enough data yet."""
    n = len(candles)
    if n < k_period + d_period:
        return {"k": None, "d": None}
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    k_values = []
    for i in range(k_period - 1, n):
        window_high = max(highs[i - k_period + 1: i + 1])
        window_low = min(lows[i - k_period + 1: i + 1])
        rng = window_high - window_low
        k = 100 * (closes[i] - window_low) / rng if rng else 50.0
        k_values.append(k)

    if len(k_values) < d_period:
        return {"k": float(k_values[-1]), "d": None}
    d = float(np.mean(k_values[-d_period:]))
    return {"k": float(k_values[-1]), "d": d}


def adx(candles: list[dict], period: int = 14) -> dict:
    """Wilder's Average Directional Index plus the latest +DI/-DI. ADX
    measures trend *strength* regardless of direction (below ~20 = choppy/
    range-bound, above ~25 = a real trend worth trusting); +DI vs -DI gives
    the direction. Returns None fields if there isn't enough data."""
    n = len(candles)
    if n < 2 * period + 1:
        return {"adx": None, "plus_di": None, "minus_di": None}

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = [0.0] * n
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

    smoothed_tr = sum(tr[1:period + 1])
    smoothed_plus = sum(plus_dm[1:period + 1])
    smoothed_minus = sum(minus_dm[1:period + 1])

    dx_values = []
    for i in range(period + 1, n):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr[i]
        smoothed_plus = smoothed_plus - (smoothed_plus / period) + plus_dm[i]
        smoothed_minus = smoothed_minus - (smoothed_minus / period) + minus_dm[i]
        plus_di = 100 * smoothed_plus / smoothed_tr if smoothed_tr else 0.0
        minus_di = 100 * smoothed_minus / smoothed_tr if smoothed_tr else 0.0
        denom = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / denom if denom else 0.0
        dx_values.append((dx, plus_di, minus_di))

    if len(dx_values) < period:
        return {"adx": None, "plus_di": None, "minus_di": None}

    adx_val = sum(d for d, _, _ in dx_values[:period]) / period
    for d, _, _ in dx_values[period:]:
        adx_val = (adx_val * (period - 1) + d) / period

    return {"adx": float(adx_val), "plus_di": float(dx_values[-1][1]), "minus_di": float(dx_values[-1][2])}


def obv_series(candles: list[dict]) -> list[float]:
    """On-Balance Volume: running total that adds a bar's volume on an up
    close and subtracts it on a down close. Its *slope* relative to price's
    slope is the signal -- rising OBV alongside rising price confirms the
    move is backed by real participation; a rising price with falling OBV
    means volume is quietly leaving, a classic early-warning divergence."""
    if not candles:
        return []
    out = [0.0]
    for i in range(1, len(candles)):
        prev_close = candles[i - 1]["close"]
        close = candles[i]["close"]
        vol = candles[i].get("volume") or 0
        if close > prev_close:
            out.append(out[-1] + vol)
        elif close < prev_close:
            out.append(out[-1] - vol)
        else:
            out.append(out[-1])
    return out


def vwap(candles: list[dict]) -> float | None:
    """Volume-weighted average price, anchored to the start of the supplied
    candle window (not calendar-session-aware -- callers should pass a
    window short enough that this stays meaningful, e.g. an intraday
    interval). None if there's no usable volume data."""
    if not candles:
        return None
    total_pv = 0.0
    total_v = 0.0
    for c in candles:
        typical = (c["high"] + c["low"] + c["close"]) / 3
        vol = c.get("volume") or 0
        total_pv += typical * vol
        total_v += vol
    if total_v <= 0:
        return None
    return total_pv / total_v
