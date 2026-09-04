"""Conversation JSON → Markdown (active branch only)."""

from __future__ import annotations

import json
from typing import Any


def conversation_id_from_url(url: str) -> str | None:
    """Pull /c/{uuid} from a chat URL."""
    if not url:
        return None
    parts = url.split("?")[0].rstrip("/").split("/")
    for i, part in enumerate(parts):
        if part == "c" and i + 1 < len(parts):
            cand = parts[i + 1]
            if len(cand) >= 8:
                return cand
    return None


def copy_header(*, title: str = "", url: str | None = None, note: str = "") -> str:
    """YAML header for chat chrome — not part of the copied words."""
    heading = (title or "Chat").strip() or "Chat"
    lines = ["---", f"title: {json.dumps(heading, ensure_ascii=False)}"]
    if url:
        lines.append(f"url: {json.dumps(str(url), ensure_ascii=False)}")
    extra = (note or "").strip()
    if extra:
        lines.append(f"note: {json.dumps(extra, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def format_markdown(
    *,
    title: str,
    turns: list[dict[str, str]],
    url: str | None = None,
    partial: bool = False,
    note: str = "",
) -> str:
    heading = (title or "Chat").strip() or "Chat"
    bits: list[str] = []
    if partial:
        bits.append("partial — only the messages currently mounted in the page were captured")
    if note:
        bits.append(note)
    blocks = [copy_header(title=heading, url=url, note=" · ".join(bits))]
    for turn in turns:
        blocks.append(f"## {turn['role']}\n\n{turn['body'].rstrip()}\n")
    return "\n".join(blocks).rstrip() + "\n"


def linearize_selection(
    text: str,
    *,
    title: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Wrap a user highlight as markdown suitable for the overlay."""
    body = (text or "").strip()
    heading = (title or "Selection").strip() or "Selection"
    markdown = copy_header(title=heading, url=url) + body + "\n"
    # Rough turn estimate: blank-line separated blocks.
    blocks = [b for b in body.split("\n\n") if b.strip()]
    return {
        "title": heading,
        "markdown": markdown,
        "turn_count": max(1, len(blocks)) if body else 0,
        "character_count": len(markdown),
        "partial": False,
        "source": "selection",
        "url": url or "",
    }


def linearize_dom_messages(
    messages: list[dict[str, str]],
    *,
    title: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """DOM fallback — always marked partial."""
    turns: list[dict[str, str]] = []
    for msg in messages:
        role_raw = (msg.get("role") or "unknown").lower()
        if role_raw == "user":
            role = "User"
        elif role_raw == "assistant":
            role = "Assistant"
        else:
            role = role_raw.capitalize()
        body = (msg.get("text") or "").strip()
        if not body:
            continue
        turns.append({"role": role, "body": body})
    heading = (title or "Chat").strip() or "Chat"
    markdown = format_markdown(title=heading, turns=turns, url=url, partial=True)
    return {
        "title": heading,
        "markdown": markdown,
        "turn_count": len(turns),
        "character_count": len(markdown),
        "partial": True,
        "source": "dom",
        "url": url or "",
    }


try:
    from app.private.conversation_payload import (
        linearize_conversation,
        turns_from_payload,
        walk_active_branch,
    )
except ImportError:  # PasteFlick / no unofficial payload
    linearize_conversation = None  # type: ignore[misc, assignment]
    turns_from_payload = None  # type: ignore[misc, assignment]
    walk_active_branch = None  # type: ignore[misc, assignment]
