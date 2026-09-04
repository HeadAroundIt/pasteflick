"""In-memory transcript state for the overlay."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptState:
    title: str = ""
    markdown: str = ""
    url: str = ""
    source: str = ""
    partial: bool = False
    turn_count: int = 0
    character_count: int = 0
    status: str = "Idle — highlight in a chat, then use the extension"
    updated_at: float = field(default_factory=time.time)
    target_hwnd: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snap_unlocked()

    def _snap_unlocked(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "markdown": self.markdown,
            "url": self.url,
            "source": self.source,
            "partial": self.partial,
            "turn_count": self.turn_count,
            "character_count": self.character_count,
            "status": self.status,
            "updated_at": self.updated_at,
        }

    def apply_payload(self, payload: dict[str, Any], *, status: str | None = None) -> dict[str, Any]:
        with self._lock:
            self.title = str(payload.get("title") or "")
            self.markdown = str(payload.get("markdown") or "")
            self.url = str(payload.get("url") or "")
            self.source = str(payload.get("source") or "")
            self.partial = bool(payload.get("partial"))
            self.turn_count = int(payload.get("turn_count") or 0)
            self.character_count = int(
                payload.get("character_count") or len(self.markdown)
            )
            if status is not None:
                self.status = status
            elif self.partial:
                self.status = "Partial (DOM) — some messages may be missing"
            elif self.source == "selection":
                self.status = "Loaded from selection"
            elif self.source == "api":
                self.status = "Pulled full thread"
            else:
                self.status = "Updated"
            self.updated_at = time.time()
            return self._snap_unlocked()

    def set_markdown(self, text: str, *, status: str = "Edited") -> dict[str, Any]:
        with self._lock:
            self.markdown = text
            self.character_count = len(text)
            self.source = self.source or "manual"
            self.status = status
            self.updated_at = time.time()
            return self._snap_unlocked()

    def clear(self) -> dict[str, Any]:
        with self._lock:
            self.title = ""
            self.markdown = ""
            self.url = ""
            self.source = ""
            self.partial = False
            self.turn_count = 0
            self.character_count = 0
            self.status = "Cleared"
            self.updated_at = time.time()
            return self._snap_unlocked()

    def set_status(self, status: str) -> None:
        with self._lock:
            self.status = status
            self.updated_at = time.time()

    def remember_target(self, hwnd: int) -> None:
        with self._lock:
            if hwnd:
                self.target_hwnd = int(hwnd)

    def pop_target(self) -> int:
        with self._lock:
            return int(self.target_hwnd or 0)
