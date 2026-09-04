"""Write transcripts to Markdown or a simple text PDF."""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def _appdata_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "PasteFlick"
    return Path.home() / ".pasteflick"


def default_output_root() -> Path:
    return Path.home() / "Documents" / "PasteFlick"


def default_export_dir() -> Path:
    return default_output_root() / "Exports"


def default_files_dir() -> Path:
    return default_output_root() / "Files"


def settings_path() -> Path:
    return _appdata_root() / "settings.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def save_settings(data: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def normalize_output_root(path: Path | str) -> Path:
    out = Path(path).expanduser()
    if out.name.lower() in {"exports", "files"}:
        out = out.parent
    return out


def get_output_root() -> Path:
    env = (os.environ.get("PASTEFLICK_EXPORT_DIR") or "").strip()
    if env:
        return normalize_output_root(env)
    with _lock:
        raw = str(load_settings().get("export_dir") or "").strip()
    return normalize_output_root(raw) if raw else default_output_root()


def get_export_dir() -> Path:
    return get_output_root() / "Exports"


def get_files_dir() -> Path:
    return get_output_root() / "Files"


def set_export_dir(path: Path | str) -> Path:
    out = normalize_output_root(path)
    out.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    with _lock:
        data = load_settings()
        data["export_dir"] = str(out)
        save_settings(data)
    return out


def get_export_format() -> str:
    with _lock:
        raw = str(load_settings().get("export_format") or "md").strip().lower().lstrip(".")
    return "pdf" if raw == "pdf" else "md"


def set_export_format(fmt: str) -> str:
    value = "pdf" if str(fmt).strip().lower().lstrip(".") == "pdf" else "md"
    with _lock:
        data = load_settings()
        data["export_format"] = value
        save_settings(data)
    return value


def export_settings() -> dict[str, Any]:
    root = get_output_root()
    return {
        "dir": str(root),
        "exists": root.is_dir(),
        "default": str(default_output_root()),
        "exports_dir": str(get_export_dir()),
        "files_dir": str(get_files_dir()),
        "format": get_export_format(),
    }


def safe_filename(title: str) -> str:
    raw = (title or "transcript").strip() or "transcript"
    cleaned = "".join(c if c.isalnum() or c in "._- " else "_" for c in raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return (cleaned or "transcript")[:80]


def export_transcript(markdown: str, *, title: str = "", fmt: str = "md") -> Path:
    folder = get_export_dir()
    folder.mkdir(parents=True, exist_ok=True)
    ext = "pdf" if str(fmt).lower().lstrip(".") == "pdf" else "md"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{safe_filename(title)}-{stamp}"
    path = folder / f"{base}.{ext}"
    n = 2
    while path.exists():
        path = folder / f"{base}-{n}.{ext}"
        n += 1
    write_file(path, markdown or "", title=title)
    return path


def write_file(path: Path, markdown: str, *, title: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".pdf":
        write_pdf(markdown, path, title=title)
        return
    if not path.suffix:
        path = path.with_suffix(".md")
    path.write_text(markdown or "", encoding="utf-8")


def keep_filename(name: str, mime: str = "") -> str:
    raw = Path(str(name or "file")).name.strip() or "file"
    cleaned = "".join(c if c.isalnum() or c in "._- " else "_" for c in raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._") or "file"
    cleaned = cleaned[:120]
    if "." not in cleaned:
        ext = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "application/zip": ".zip",
            "text/markdown": ".md",
            "text/x-markdown": ".md",
            "text/plain": ".txt",
            "application/json": ".json",
        }.get(str(mime or "").split(";")[0].strip().lower(), "")
        cleaned += ext
    return cleaned


def uniquify_name(folder: Path, name: str) -> Path:
    path = folder / name
    if not path.exists():
        return path
    stem, suf = path.stem, path.suffix
    n = 2
    while True:
        cand = folder / f"{stem}-{n}{suf}"
        if not cand.exists():
            return cand
        n += 1


def export_bytes(data: bytes, *, name: str, mime: str = "") -> Path:
    folder = get_files_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = uniquify_name(folder, keep_filename(name, mime))
    path.write_bytes(data or b"")
    return path


def staging_file(data: bytes, *, name: str, mime: str = "") -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        folder = _appdata_root() / "drop"
    else:
        folder = Path(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp") / "PasteFlick"
    folder.mkdir(parents=True, exist_ok=True)
    path = uniquify_name(folder, keep_filename(name, mime))
    path.write_bytes(data or b"")
    return path


def _pdf_font_paths() -> list[Path]:
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"
    fonts = Path(windir) / "Fonts"
    candidates = [
        fonts / "arialuni.ttf",
        fonts / "ARIALUNI.TTF",
        fonts / "msyh.ttf",
        fonts / "malgun.ttf",
        fonts / "segoeui.ttf",
        fonts / "arial.ttf",
        fonts / "calibri.ttf",
        fonts / "tahoma.ttf",
        fonts / "msyh.ttc",
        fonts / "YuGothR.ttc",
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    found: list[Path] = []
    for path in candidates:
        if path.is_file() and path not in found:
            found.append(path)
    return found


def write_pdf(text: str, path: Path, *, title: str = "") -> None:
    from fpdf import FPDF

    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    path.parent.mkdir(parents=True, exist_ok=True)

    for font in _pdf_font_paths():
        try:
            pdf = FPDF(format="letter", unit="pt")
            pdf.set_title(title or "Transcript")
            pdf.set_creator("PasteFlick")
            pdf.set_producer("PasteFlick")
            pdf.set_margins(72, 72, 72)
            pdf.set_auto_page_break(auto=True, margin=72)
            pdf.add_page()
            pdf.add_font("PasteFlick", fname=str(font))
            pdf.set_font("PasteFlick", size=11)
            pdf.multi_cell(w=0, h=16, text=body or " ")
            pdf.output(str(path))
            return
        except Exception:
            continue

    pdf = FPDF(format="letter", unit="pt")
    pdf.set_title(title or "Transcript")
    pdf.set_creator("PasteFlick")
    pdf.set_producer("PasteFlick")
    pdf.set_margins(72, 72, 72)
    pdf.set_auto_page_break(auto=True, margin=72)
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    pdf.multi_cell(w=0, h=16, text=body.encode("latin-1", "replace").decode("latin-1") or " ")
    pdf.output(str(path))
