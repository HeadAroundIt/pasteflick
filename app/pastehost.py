"""Headless Auto-paste helper — no overlay window."""

from __future__ import annotations

import subprocess
import sys
import threading
import time

import uvicorn

from app import DEFAULT_PORT
from app.server import app, overlay_is_up, remember_foreground

UPDATE_EVERY = 6 * 3600


def _poll_targets() -> None:
    while True:
        try:
            remember_foreground()
        except Exception:
            pass
        time.sleep(0.08)


def _restart_windows_helper() -> None:
    from app.update import default_install_root

    script = default_install_root() / "installer" / "start-pastehost.ps1"
    if sys.platform != "win32" or not script.is_file():
        return
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=str(script.parent.parent),
    )


def _update_loop() -> None:
    time.sleep(45)
    while True:
        try:
            from app.update import check_and_apply

            result = check_and_apply()
            if result.applied:
                _restart_windows_helper()
                return
        except Exception:
            pass
        time.sleep(UPDATE_EVERY)


def main() -> int:
    from app.update import ensure_install_metadata

    ensure_install_metadata()
    if overlay_is_up():
        return 0
    remember_foreground()
    threading.Thread(target=_poll_targets, daemon=True).start()
    threading.Thread(target=_update_loop, daemon=True).start()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=DEFAULT_PORT,
        log_level="warning",
        access_log=False,
    )
    uvicorn.Server(config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
