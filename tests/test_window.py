"""Overlay matching and paste-app filters — keep Auto-paste out of tool windows."""

from __future__ import annotations

from app.window import (
    WS_CAPTION,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    browser_title_match,
    is_browser_hwnd,
    is_paste_app,
    overlay_title_match,
)


def test_overlay_title_is_exact_not_cursor_workspace() -> None:
    assert overlay_title_match("PasteFlick")
    assert overlay_title_match("pasteflick")
    assert not overlay_title_match("PasteFlick - Cursor")
    assert not overlay_title_match("window.py - PasteFlick - Cursor")
    assert not overlay_title_match("PasteFlick Auto-paste")
    assert not overlay_title_match("")


def test_browser_title_ignores_filename_tokens() -> None:
    assert browser_title_match("Hush Work 7 - Brave")
    assert browser_title_match("Cursor - The best way to code with AI - Brave")
    assert browser_title_match("ChatGPT - Google Chrome")
    assert browser_title_match("docs - Microsoft Edge")
    assert browser_title_match("Inbox - Arc")
    assert not browser_title_match("architecture.py - PasteFlick - Cursor")
    assert not browser_title_match("brave.ts - Cursor")
    assert not browser_title_match("chromium.md - Hush - Cursor")
    assert not browser_title_match("March notes - Cursor")
    assert not browser_title_match("PasteFlick - Cursor")


def test_is_browser_hwnd_uses_exe_before_title(monkeypatch) -> None:
    titles = {
        1: "architecture.py - PasteFlick - Cursor",
        2: "ChatGPT",
        3: "brave.ts - Cursor",
    }
    exes = {1: "Cursor.exe", 2: "brave.exe", 3: "Cursor.exe"}
    monkeypatch.setattr("app.window.window_title", lambda hwnd: titles.get(hwnd, ""))
    monkeypatch.setattr("app.window.window_exe_name", lambda hwnd: exes.get(hwnd, ""))

    assert is_browser_hwnd(1) is False
    assert is_browser_hwnd(2) is True
    assert is_browser_hwnd(3) is False


def test_is_paste_app_skips_tool_windows_and_browsers(monkeypatch) -> None:
    titles = {1: "PasteFlick - Cursor", 2: "RzMonitorForegroundWindow", 3: "Chat - Brave", 4: "Hush Overlay", 5: "Settings"}
    styles = {1: WS_CAPTION, 2: 0, 3: WS_CAPTION, 4: 0, 5: WS_CAPTION}
    exstyles = {1: 0, 2: WS_EX_TOOLWINDOW, 3: 0, 4: WS_EX_NOACTIVATE, 5: 0}
    exes = {1: "Cursor.exe", 2: "RazerAppEngine.exe", 3: "brave.exe", 4: "pythonw.exe", 5: "ApplicationFrameHost.exe"}

    monkeypatch.setattr("app.window.is_window", lambda hwnd: hwnd in titles)
    monkeypatch.setattr("app.window.user32.IsWindowVisible", lambda hwnd: True)
    monkeypatch.setattr("app.window.window_title", lambda hwnd: titles.get(hwnd, ""))
    monkeypatch.setattr("app.window.window_style", lambda hwnd: styles.get(hwnd, 0))
    monkeypatch.setattr("app.window.window_exstyle", lambda hwnd: exstyles.get(hwnd, 0))
    monkeypatch.setattr("app.window.window_exe_name", lambda hwnd: exes.get(hwnd, ""))

    assert is_paste_app(1) is True
    assert is_paste_app(2) is False
    assert is_paste_app(3) is False
    assert is_paste_app(4) is False
    assert is_paste_app(5) is False
    assert is_paste_app(0) is False
