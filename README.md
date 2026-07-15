# Tohtoe's Stock Predictions — Real-Time Stock Pattern Viewer

Native desktop app (and web app) for live candlestick charts of any NASDAQ
or NYSE stock, with automatic trend-line / support-resistance detection and
a 30-pattern candlestick recognition engine (each with a low/medium/high
confidence score), backed by a constantly-updating SQLite database of every
trade tick and 1-second candle.

This is a separate, independently-built edition of the PulseChart app —
same engine, its own branding, its own project folder, its own exe.

## How it works

- **Data feed**: connects to [Finnhub](https://finnhub.io)'s free real-time
  trade websocket (second-level precision, US stocks + crypto like
  `BINANCE:BTCUSDT`).
- **Historical fallback**: when live data isn't flowing (market closed, or
  you pick a longer timeframe), the app automatically pulls real OHLC
  history from Yahoo Finance — no key required. Timeframe buttons: Live,
  1D, 1W, 1M, 3M, 1Y, 5Y.
- **Symbol search**: type a ticker or company name and get autocomplete
  suggestions across all ~5,000 NASDAQ + NYSE common stocks/ADRs (backed by
  Finnhub's exchange listing, cached locally).
- **Pattern engine** (`backend/patterns.py`): detects 30 candlestick
  patterns — single-candle (Doji variants, Marubozu, Hammer/Hanging Man,
  Inverted Hammer/Shooting Star, Spinning Top), two-candle (Engulfing,
  Harami, Piercing Line/Dark Cloud Cover, Tweezer, Kicker), and three-candle
  (Morning/Evening Star, Three Soldiers/Crows, Three Inside/Outside,
  Abandoned Baby) — plus swing-based trend lines and support/resistance.
  Each detection carries a low/medium/high confidence score, filterable in
  the UI.
- **Animated start screen**: Live Markets / Search Stocks / Recent / About
  menu with a particle background, before entering the chart dashboard.
- **Backend** (`backend/`): FastAPI app that ingests trades, aggregates them
  into 1-second OHLC candles in memory, persists ticks + candles to SQLite
  (`data/market.db`), runs pattern analysis, and streams updates over a
  WebSocket.
- **Desktop shell** (`desktop_app.py`): runs the backend in-process and
  displays it in a native PySide6 window — no browser, no console. Packaged
  as a standalone `TohtoeStockPredictions.exe` via PyInstaller (`tohtoe.spec`).

## Setup (running from source)

1. Get a **free** Finnhub API key: https://finnhub.io/register
2. Copy `.env.example` to `.env` and paste your key in.
3. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Run as a desktop app:
   ```
   python desktop_app.py
   ```
   ...or as a web app:
   ```
   uvicorn backend.main:app --reload --port 8000
   ```
   then open http://localhost:8000.

## Building the exe

```
pip install -r requirements-build.txt
pyinstaller tohtoe.spec --noconfirm
```
Produces `dist\TohtoeStockPredictions.exe`. Put your `.env` (with your
Finnhub key) next to the exe — it's portable, along with `data\` (SQLite
db) and `logs\tohtoe.log` (diagnostics), all written beside wherever the
exe lives rather than baked into the bundle.

## Notes

- Finnhub's free tier streams real US-exchange trades as they happen
  (second precision) for common stocks, plus crypto pairs — no delay,
  no paid plan required. Markets only send trades during open hours;
  crypto symbols (`BINANCE:...`) tick 24/7.
- All ticks and candles are stored in `data/market.db` (SQLite) so
  history persists across restarts and reloads instantly on reconnect.
- The NASDAQ/NYSE symbol directory refreshes from Finnhub weekly and is
  cached to `data/us_symbols_cache.json`; search still works instantly on
  cold start from that cache.
- Pattern detection re-runs on every new candle, so trend lines,
  support/resistance levels, and candlestick markers all update live.
