"""Shared fixtures and candle builders for the test suite.

Everything here is deterministic and offline -- no network, no API key, no
database. The modules under test all take plain lists of candle dicts, so the
builders below are enough to exercise them fully.
"""
import math
import sys
from pathlib import Path

import pytest

# The app is imported as `backend.*`, so the project root must be importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def candle(o, h, l, c, v=1_000_000, ts=0):
    """Build a candle in the shape the whole app uses."""
    return {"time": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}


def make_candles(closes, spread=0.5, volume=1_000_000):
    """Turn a list of closes into candles with a small symmetric range.

    open follows the previous close so the series has no artificial gaps,
    which would otherwise trip the gap-sensitive pattern detectors.
    """
    out = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i else c
        out.append(candle(
            o=o,
            h=max(o, c) + spread,
            l=min(o, c) - spread,
            c=c,
            v=volume,
            ts=i * 86_400,
        ))
    return out


@pytest.fixture
def rising_candles():
    """A clean uptrend: 120 bars climbing steadily."""
    return make_candles([100 + i * 0.5 for i in range(120)])


@pytest.fixture
def falling_candles():
    """A clean downtrend: 120 bars declining steadily."""
    return make_candles([160 - i * 0.5 for i in range(120)])


@pytest.fixture
def choppy_candles():
    """Sideways oscillation -- no trend, for regime/ADX checks."""
    return make_candles([100 + 3 * math.sin(i / 3) for i in range(120)])


@pytest.fixture
def flat_candles():
    """Perfectly flat prices -- the degenerate case that makes naive
    indicator math divide by zero."""
    return make_candles([100.0] * 120, spread=0.0)
