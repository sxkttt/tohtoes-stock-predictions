import time

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

-- One row per /api/advisor call. outcome_price/outcome_hit are filled in
-- later by the accuracy-backtracking job once the horizon window elapses.
CREATE TABLE IF NOT EXISTS advisor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts INTEGER NOT NULL,
    horizon TEXT NOT NULL,
    verdict TEXT NOT NULL,
    score REAL NOT NULL,
    confidence REAL NOT NULL,
    price REAL NOT NULL,
    outcome_price REAL,
    outcome_hit INTEGER
);
CREATE INDEX IF NOT EXISTS idx_advisor_runs_symbol_ts ON advisor_runs(symbol, ts);
CREATE INDEX IF NOT EXISTS idx_advisor_runs_unscored ON advisor_runs(outcome_hit) WHERE outcome_hit IS NULL;

CREATE TABLE IF NOT EXISTS watchlist (
    symbol TEXT PRIMARY KEY,
    added_ts INTEGER NOT NULL
);

-- kind: price_above | price_below | pattern | verdict_change | earnings_reminder
-- params_json holds kind-specific fields (e.g. {"price": 150} for price_above).
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    kind TEXT NOT NULL,
    params_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_ts INTEGER NOT NULL,
    last_fired_ts INTEGER
);

CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    message TEXT NOT NULL,
    ts INTEGER NOT NULL,
    seen INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alert_events_seen ON alert_events(seen);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    price REAL NOT NULL,
    ts INTEGER NOT NULL,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);

-- UI preferences (theme, drawings, indicator panes, ...). These live in the
-- browser's localStorage for instant synchronous reads at boot, but
-- localStorage is scoped per origin and the origin includes the port -- so
-- they are mirrored here to survive a port change.
CREATE TABLE IF NOT EXISTS prefs (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_ts INTEGER NOT NULL
);
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


# --- advisor run history / accuracy tracking --------------------------------

async def insert_advisor_run(symbol: str, horizon: str, verdict: str, score: float,
                              confidence: float, price: float) -> int:
    cursor = await _conn.execute(
        "INSERT INTO advisor_runs (symbol, ts, horizon, verdict, score, confidence, price) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (symbol, int(time.time()), horizon, verdict, score, confidence, price),
    )
    await _conn.commit()
    return cursor.lastrowid


async def get_advisor_history(symbol: str, limit: int = 30) -> list[dict]:
    cursor = await _conn.execute(
        "SELECT ts, horizon, verdict, score, confidence, price FROM advisor_runs "
        "WHERE symbol = ? ORDER BY ts DESC LIMIT ?",
        (symbol, limit),
    )
    rows = await cursor.fetchall()
    rows.reverse()
    return [
        {"ts": r[0], "horizon": r[1], "verdict": r[2], "score": r[3], "confidence": r[4], "price": r[5]}
        for r in rows
    ]


async def get_unscored_runs_before(cutoff_ts: int) -> list[dict]:
    """Runs old enough for their horizon window to have elapsed, that
    haven't been scored against an outcome yet."""
    cursor = await _conn.execute(
        "SELECT id, symbol, ts, horizon, verdict, score, price FROM advisor_runs "
        "WHERE outcome_hit IS NULL AND ts <= ?",
        (cutoff_ts,),
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "symbol": r[1], "ts": r[2], "horizon": r[3], "verdict": r[4], "score": r[5], "price": r[6]}
        for r in rows
    ]


async def set_run_outcome(run_id: int, outcome_price: float, outcome_hit: bool):
    await _conn.execute(
        "UPDATE advisor_runs SET outcome_price = ?, outcome_hit = ? WHERE id = ?",
        (outcome_price, int(outcome_hit), run_id),
    )
    await _conn.commit()


async def get_accuracy_stats() -> list[dict]:
    """Hit rate grouped by horizon, scored runs only."""
    cursor = await _conn.execute(
        "SELECT horizon, COUNT(*), SUM(outcome_hit) FROM advisor_runs "
        "WHERE outcome_hit IS NOT NULL GROUP BY horizon"
    )
    rows = await cursor.fetchall()
    return [
        {"horizon": r[0], "total": r[1], "hits": r[2] or 0,
         "hit_rate": (r[2] or 0) / r[1] if r[1] else 0.0}
        for r in rows
    ]


# --- watchlist ----------------------------------------------------------------

async def add_watchlist(symbol: str):
    await _conn.execute(
        "INSERT OR IGNORE INTO watchlist (symbol, added_ts) VALUES (?, ?)",
        (symbol, int(time.time())),
    )
    await _conn.commit()


async def remove_watchlist(symbol: str):
    await _conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    await _conn.commit()


async def get_watchlist() -> list[dict]:
    cursor = await _conn.execute("SELECT symbol, added_ts FROM watchlist ORDER BY added_ts ASC")
    rows = await cursor.fetchall()
    return [{"symbol": r[0], "added_ts": r[1]} for r in rows]


