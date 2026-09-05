"""Lightweight end-to-end verifier for PasteFlick."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTBED = Path(__file__).resolve().parent
EXT = ROOT / "extension"
OVERLAY = "http://127.0.0.1:8768"
MOCK = "http://127.0.0.1:8770/mock-chatgpt.html?autotest=1&v=78"

BROWSER_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "Microsoft/Edge/Application/msedge.exe",
]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TESTBED), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_GET(self):  # noqa: N802
        name = self.path.split("?", 1)[0].lstrip("/")
        if name in {"extractor.js", "pasteflick.js"}:
            data = (EXT / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def http_json(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            raw = res.read().decode("utf-8")
            return res.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def find_browser() -> Path | None:
    for path in BROWSER_CANDIDATES:
        if path.is_file():
            return path
    return None


def python_exe() -> str:
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    return str(venv if venv.is_file() else sys.executable)


def ok(label: str) -> None:
    print(f"  PASS  {label}")


def fail(label: str, detail: str) -> None:
    print(f"  FAIL  {label}: {detail}")
    raise SystemExit(1)


def run_unit_tests() -> None:
    print("\n== unit tests ==")
    proc = subprocess.run([python_exe(), "-m", "pytest", "tests", "-q"], cwd=ROOT)
    if proc.returncode != 0:
        fail("pytest", f"exit {proc.returncode}")
    ok("pytest")


def start_overlay() -> subprocess.Popen | None:
    print("\n== overlay API (8768) ==")
    if port_open("127.0.0.1", 8768):
        print("  info  port 8768 already in use — reusing it")
        return None
    proc = subprocess.Popen(
        [
            python_exe(),
            "-m",
            "uvicorn",
            "app.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8768",
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
    )
    for _ in range(50):
        if port_open("127.0.0.1", 8768):
            ok("overlay listening")
            return proc
        if proc.poll() is not None:
            fail("overlay start", f"process exited {proc.returncode}")
        time.sleep(0.15)
    fail("overlay start", "timed out")
    return proc


def start_mock_server() -> ThreadingHTTPServer:
    print("\n== mock chat page (8770) ==")
    if port_open("127.0.0.1", 8770):
        fail("mock server", "port 8770 already in use")
    httpd = ThreadingHTTPServer(("127.0.0.1", 8770), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    ok("mock server listening")
    return httpd


def api_smoke() -> None:
    print("\n== API smoke ==")
    code, health = http_json("GET", f"{OVERLAY}/api/health")
    if code != 200 or not health.get("ok"):
        fail("health", str(health))
    ok("health")

    marker = f"verify-marker-{int(time.time())}"
    md = f"# API smoke\n\n{marker}\n"
    code, snap = http_json(
        "POST",
        f"{OVERLAY}/api/ingest",
        {
            "title": "API smoke",
            "markdown": md,
            "source": "selection",
            "turn_count": 1,
            "character_count": len(md),
            "copy_to_clipboard": True,
        },
    )
    if code != 200:
        fail("ingest", str(snap))
    if marker not in snap.get("markdown", ""):
        fail("ingest markdown", str(snap)[:200])
    ok("ingest")

    code, state = http_json("GET", f"{OVERLAY}/api/state")
    if code != 200 or marker not in state.get("markdown", ""):
        fail("state", str(state)[:200])
    ok("state")

    code, copied = http_json("POST", f"{OVERLAY}/api/copy", {})
    if code != 200:
        fail("copy", str(copied))
    ok("copy endpoint")

    sys.path.insert(0, str(ROOT))
    from app import clipboard as clip

    clip.set_text(marker)
    got = clip.get_text()
    if got != marker:
        fail("clipboard", repr(got))
    ok("clipboard round-trip")


def chrome_autotest() -> None:
    print("\n== Chrome mock autotest ==")
    browser = find_browser()
    if browser is None:
        fail("browser", "Chrome/Edge not found")

    http_json(
        "POST",
        f"{OVERLAY}/api/ingest",
        {
            "title": "TESTBED_PENDING",
            "markdown": "# pending\n",
            "source": "manual",
            "copy_to_clipboard": False,
        },
    )

    profile = Path(tempfile.mkdtemp(prefix="pasteflick-verify-chrome-"))
    proc = subprocess.Popen(
        [
            str(browser),
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--noerrdialogs",
            "--window-size=1400,900",
            "--new-window",
            MOCK,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + 120
    last_title = ""
    while time.time() < deadline:
        code, state = http_json("GET", f"{OVERLAY}/api/state")
        if code == 200:
            last_title = str(state.get("title") or "")
            if last_title == "TESTBED_OK":
                ok("mock page -> overlay ingest")
                try:
                    proc.terminate()
                except Exception:
                    pass
                return
            if last_title == "TESTBED_FAIL":
                fail("mock autotest", state.get("markdown", "")[:500])
        time.sleep(0.4)

    try:
        proc.terminate()
    except Exception:
        pass
    fail("mock autotest", f"timed out (last title={last_title!r})")


def main() -> int:
    print("PasteFlick — verify")
    run_unit_tests()
    overlay = start_overlay()
    httpd: ThreadingHTTPServer | None = None
    try:
        httpd = start_mock_server()
        api_smoke()
        chrome_autotest()
    finally:
        if httpd is not None:
            httpd.shutdown()
        if overlay is not None:
            overlay.terminate()
            try:
                overlay.wait(timeout=3)
            except Exception:
                overlay.kill()
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
