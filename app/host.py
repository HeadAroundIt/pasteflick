"""pywebview host for the PasteFlick overlay."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import uvicorn
import webview

from app import DEFAULT_PORT, OVERLAY_TITLE, SHELL_HEX
from app.server import app, overlay_is_up, remember_foreground

ROOT = Path(__file__).resolve().parent.parent
WIDTH = 560
HEIGHT = 760


class Api:
    def __init__(self) -> None:
        self._window: webview.Window | None = None

    def bind(self, window: webview.Window) -> None:
        self._window = window

    def close_window(self) -> None:
        if self._window is not None:
            self._window.destroy()


def _run_server(port: int) -> None:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    uvicorn.Server(config).run()


def _poll_targets() -> None:
    while True:
        try:
            remember_foreground()
        except Exception:
            pass
        time.sleep(0.08)


def main() -> int:
    from app.update import default_install_root, ensure_install_metadata

    installed = default_install_root()
    if ROOT.resolve() == installed.resolve():
        ensure_install_metadata(installed)
    ui = ROOT / "ui" / "dist" / "index.html"
    if not ui.is_file():
        print("UI not built. From the ui folder run: npm install && npm run build")
        print("Or use run.bat, which builds automatically.")
        return 1

    remember_foreground()

    port = DEFAULT_PORT
    if not overlay_is_up():
        threading.Thread(target=_run_server, args=(port,), daemon=True).start()
        threading.Thread(target=_poll_targets, daemon=True).start()

    api = Api()
    window = webview.create_window(
        OVERLAY_TITLE,
        url=f"http://127.0.0.1:{port}/",
        width=WIDTH,
        height=HEIGHT,
        background_color=SHELL_HEX,
        frameless=True,
        easy_drag=True,
        on_top=True,
        js_api=api,
    )
    api.bind(window)
    webview.start(gui="edgechromium", debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
