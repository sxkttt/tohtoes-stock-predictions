"""Native desktop shell for Tohtoe's Stock Predictions: runs the FastAPI
server in-process and displays it in a PySide6 window (no browser tab, no
console window)."""
import json
import logging
import multiprocessing
import os
import socket
import sys
import threading
import time
import urllib.request
from contextlib import closing
from pathlib import Path

# In a windowed (console=False) PyInstaller build, sys.stdout/stderr are None --
# uvicorn/click write to them during server startup and crash the (invisible,
# unlogged) background thread. Give them somewhere harmless to write.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import uvicorn
from PySide6.QtCore import QEvent, QThread, QUrl, Qt, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QStyle, QSystemTrayIcon
from PySide6.QtWebEngineWidgets import QWebEngineView

# Tohtoe's edition of the auto-update check compares its version.py against
# this fork's GitHub repo; PulseChart never sets this, so the same endpoint
# there just reports itself disabled.
os.environ["UPDATE_REPO"] = "sxkttt/tohtoes-stock-predictions"

from backend import config
from backend.main import app as fastapi_app

log = logging.getLogger("desktop_app")

# Same codebase ships as two branded editions of the same app -- the Mac
# build gets its own suffixed name so it's clearly distinguishable from the
# Windows edition (e.g. if someone has both on a synced drive/screenshot).
APP_NAME = "Tohtoe's Stock Predictions for Mac" if sys.platform == "darwin" else "Tohtoe's Stock Predictions"


def _setup_logging():
    log_dir = config.ROOT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        filename=log_dir / "tohtoe.log",
        filemode="a",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_server(port: int):
    uv_config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(uv_config)
    server.run()


def _wait_for_server(url: str, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.15)
    return False


class NoZoomWebEngineView(QWebEngineView):
    """Chromium's built-in page zoom (Ctrl+scroll, Ctrl+=/-/0, trackpad
    pinch) is a browser affordance that doesn't belong in a native desktop
    app -- it's easy to trigger by accident (e.g. a stray Ctrl+scroll while
    panning the chart) and there's no in-app way to reset it. Zoom is
    locked to 100% by swallowing the zoom gestures/shortcuts before
    Chromium ever sees them."""

    _ZOOM_KEYS = {Qt.Key_Plus, Qt.Key_Minus, Qt.Key_Equal, Qt.Key_0}

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and event.key() in self._ZOOM_KEYS:
            event.ignore()
            return
        super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QEvent.NativeGesture:  # trackpad pinch-to-zoom
            return True
        return super().event(event)


class AlertPoller(QThread):
    """Polls the alerts endpoint off the Qt main thread (network I/O has no
    business blocking the UI) and emits any newly-fired events so the
    window can turn them into native tray notifications -- this is what
    makes alerts show up even while the app is minimized."""

    events_found = Signal(list)

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                with urllib.request.urlopen(f"{self.base_url}api/alerts/pending", timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                events = data.get("events") or []
                if events:
                    self.events_found.emit(events)
                    ids = [e["id"] for e in events]
                    req = urllib.request.Request(
                        f"{self.base_url}api/alerts/seen",
                        data=json.dumps({"ids": ids}).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=5)
            except Exception:
                log.exception("alert poll failed")
            self.msleep(15000)


class UpdateChecker(QThread):
    """One-shot check against /api/update-check, run once per app launch.
    A no-op on editions that don't set UPDATE_REPO (the endpoint just
    reports itself disabled), so this is safe to include unconditionally
    rather than needing an edition-specific code path here too."""

    update_found = Signal(dict)

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url

    def run(self):
        try:
            with urllib.request.urlopen(f"{self.base_url}api/update-check", timeout=5) as resp:
                data = json.loads(resp.read().decode())
            if data.get("update_available"):
                self.update_found.emit(data)
        except Exception:
            log.exception("update check failed")


class MainWindow(QMainWindow):
    def __init__(self, url: str):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Real-Time Stock Patterns")
        self.resize(1440, 920)
        self.view = NoZoomWebEngineView()
        self.view.load(QUrl(url))
        self.setCentralWidget(self.view)

        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        self.tray.setToolTip(APP_NAME)
        self.tray.show()

        self.poller = AlertPoller(url)
        self.poller.events_found.connect(self._on_alert_events)
        self.poller.start()

        self.update_checker = UpdateChecker(url)
        self.update_checker.update_found.connect(self._on_update_found)
        self.update_checker.start()

    def _on_alert_events(self, events: list):
        for e in events:
            self.tray.showMessage(f"{APP_NAME} Alert", e["message"], QSystemTrayIcon.Information, 8000)

    def _on_update_found(self, data: dict):
        self.tray.showMessage(
            f"{APP_NAME} Update Available",
            f"Version {data.get('latest')} is available (you're on {data.get('current')}).",
            QSystemTrayIcon.Information, 10000,
        )

    def closeEvent(self, event):
        self.poller.stop()
        self.poller.wait(2000)
        super().closeEvent(event)


def main():
    _setup_logging()
    log.info("Starting %s desktop app", APP_NAME)

    port = _find_free_port()
    server_thread = threading.Thread(target=_run_server, args=(port,), daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}/"
    if not _wait_for_server(base_url):
        log.error("Backend server did not start in time")

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    window = MainWindow(base_url)
    window.show()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
