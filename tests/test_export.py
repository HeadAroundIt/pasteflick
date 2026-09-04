"""Markdown / PDF export and destination mutual exclusion."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import export as files
from app.server import app, _destination
from app.server import IngestBody


def test_safe_filename_strips_junk() -> None:
    assert files.safe_filename("My chat: v2") == "My chat_ v2"
    assert files.safe_filename("") == "transcript"


def test_write_markdown_and_pdf(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PASTEFLICK_EXPORT_DIR", str(tmp_path))
    marker = "export-marker-copper-lantern"
    md = files.export_transcript(f"# Title\n\n{marker}\n", title="Fixture chat", fmt="md")
    assert md.suffix == ".md"
    assert md.parent == tmp_path / "Exports"
    assert marker in md.read_text(encoding="utf-8")

    pdf = files.export_transcript(f"# Title\n\n{marker}\n", title="Fixture chat", fmt="pdf")
    raw = pdf.read_bytes()
    assert pdf.suffix == ".pdf"
    assert raw.startswith(b"%PDF-")
    assert raw.rstrip().endswith(b"%%EOF") or b"%%EOF" in raw[-32:]


def test_destination_prefers_explicit_field() -> None:
    body = IngestBody(markdown="x", destination="file", auto_paste=True, save=False)
    assert _destination(body) == "file"
    body = IngestBody(markdown="x", destination="cursor", save=True)
    assert _destination(body) == "cursor"
    body = IngestBody(markdown="x", auto_paste=True)
    assert _destination(body) == "cursor"
    body = IngestBody(markdown="x")
    assert _destination(body) == "clipboard"


def test_ingest_file_does_not_paste(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PASTEFLICK_EXPORT_DIR", str(tmp_path))
    client = TestClient(app)
    marker = "ingest-file-only-xyz"
    res = client.post(
        "/api/ingest",
        json={
            "title": "File dest",
            "markdown": f"# File dest\n\n{marker}\n",
            "destination": "file",
            "format": "md",
            "auto_paste": True,
            "copy_to_clipboard": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["saved"] is True
    assert data["pasted"] is False
    assert data["destination"] == "file"
    saved = Path(data["path"])
    assert saved.is_file()
    assert saved.parent == tmp_path / "Exports"
    assert marker in saved.read_text(encoding="utf-8")

    pdf_res = client.post(
        "/api/ingest",
        json={
            "title": "File dest",
            "markdown": f"# PDF dest\n\n{marker}\n",
            "destination": "file",
            "format": "pdf",
            "auto_paste": True,
            "copy_to_clipboard": False,
        },
    )
    assert pdf_res.status_code == 200
    pdf_data = pdf_res.json()
    assert pdf_data["saved"] is True
    assert pdf_data["pasted"] is False
    pdf_path = Path(pdf_data["path"])
    assert pdf_path.suffix == ".pdf"
    raw = pdf_path.read_bytes()
    assert raw.startswith(b"%PDF-")
    assert b"%%EOF" in raw[-64:]


def test_ingest_clipboard_does_not_save(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PASTEFLICK_EXPORT_DIR", str(tmp_path))
    client = TestClient(app)
    res = client.post(
        "/api/ingest",
        json={
            "title": "Clip only",
            "markdown": "# Clip only\n\nnothing-saved-here\n",
            "destination": "clipboard",
            "copy_to_clipboard": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["saved"] is False
    assert data["pasted"] is False
    assert list(tmp_path.iterdir()) == []


def test_export_dir_sets_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(files, "settings_path", lambda: tmp_path / "settings.json")
    monkeypatch.delenv("PASTEFLICK_EXPORT_DIR", raising=False)
    dest = tmp_path / "picked"
    dest.mkdir()
    client = TestClient(app)
    res = client.post("/api/export-dir", json={"path": str(dest)})
    assert res.status_code == 200
    data = res.json()
    assert data["picked"] is True
    assert Path(data["dir"]) == dest.resolve()
    assert data["format"] in {"md", "pdf"}


def test_export_dir_normalizes_generated_subfolders(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(files, "settings_path", lambda: tmp_path / "settings.json")
    monkeypatch.delenv("PASTEFLICK_EXPORT_DIR", raising=False)
    root = tmp_path / "PasteFlick"
    selected = root / "Exports"
    selected.mkdir(parents=True)
    assert files.set_export_dir(selected) == root.resolve()
    assert files.get_output_root() == root.resolve()
    assert files.get_export_dir() == root.resolve() / "Exports"
    assert files.get_files_dir() == root.resolve() / "Files"


def test_health_includes_version() -> None:
    from app.server import ROOT
    from app.update import read_manifest_version

    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["app"] == "pasteflick"
    assert data["version"] == read_manifest_version(ROOT)


def test_export_format_persists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(files, "settings_path", lambda: tmp_path / "settings.json")
    monkeypatch.delenv("PASTEFLICK_EXPORT_DIR", raising=False)
    client = TestClient(app)
    assert client.get("/api/export-settings").json()["format"] == "md"
    res = client.post("/api/export-format", json={"format": "pdf"})
    assert res.status_code == 200
    assert res.json()["format"] == "pdf"
    assert files.get_export_format() == "pdf"
    res = client.post("/api/export-format", json={"format": "markdown"})
    assert res.json()["format"] == "md"


def test_pdf_accepts_unicode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PASTEFLICK_EXPORT_DIR", str(tmp_path))
    pdf = files.export_transcript("Hello 你好 — café\n", title="Unicode chat", fmt="pdf")
    raw = pdf.read_bytes()
    assert pdf.suffix == ".pdf"
    assert raw.startswith(b"%PDF-")
    assert b"%%EOF" in raw[-64:]
    assert pdf.stat().st_size > 200


def test_keep_filename_keeps_pdf() -> None:
    assert files.keep_filename("notes.pdf") == "notes.pdf"
    assert files.keep_filename("notes", "application/pdf") == "notes.pdf"
    assert files.keep_filename("notes", "text/markdown") == "notes.md"


def test_ingest_file_saves_original_bytes(tmp_path: Path, monkeypatch) -> None:
    import base64

    monkeypatch.setenv("PASTEFLICK_EXPORT_DIR", str(tmp_path))
    raw = b"%PDF-1.1\n%%EOF\n"
    client = TestClient(app)
    res = client.post(
        "/api/ingest-file",
        json={
            "name": "notes.pdf",
            "mime": "application/pdf",
            "data": base64.b64encode(raw).decode("ascii"),
            "destination": "file",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["saved"] is True
    path = Path(data["path"])
    assert path.name == "notes.pdf"
    assert path.parent == tmp_path / "Files"
    assert path.read_bytes() == raw


def test_ingest_file_saves_markdown_bytes(tmp_path: Path, monkeypatch) -> None:
    import base64

    monkeypatch.setenv("PASTEFLICK_EXPORT_DIR", str(tmp_path))
    raw = b"# notes\nlantern-md-file-ok\n"
    client = TestClient(app)
    res = client.post(
        "/api/ingest-file",
        json={
            "name": "notes.md",
            "mime": "text/markdown",
            "data": base64.b64encode(raw).decode("ascii"),
            "destination": "file",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["saved"] is True
    path = Path(data["path"])
    assert path.name == "notes.md"
    assert path.parent == tmp_path / "Files"
    assert path.read_bytes() == raw


def test_ingest_file_copy_uses_file_clipboard(tmp_path: Path, monkeypatch) -> None:
    import base64

    from app import server as server_mod

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))
    held: list[str] = []
    monkeypatch.setattr(server_mod.clip, "set_files", lambda paths: held.extend(paths))
    raw = b"hello-file"
    client = TestClient(app)
    res = client.post(
        "/api/ingest-file",
        json={
            "name": "hello.txt",
            "mime": "text/plain",
            "data": base64.b64encode(raw).decode("ascii"),
            "destination": "clipboard",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["saved"] is False
    assert held
    assert Path(held[0]).read_bytes() == raw
