import aiosqlite
from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price REAL NOT NULL,
    volume REAL,
    ts_ms INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_ts ON ticks(symbol, ts_ms);

CREATE TABLE IF NOT EXISTS candles (
    symbol TEXT NOT NULL,
    ts_sec INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (symbol, ts_sec)
);
CREATE INDEX IF NOT EXISTS idx_candles_symbol_ts ON candles(symbol, ts_sec);
"""

_conn: aiosqlite.Connection | None = None


async def init_db():
    global _conn
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _conn = await aiosqlite.connect(config.DB_PATH)
    await _conn.executescript(_SCHEMA)
    await _conn.commit()


async def close_db():
    if _conn:
        await _conn.close()


async def insert_tick(symbol: str, price: float, volume: float, ts_ms: int):
    await _conn.execute(
        "INSERT INTO ticks (symbol, price, volume, ts_ms) VALUES (?, ?, ?, ?)",
        (symbol, price, volume, ts_ms),
    )
    await _conn.commit()


async def upsert_candle(symbol: str, ts_sec: int, o: float, h: float, l: float, c: float, v: float):
    await _conn.execute(
        """
        INSERT INTO candles (symbol, ts_sec, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, ts_sec) DO UPDATE SET
            high=MAX(high, excluded.high),
            low=MIN(low, excluded.low),
            close=excluded.close,
            volume=excluded.volume
        """,
        (symbol, ts_sec, o, h, l, c, v),
    )
    await _conn.commit()


async def get_recent_candles(symbol: str, limit: int = 300):
    cursor = await _conn.execute(
        """
        SELECT ts_sec, open, high, low, close, volume FROM candles
        WHERE symbol = ?
        ORDER BY ts_sec DESC
        LIMIT ?
        """,
        (symbol, limit),
    )
    rows = await cursor.fetchall()
    rows.reverse()
    return [
        {"time": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
        for r in rows
    ]
