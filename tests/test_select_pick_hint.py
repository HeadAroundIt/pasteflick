"""Select-view footer note appears only while text is highlighted."""

from __future__ import annotations

import socket
import threading
from http.server import ThreadingHTTPServer

import pytest

from testbed.verify import Handler, TESTBED


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_select_view_saving_highlight_note() -> None:
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
            opened = page.evaluate(
                """async () => {
                  const api = window.__transcriptCopy;
                  if (!api || !api.openSelectView) return false;
                  const res = await api.openSelectView();
                  return !!(res && res.opened);
                }"""
            )
            assert opened
            hint = page.locator('[data-pasteflick="pick-hint"]')
            hint.wait_for(state="attached")
            assert (hint.text_content() or "").strip() == ""
            page.locator(".sm-pre").evaluate(
                """el => {
                  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                  let node = walker.nextNode();
                  while (node && !String(node.data || '').trim()) node = walker.nextNode();
                  if (!node) return false;
                  const start = String(node.data).search(/\\S/);
                  if (start < 0) return false;
                  const end = Math.min(node.data.length, start + 8);
                  if (end <= start) return false;
                  const range = document.createRange();
                  range.setStart(node, start);
                  range.setEnd(node, end);
                  const sel = window.getSelection();
                  sel.removeAllRanges();
                  sel.addRange(range);
                  return true;
                }"""
            )
            page.wait_for_function(
                "() => (document.querySelector('[data-pasteflick=\"pick-hint\"]')?.textContent || '').trim() === 'Saving highlight'"
            )
            page.locator(".sm-pre").evaluate(
                """el => {
                  const range = document.createRange();
                  range.selectNodeContents(el);
                  const sel = window.getSelection();
                  sel.removeAllRanges();
                  sel.addRange(range);
                }"""
            )
            page.wait_for_function(
                "() => !(document.querySelector('[data-pasteflick=\"pick-hint\"]')?.textContent || '').trim()"
            )
            page.evaluate("() => window.getSelection().removeAllRanges()")
            page.wait_for_function(
                "() => !(document.querySelector('[data-pasteflick=\"pick-hint\"]')?.textContent || '').trim()"
            )
            browser.close()
    finally:
        httpd.shutdown()
