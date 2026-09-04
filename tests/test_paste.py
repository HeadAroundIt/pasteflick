"""Paste goes to the last focused app, like Hush — not a hunt for a Cursor title."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import server as server_mod
from app.server import _paste_now, _paste_target, app, remember_foreground, state


LAST_APP = 42
CURSOR = 99
BROWSER = 7
OURS = 1
TOOL = 8


@pytest.fixture
def paste_env(monkeypatch):
    state.target_hwnd = 0
    live = {LAST_APP: True, CURSOR: True, BROWSER: True, OURS: True, TOOL: True}
    pasted: list[int] = []

    monkeypatch.setattr(server_mod.win, "find_hwnds_by_title", lambda *_a, **_k: {OURS})
    monkeypatch.setattr(server_mod.win, "is_window", lambda hwnd: bool(live.get(hwnd)))
    monkeypatch.setattr(server_mod.win, "is_browser_hwnd", lambda hwnd: hwnd == BROWSER)
    monkeypatch.setattr(
        server_mod.win,
        "is_paste_app",
        lambda hwnd: bool(live.get(hwnd)) and hwnd not in {BROWSER, TOOL},
    )
    monkeypatch.setattr(server_mod.win, "toplevel_hwnd", lambda hwnd: hwnd)
    monkeypatch.setattr(server_mod.win, "find_cursor_hwnd", lambda: CURSOR)
    monkeypatch.setattr(server_mod.win, "find_last_app_hwnd", lambda *_a, **_k: 0)
    monkeypatch.setattr(server_mod.win, "get_foreground", lambda: BROWSER)
    monkeypatch.setattr(server_mod.clip, "set_text", lambda _text: None)

    def fake_paste(hwnd: int) -> bool:
        pasted.append(hwnd)
        return True

    monkeypatch.setattr(server_mod.win, "paste_into", fake_paste)
    yield pasted
    state.target_hwnd = 0


def test_paste_prefers_last_app_over_cursor_window(paste_env) -> None:
    state.remember_target(LAST_APP)
    assert _paste_target() == LAST_APP
    assert _paste_now("hello") is True
    assert paste_env == [LAST_APP]


def test_paste_skips_browser_and_falls_back_to_cursor(paste_env) -> None:
    state.remember_target(BROWSER)
    assert _paste_target() == CURSOR
    assert _paste_now("hello") is True
    assert paste_env == [CURSOR]


def test_paste_uses_cursor_when_nothing_was_remembered(paste_env) -> None:
    assert _paste_target() == CURSOR


def test_paste_uses_window_behind_the_browser(paste_env, monkeypatch) -> None:
    monkeypatch.setattr(server_mod.win, "find_last_app_hwnd", lambda *_a, **_k: LAST_APP)
    assert _paste_target() == LAST_APP


def test_browser_foreground_does_not_replace_last_app(paste_env) -> None:
    state.remember_target(LAST_APP)
    remember_foreground()
    assert state.pop_target() == LAST_APP
    assert _paste_target() == LAST_APP


def test_paste_skips_tool_window_and_falls_back_to_cursor(paste_env) -> None:
    state.remember_target(TOOL)
    assert _paste_target() == CURSOR
    assert _paste_now("hello") is True
    assert paste_env == [CURSOR]


def test_ingest_pastes_into_last_app(paste_env) -> None:
    state.remember_target(LAST_APP)
    client = TestClient(app)
    res = client.post(
        "/api/ingest",
        json={
            "markdown": "paste me",
            "destination": "cursor",
            "copy_to_clipboard": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["pasted"] is True
    assert data["destination"] == "cursor"
    assert paste_env == [LAST_APP]
