"""Tests for selection/DOM Markdown wrapping."""

from __future__ import annotations

from app.linearize import (
    conversation_id_from_url,
    format_markdown,
    linearize_conversation,
    linearize_dom_messages,
    linearize_selection,
)


def test_conversation_id_from_url() -> None:
    assert (
        conversation_id_from_url("https://chatgpt.com/c/abc-123-def?foo=1")
        == "abc-123-def"
    )
    assert conversation_id_from_url("https://chatgpt.com/") is None


def test_unofficial_payload_helpers_are_absent() -> None:
    assert linearize_conversation is None


def test_linearize_selection() -> None:
    result = linearize_selection(
        "Just this highlighted bit",
        title="My pick",
        url="https://chatgpt.com/c/x",
    )
    assert result["source"] == "selection"
    assert result["partial"] is False
    assert "Just this highlighted bit" in result["markdown"]
    assert result["markdown"].startswith("---\n")
    assert 'title: "My pick"' in result["markdown"]
    assert not result["markdown"].lstrip().startswith("# ")


def test_dom_fallback_marked_partial() -> None:
    result = linearize_dom_messages(
        [
            {"role": "user", "text": "Q"},
            {"role": "assistant", "text": "A"},
        ],
        title="Partial",
    )
    assert result["partial"] is True
    assert result["source"] == "dom"
    assert result["markdown"].startswith("---\n")
    assert "partial" in result["markdown"].lower()
    assert result["turn_count"] == 2


def test_format_markdown_partial_note() -> None:
    md = format_markdown(
        title="T",
        turns=[{"role": "User", "body": "hi"}],
        partial=True,
    )
    assert "partial" in md.lower()
    assert md.startswith("---\n")
    assert 'title: "T"' in md
    assert not md.lstrip().startswith("# ")
