"""Focused browser regression for PasteFlick header wrapping."""

from __future__ import annotations

import subprocess
import tempfile
import threading
import time
import http.client
import json
from html.parser import HTMLParser
from pathlib import Path

from verify import Handler, TESTBED, ThreadingHTTPServer, find_browser


class ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_script = False
        self.current: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "script" and not dict(attrs).get("src"):
            self.in_script = True
            self.current = []

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.in_script:
            self.scripts.append("".join(self.current))
            self.in_script = False


def inspect_page(websocket_url: str) -> str:
    script = r"""
const ws = new WebSocket(process.argv[1]);
await new Promise((resolve) => ws.addEventListener("open", resolve, {once: true}));
ws.send(JSON.stringify({
  id: 1,
  method: "Runtime.evaluate",
  params: {
    expression: 'JSON.stringify({title:document.title,search:location.search,log:document.querySelector("#log")?.textContent,runner:typeof runWrapAutotest})',
    returnByValue: true
  }
}));
const value = await new Promise((resolve) => ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id === 1) resolve(message.result?.result?.value || JSON.stringify(message));
}));
console.log(value);
ws.close();
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, websocket_url],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=5,
    )
    return (result.stdout or result.stderr).strip()


def main() -> int:
    collector = ScriptCollector()
    collector.feed((TESTBED / "mock-chatgpt.html").read_text(encoding="utf-8"))
    syntax = subprocess.run(
        ["node", "--check", "-"],
        input=collector.scripts[-1],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if syntax.returncode:
        print(syntax.stderr)
        return 1

    browser = find_browser()
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if edge.is_file():
        browser = edge
    if browser is None:
        print("WRAP_TEST_FAIL: Chrome/Edge not found")
        return 1

    web_port = 8770
    server = ThreadingHTTPServer(("127.0.0.1", web_port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    profile = tempfile.mkdtemp(prefix="pasteflick-wrap-")
    process = subprocess.Popen(
        [
            str(browser),
            f"--user-data-dir={profile}",
            "--remote-debugging-port=9225",
            "--headless=new",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-proxy-server",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--window-size=1400,900",
            "--new-window",
            f"http://127.0.0.1:{web_port}/mock-chatgpt.html?wraptest=1&v=84",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        targets = []
        result = ""
        deadline = time.time() + 20
        while time.time() < deadline and not result:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", 9225, timeout=1)
                connection.request("GET", "/json")
                targets = json.loads(connection.getresponse().read().decode("utf-8"))
                connection.close()
                page_url = next(
                    (
                        str(target.get("url") or "")
                        for target in targets
                        if "127.0.0.1:8770/" in str(target.get("url") or "")
                    ),
                    "",
                )
                if page_url.endswith("#WRAP_TEST_OK"):
                    result = "WRAP_TEST_OK"
                elif page_url.endswith("#WRAP_TEST_FAIL"):
                    result = "WRAP_TEST_FAIL"
            except Exception:
                pass
            if not result:
                time.sleep(0.2)
        result = result or "WRAP_TEST_TIMEOUT"
        if result == "WRAP_TEST_FAIL":
            page = next(
                (target for target in targets if "127.0.0.1:8770/" in str(target.get("url") or "")),
                None,
            )
            if page and page.get("webSocketDebuggerUrl"):
                result += ": " + inspect_page(str(page["webSocketDebuggerUrl"]))
        print(result)
        if result == "WRAP_TEST_TIMEOUT":
            try:
                connection = http.client.HTTPConnection("127.0.0.1", 9225, timeout=2)
                connection.request("GET", "/json")
                targets = json.loads(connection.getresponse().read().decode("utf-8"))
                print("targets=" + " | ".join(str(target.get("url") or "") for target in targets))
                page = next(
                    (target for target in targets if "127.0.0.1:8770/" in str(target.get("url") or "")),
                    None,
                )
                if page and page.get("webSocketDebuggerUrl"):
                    print("page=" + inspect_page(str(page["webSocketDebuggerUrl"])))
                connection.close()
            except Exception as exc:
                print(f"targets_error={exc!r}")
            process.terminate()
            try:
                error = process.communicate(timeout=3)[1]
            except subprocess.TimeoutExpired:
                error = ""
            if error:
                print(error[-1200:])
        return 0 if result == "WRAP_TEST_OK" else 1
    finally:
        if process.poll() is None:
            process.terminate()
        server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
