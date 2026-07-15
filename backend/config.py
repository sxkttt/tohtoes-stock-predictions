import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    # Running as a PyInstaller build: keep user data (.env, database) writable,
    # sitting next to the app, while read-only bundled assets live in _MEIPASS.
    exe_path = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        # A --windowed build on macOS is a Foo.app/Contents/MacOS/Foo bundle;
        # sys.executable points *inside* it. Writing user data inside a
        # signed bundle is bad practice (not user-visible, can be wiped on
        # update), so walk up to whatever contains the .app instead --
        # matching the "everything sits next to the app" convention used
        # on Windows.
        app_bundle = next((p for p in exe_path.parents if p.suffix == ".app"), None)
        ROOT_DIR = app_bundle.parent if app_bundle else exe_path.parent
    else:
        ROOT_DIR = exe_path.parent
    FRONTEND_DIR = Path(sys._MEIPASS) / "frontend"
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    FRONTEND_DIR = ROOT_DIR / "frontend"

ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_WS_URL = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"
DB_PATH = ROOT_DIR / "data" / "market.db"

# how many finalized candles to keep in memory / analyze for patterns
CANDLE_HISTORY_LEN = 300
# recompute pattern analysis every N finalized candles
PATTERN_RECOMPUTE_EVERY = 1


def set_api_key(new_key: str):
    """Update the in-memory key immediately and persist it to .env on disk,
    next to the running app -- never baked into the built exe itself."""
    global FINNHUB_API_KEY, FINNHUB_WS_URL
    new_key = (new_key or "").strip()
    FINNHUB_API_KEY = new_key
    FINNHUB_WS_URL = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"

    lines = []
    found = False
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("FINNHUB_API_KEY="):
                lines.append(f"FINNHUB_API_KEY={new_key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"FINNHUB_API_KEY={new_key}")
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