# --- alerts ---------------------------------------------------------------------

async def create_alert(symbol: str, kind: str, params_json: str) -> int:
    cursor = await _conn.execute(
        "INSERT INTO alerts (symbol, kind, params_json, active, created_ts) VALUES (?, ?, ?, 1, ?)",
        (symbol, kind, params_json, int(time.time())),
    )
    await _conn.commit()
    return cursor.lastrowid


async def get_alerts(symbol: str | None = None) -> list[dict]:
    if symbol:
        cursor = await _conn.execute(
            "SELECT id, symbol, kind, params_json, active, created_ts, last_fired_ts FROM alerts "
            "WHERE symbol = ? ORDER BY created_ts DESC",
            (symbol,),
        )
    else:
        cursor = await _conn.execute(
            "SELECT id, symbol, kind, params_json, active, created_ts, last_fired_ts FROM alerts "
            "ORDER BY created_ts DESC"
        )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "symbol": r[1], "kind": r[2], "params_json": r[3],
         "active": bool(r[4]), "created_ts": r[5], "last_fired_ts": r[6]}
        for r in rows
    ]


async def get_active_alerts() -> list[dict]:
    cursor = await _conn.execute(
        "SELECT id, symbol, kind, params_json, last_fired_ts FROM alerts WHERE active = 1"
    )
    rows = await cursor.fetchall()
    return [{"id": r[0], "symbol": r[1], "kind": r[2], "params_json": r[3], "last_fired_ts": r[4]} for r in rows]


async def delete_alert(alert_id: int):
    await _conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    await _conn.commit()


async def mark_alert_fired(alert_id: int):
    await _conn.execute(
        "UPDATE alerts SET last_fired_ts = ? WHERE id = ?", (int(time.time()), alert_id)
    )
    await _conn.commit()


async def create_alert_event(alert_id: int, symbol: str, message: str) -> int:
    cursor = await _conn.execute(
        "INSERT INTO alert_events (alert_id, symbol, message, ts, seen) VALUES (?, ?, ?, ?, 0)",
        (alert_id, symbol, message, int(time.time())),
    )
    await _conn.commit()
    return cursor.lastrowid


async def get_pending_alert_events() -> list[dict]:
    cursor = await _conn.execute(
        "SELECT id, alert_id, symbol, message, ts FROM alert_events WHERE seen = 0 ORDER BY ts ASC"
    )
    rows = await cursor.fetchall()
    return [{"id": r[0], "alert_id": r[1], "symbol": r[2], "message": r[3], "ts": r[4]} for r in rows]


async def mark_alert_events_seen(event_ids: list[int]):
    if not event_ids:
        return
    placeholders = ",".join("?" for _ in event_ids)
    await _conn.execute(f"UPDATE alert_events SET seen = 1 WHERE id IN ({placeholders})", event_ids)
    await _conn.commit()


# --- paper trading ----------------------------------------------------------------

async def add_paper_trade(symbol: str, side: str, qty: float, price: float, note: str = "") -> int:
    cursor = await _conn.execute(
        "INSERT INTO paper_trades (symbol, side, qty, price, ts, note) VALUES (?, ?, ?, ?, ?, ?)",
        (symbol, side, qty, price, int(time.time()), note),
    )
    await _conn.commit()
    return cursor.lastrowid


async def get_paper_trades(symbol: str | None = None) -> list[dict]:
    if symbol:
        cursor = await _conn.execute(
            "SELECT id, symbol, side, qty, price, ts, note FROM paper_trades WHERE symbol = ? ORDER BY ts ASC",
            (symbol,),
        )
    else:
        cursor = await _conn.execute(
            "SELECT id, symbol, side, qty, price, ts, note FROM paper_trades ORDER BY ts ASC"
        )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "symbol": r[1], "side": r[2], "qty": r[3], "price": r[4], "ts": r[5], "note": r[6]}
        for r in rows
    ]


async def delete_paper_trade(trade_id: int):
    await _conn.execute("DELETE FROM paper_trades WHERE id = ?", (trade_id,))
    await _conn.commit()


async def get_prefs() -> dict[str, str]:
    cursor = await _conn.execute("SELECT key, value FROM prefs")
    rows = await cursor.fetchall()
    return {r[0]: r[1] for r in rows}


async def set_prefs(values: dict[str, str]):
    """Upsert a batch of preferences. Values are opaque strings -- the
    frontend stores exactly what it would have put in localStorage."""
    if not values:
        return
    now = int(time.time())
    await _conn.executemany(
        "INSERT INTO prefs (key, value, updated_ts) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_ts = excluded.updated_ts",
        [(k, v, now) for k, v in values.items()],
    )
    await _conn.commit()
