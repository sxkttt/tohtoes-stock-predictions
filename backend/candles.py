"""Aggregates raw trade ticks into 1-second OHLC candles, per symbol."""
from collections import deque
from . import config


class SymbolState:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.candles: deque = deque(maxlen=config.CANDLE_HISTORY_LEN)  # finalized candles
        self.current: dict | None = None  # in-progress candle
        self.finalized_count = 0

    def _new_candle(self, ts_sec: int, price: float, volume: float) -> dict:
        return {
            "time": ts_sec,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
        }

    def add_tick(self, price: float, volume: float, ts_ms: int):
        """Returns (current_candle, finalized_candle_or_None)."""
        ts_sec = ts_ms // 1000
        finalized = None

        if self.current is None:
            self.current = self._new_candle(ts_sec, price, volume)
        elif ts_sec == self.current["time"]:
            c = self.current
            c["high"] = max(c["high"], price)
            c["low"] = min(c["low"], price)
            c["close"] = price
            c["volume"] += volume
        else:
            # a new second has started -> finalize the previous candle
            finalized = self.current
            self.candles.append(finalized)
            self.finalized_count += 1
            self.current = self._new_candle(ts_sec, price, volume)

        return self.current, finalized

    def history(self):
        hist = list(self.candles)
        if self.current is not None:
            hist = hist + [self.current]
        return hist


class CandleStore:
    def __init__(self):
        self._states: dict[str, SymbolState] = {}

    def get(self, symbol: str) -> SymbolState:
        if symbol not in self._states:
            self._states[symbol] = SymbolState(symbol)
        return self._states[symbol]


store = CandleStore()
