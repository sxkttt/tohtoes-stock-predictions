# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TohtoeStockPredictions.exe (onefile, windowed PySide6 app).

Bundles the FastAPI/uvicorn backend and the static frontend (HTML/JS/CSS)
into a single exe. At runtime, desktop_app.py starts the server on a free
localhost port in a background thread and shows it in a QWebEngineView --
no browser, no console window.

The frontend/ directory is bundled as read-only data (loaded via
sys._MEIPASS, see backend/config.py). The .env file and data/ (SQLite db)
live next to the produced exe instead, so users can edit their API key or
wipe history without rebuilding.

Run: pyinstaller tohtoe.spec --noconfirm

On macOS this also wraps the executable in a proper
"Tohtoe's Stock Predictions for Mac.app" bundle (via BUNDLE below) --
without it PyInstaller would just emit a bare Unix executable, not
something Finder/Dock/Gatekeeper treat as a real app. The Mac edition is
named distinctly from the Windows one (see desktop_app.py's APP_NAME) so
the two are clearly distinguishable. The .app is unsigned; first launch
requires right-click > Open once to get past Gatekeeper (or
`xattr -cr "Tohtoe's Stock Predictions for Mac.app"` to clear the
quarantine flag). Distributing it to other people's Macs would
additionally need an Apple Developer ID + notarization -- not required
just to run it yourself. Run build_dmg.sh afterward to package the .app
into a drag-to-Applications installer .dmg.
"""
import sys

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = collect_submodules("multiprocessing") + [
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "backend.main", "backend.config", "backend.db", "backend.candles",
    "backend.patterns", "backend.finnhub_feed", "backend.history", "backend.symbols",
    "backend.settings", "backend.indicators", "backend.fundamentals", "backend.macro", "backend.advisor",
    "backend.alerts", "backend.econ_calendar", "backend.options", "backend.version",
]

a = Analysis(
    ["desktop_app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("frontend", "frontend"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "tkinter", "IPython", "notebook",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtMultimedia",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSensors",
        "PySide6.QtPositioning", "PySide6.QtSerialPort", "PySide6.Qt3DCore",
        "PySide6.QtPdf", "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtTest", "PySide6.QtDesigner",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TohtoeStockPredictions",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Tohtoe's Stock Predictions for Mac.app",
        icon=None,
        bundle_identifier="com.tohtoe.stockpredictions.mac",
        info_plist={
            "CFBundleName": "Tohtoe's Stock Predictions for Mac",
            "CFBundleDisplayName": "Tohtoe's Stock Predictions for Mac",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "CFBundleShortVersionString": "1.0.0",
        },
    )
