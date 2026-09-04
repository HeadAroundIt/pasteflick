"""Clipboard round-trip (Windows only)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app import clipboard as clip


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 clipboard")
def test_clipboard_roundtrip() -> None:
    sample = "PasteFlick clipboard probe\nline 2 · 你好"
    clip.set_text(sample)
    assert clip.get_text() == sample


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 clipboard")
def test_set_files_does_not_paste_as_filename(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# lantern-file\n", encoding="utf-8")
    clip.set_text("sentinel-text")
    clip.set_files([str(path)])
    text = clip.get_text()
    assert "notes.md" not in (text or "")
    assert "sentinel-text" not in (text or "")
