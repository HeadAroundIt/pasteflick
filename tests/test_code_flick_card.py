"""Code fences get a Flick card without bookmarking first."""

from __future__ import annotations

import socket
import threading
from http.server import ThreadingHTTPServer

import pytest

from testbed.verify import Handler


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_code_fence_has_flick_card() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as p:
            browser = None
            for launcher in (
                lambda: p.chromium.launch(channel="msedge", headless=True),
                lambda: p.chromium.launch(channel="chrome", headless=True),
                lambda: p.chromium.launch(headless=True),
            ):
                try:
                    browser = launcher()
                    break
                except Exception:
                    continue
            if browser is None:
                pytest.skip("No browser for Playwright")
            page = browser.new_page(viewport={"width": 1200, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/mock-chatgpt.html", wait_until="networkidle")
            page.wait_for_function("() => !!(window.PasteFlick && window.PasteFlick.scan)")
            found = page.evaluate(
                """() => {
                  PasteFlick.scan();
                  const python = document.querySelector('[data-message-id="msg-assistant-1"] > pre');
                  const plain = document.querySelector('#code-plain');
                  const mermaid = document.querySelector('#flow-chart pre');
                  const doc = document.querySelector('#named-doc');
                  const pythonPin = python && PasteFlick.pinFor(python);
                  const plainPin = plain && PasteFlick.pinFor(plain);
                  const ui = PasteFlick.dockRoot();
                  const blocks = ui
                    ? Array.from(ui.querySelectorAll('[data-pasteflick="pin"][data-kind="block"]'))
                    : [];
                  const flick = pythonPin && pythonPin.querySelector('[data-pasteflick="paste-block"]');
                  return {
                    python: !!(pythonPin && pythonPin.getAttribute('data-block-kind') === 'code'),
                    plain: !!(plainPin && plainPin.getAttribute('data-block-kind') === 'code'),
                    mermaid: !!(mermaid && PasteFlick.pinFor(mermaid)),
                    doc: !!(doc && PasteFlick.pinFor(doc)),
                    onlyCode: blocks.length === 2 &&
                      blocks.every((pin) => pin.getAttribute('data-block-kind') === 'code'),
                    flickPrimary: !!(flick && flick.classList.contains('is-primary')),
                    flickTip: flick ? String(flick.title || '') : '',
                  };
                }"""
            )
            browser.close()
    finally:
        httpd.shutdown()

    assert found["python"]
    assert found["plain"]
    assert found["onlyCode"]
    assert found["flickPrimary"]
    assert found["flickTip"] == "Flick this code."
    assert not found["mermaid"]
    assert not found["doc"]
