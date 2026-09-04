"""FastAPI server for the overlay + extension ingest."""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app import DEFAULT_PORT, OVERLAY_TITLE, __version__
from app import clipboard as clip
from app import export as files
from app import window as win
from app.state import TranscriptState

ROOT = Path(__file__).resolve().parent.parent
UI_DIST = ROOT / "ui" / "dist"

state = TranscriptState()
app = FastAPI(title="PasteFlick")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chatgpt.com",
        "https://chat.openai.com",
        "http://127.0.0.1:8768",
        "http://localhost:8768",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8769",
        "http://localhost:8769",
    ],
    allow_origin_regex=r"^(chrome-extension://.*|http://(127\.0\.0\.1|localhost):\d+)$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith("/api/"):
        from app.update import default_install_root, read_api_token

        installed = default_install_root()
        token_root = installed if os.environ.get("PASTEFLICK_ROOT") or ROOT.resolve() == installed.resolve() else ROOT
        expected = read_api_token(token_root)
        provided = request.headers.get("x-pasteflick-token", "")
        if expected and not hmac.compare_digest(provided, expected):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)

_loop: asyncio.AbstractEventLoop | None = None
_clients: set[WebSocket] = set()
_lock = threading.Lock()
_pick_lock = threading.Lock()


class IngestBody(BaseModel):
    title: str = ""
    markdown: str
    url: str = ""
    source: str = "selection"
    partial: bool = False
    turn_count: int = 0
    character_count: int = 0
    copy_to_clipboard: bool = True
    auto_paste: bool = False
    save: bool = False
    destination: str = ""
    format: str = "md"


class ExportDirBody(BaseModel):
    path: str | None = None


class FormatBody(BaseModel):
    format: str = "md"


class SaveBody(BaseModel):
    format: str | None = None
    markdown: str | None = None
    title: str | None = None


class TranscriptBody(BaseModel):
    markdown: str = ""


class FileIngestBody(BaseModel):
    name: str = "file"
    mime: str = ""
    data: str = ""
    destination: str = "clipboard"


class TextBody(BaseModel):
    text: str | None = None


def _broadcast(snapshot: dict[str, Any]) -> None:
    loop = _loop
    if loop is None:
        return
    payload = json.dumps(snapshot)

    async def _send_all() -> None:
        dead: list[WebSocket] = []
        with _lock:
            clients = list(_clients)
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            with _lock:
                for ws in dead:
                    _clients.discard(ws)

    asyncio.run_coroutine_threadsafe(_send_all(), loop)


@app.on_event("startup")
async def _on_startup() -> None:
    global _loop
    _loop = asyncio.get_running_loop()


@app.get("/api/health")
def health() -> dict[str, Any]:
    from app.update import read_manifest_version, status_dict

    status = status_dict()
    return {
        "ok": True,
        "port": DEFAULT_PORT,
        "app": "pasteflick",
        "version": read_manifest_version(ROOT) or __version__,
        "sha": status.get("sha") or "",
    }


@app.get("/api/update-status")
def update_status() -> dict[str, Any]:
    from app.update import status_dict

    return status_dict()


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    return state.snapshot()


def _destination(body: IngestBody) -> str:
    dest = (body.destination or "").strip().lower()
    if dest in {"clipboard", "cursor", "file"}:
        return dest
    if body.save:
        return "file"
    if body.auto_paste:
        return "cursor"
    return "clipboard"


def _export_format(raw: str | None) -> str:
    if raw is None or not str(raw).strip():
        return files.get_export_format()
    value = str(raw).strip().lower().lstrip(".")
    return "pdf" if value == "pdf" else "md"


def _pick_folder(current: Path) -> Path | None:
    from app.folderpick import pick_folder

    start = current if current.is_dir() else files.default_export_dir()
    return pick_folder(start)


def _is_ours(hwnd: int, ours: set[int]) -> bool:
    if not hwnd:
        return True
    if hwnd in ours:
        return True
    top = win.toplevel_hwnd(hwnd) or hwnd
    return top in ours


def _usable_target(hwnd: int, ours: set[int]) -> bool:
    """Last app is fine; the chat browser is not — paste must not bounce back into ChatGPT."""
    if not hwnd or not win.is_window(hwnd) or _is_ours(hwnd, ours):
        return False
    if not win.is_paste_app(hwnd):
        return False
    top = win.toplevel_hwnd(hwnd) or hwnd
    if top != hwnd and (not win.is_window(top) or _is_ours(top, ours) or not win.is_paste_app(top)):
        return False
    return True


def overlay_is_up() -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{DEFAULT_PORT}/api/health", timeout=0.4) as res:
            data = json.loads(res.read().decode())
        return data.get("app") in {"pasteflick", "transtrip-copier"}
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return False


def remember_foreground() -> None:
    """Keep the last non-browser app, the same way Hush tracks the caret target."""
    ours = win.find_hwnds_by_title(OVERLAY_TITLE)
    fg = win.get_foreground()
    if _usable_target(fg, ours):
        state.remember_target(win.toplevel_hwnd(fg) or fg)


def _paste_target() -> int:
    ours = win.find_hwnds_by_title(OVERLAY_TITLE)
    remembered = state.pop_target()
    if _usable_target(remembered, ours):
        return win.toplevel_hwnd(remembered) or remembered
    last = win.find_last_app_hwnd(ours)
    if last and _usable_target(last, ours):
        return win.toplevel_hwnd(last) or last
    cursor = win.find_cursor_hwnd()
    if cursor and not _is_ours(cursor, ours):
        return win.toplevel_hwnd(cursor) or cursor
    fg = win.get_foreground()
    if _usable_target(fg, ours):
        return win.toplevel_hwnd(fg) or fg
    return 0


def _paste_now(text: str) -> bool:
    try:
        clip.set_text(text)
    except OSError:
        return False
    return _paste_keys()


def _paste_keys() -> bool:
    target = _paste_target()
    if not target:
        return False
    return bool(win.paste_into(target))


@app.post("/api/ingest")
def ingest(body: IngestBody) -> dict[str, Any]:
    remember_foreground()

    payload = body.model_dump()
    if not payload.get("character_count"):
        payload["character_count"] = len(body.markdown)
    snap = state.apply_payload(payload)
    if body.copy_to_clipboard and body.markdown:
        try:
            clip.set_text(body.markdown)
            state.set_status(snap["status"] + " · clipboard updated")
            snap = state.snapshot()
        except OSError as exc:
            state.set_status(f"Ingested, clipboard failed: {exc}")
            snap = state.snapshot()
    dest = _destination(body)
    pasted = False
    saved = False
    saved_path = ""
    if dest == "cursor" and body.markdown:
        pasted = _paste_now(body.markdown)
        state.set_status("Pasted into last app" if pasted else "Copied — couldn't paste into last app")
        snap = state.snapshot()
    elif dest == "file" and body.markdown:
        try:
            out = files.export_transcript(
                body.markdown,
                title=body.title or snap.get("title") or "transcript",
                fmt=_export_format(body.format),
            )
            saved = True
            saved_path = str(out)
            state.set_status(f"Saved {out.name}")
            snap = state.snapshot()
        except OSError as exc:
            state.set_status(f"Couldn't save: {exc}")
            snap = state.snapshot()
    _broadcast(snap)
    return {**snap, "pasted": pasted, "saved": saved, "path": saved_path, "destination": dest}


@app.post("/api/ingest-file")
def ingest_file(body: FileIngestBody) -> dict[str, Any]:
    remember_foreground()
    dest = body.destination if body.destination in {"clipboard", "cursor", "file"} else "clipboard"
    try:
        raw = base64.b64decode(body.data or "", validate=False)
    except Exception as exc:
        raise HTTPException(400, "Couldn't read that file") from exc
    if not raw:
        raise HTTPException(400, "That file was empty")
    name = files.keep_filename(body.name, body.mime)
    mime = str(body.mime or "").split(";")[0].strip().lower()
    pasted = False
    saved = False
    saved_path = ""
    try:
        if dest == "file":
            out = files.export_bytes(raw, name=name, mime=mime)
            saved = True
            saved_path = str(out)
            state.set_status(f"Saved {out.name}")
        else:
            staged = files.staging_file(raw, name=name, mime=mime)
            clip.set_files([str(staged)])
            saved_path = str(staged)
            if dest == "cursor":
                time.sleep(0.15)
                pasted = _paste_keys()
                state.set_status(
                    "Sent file into last app" if pasted else "File copied. Couldn't paste into the last app."
                )
            else:
                state.set_status(f"Copied {staged.name}")
    except OSError as exc:
        state.set_status(f"Couldn't handle that file: {exc}")
        snap = state.snapshot()
        _broadcast(snap)
        return {**snap, "ok": False, "pasted": False, "saved": False, "path": "", "destination": dest}
    snap = state.snapshot()
    _broadcast(snap)
    return {
        **snap,
        "ok": True,
        "pasted": pasted,
        "saved": saved,
        "path": saved_path,
        "destination": dest,
        "title": name,
    }


@app.post("/api/transcript")
def set_transcript(body: TranscriptBody) -> dict[str, Any]:
    snap = state.set_markdown(body.markdown, status="Edited")
    _broadcast(snap)
    return snap


@app.post("/api/copy")
def copy_transcript(body: TextBody | None = None) -> dict[str, Any]:
    text = body.text if body and body.text is not None else None
    if text is None:
        text = state.snapshot()["markdown"]
    if not text:
        raise HTTPException(400, "Nothing to copy")
    try:
        clip.set_text(text)
    except OSError as exc:
        raise HTTPException(500, str(exc)) from exc
    if body and body.text is not None:
        snap = state.set_markdown(text, status="Copied")
    else:
        state.set_status("Copied")
        snap = state.snapshot()
    _broadcast(snap)
    return snap


@app.post("/api/paste")
def paste_transcript(body: TextBody | None = None) -> dict[str, Any]:
    text = body.text if body and body.text is not None else None
    if text is None:
        text = state.snapshot()["markdown"]
    if not text:
        raise HTTPException(400, "Nothing to paste")
    try:
        clip.set_text(text)
    except OSError as exc:
        raise HTTPException(500, str(exc)) from exc

    ok = _paste_now(text)
    if not ok:
        state.set_status("Clipboard set — click the last app and press Ctrl+V")
        snap = state.snapshot()
        _broadcast(snap)
        return {**snap, "pasted": False}

    if body and body.text is not None:
        snap = state.set_markdown(text, status="Pasted")
    else:
        state.set_status("Pasted")
        snap = state.snapshot()
    _broadcast(snap)
    return {**snap, "pasted": ok}


@app.post("/api/clear")
def clear_transcript() -> dict[str, Any]:
    snap = state.clear()
    _broadcast(snap)
    return snap


@app.get("/api/export-settings")
def get_export_settings() -> dict[str, Any]:
    return files.export_settings()


@app.post("/api/export-dir")
def set_export_directory(body: ExportDirBody | None = None) -> dict[str, Any]:
    raw = (body.path if body else None) or ""
    if raw.strip():
        folder = files.set_export_dir(raw.strip())
        return {**files.export_settings(), "picked": True, "dir": str(folder)}
    if not _pick_lock.acquire(blocking=False):
        return {**files.export_settings(), "picked": False, "busy": True}
    try:
        picked = _pick_folder(files.get_output_root())
        if picked is None:
            return {**files.export_settings(), "picked": False}
        folder = files.set_export_dir(picked)
        return {**files.export_settings(), "picked": True, "dir": str(folder)}
    finally:
        _pick_lock.release()


@app.post("/api/export-format")
def set_export_format(body: FormatBody | None = None) -> dict[str, Any]:
    raw = body.format if body else None
    fmt = "pdf" if str(raw or "").strip().lower().lstrip(".") == "pdf" else "md"
    files.set_export_format(fmt)
    return files.export_settings()


@app.post("/api/save")
def save_markdown(body: SaveBody | None = None) -> dict[str, Any]:
    snap = state.snapshot()
    text = body.markdown if body and body.markdown is not None else snap["markdown"]
    if not text:
        raise HTTPException(400, "Nothing to save")
    try:
        import webview
    except ImportError as exc:
        raise HTTPException(500, "webview not available") from exc

    windows = getattr(webview, "windows", None) or []
    window = windows[0] if windows else None
    if window is None:
        raise HTTPException(500, "No webview window")

    suggested = (body.title if body and body.title else None) or snap.get("title") or "transcript"
    safe = files.safe_filename(str(suggested))
    fmt = _export_format(body.format if body else None)
    path = window.create_file_dialog(
        webview.SAVE_DIALOG,
        directory=str(files.get_export_dir()),
        save_filename=f"{safe}.{fmt}",
        file_types=("Markdown (*.md)", "PDF (*.pdf)"),
    )
    if not path:
        return {**snap, "saved": False}
    out = Path(path if isinstance(path, str) else path[0])
    if out.suffix.lower() not in {".md", ".pdf"}:
        out = out.with_suffix(".pdf" if fmt == "pdf" else ".md")
    files.write_file(out, text, title=str(suggested))
    state.set_status(f"Saved {out.name}")
    snap = state.snapshot()
    _broadcast(snap)
    return {**snap, "saved": True, "path": str(out)}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    with _lock:
        _clients.add(ws)
    try:
        await ws.send_text(json.dumps(state.snapshot()))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with _lock:
            _clients.discard(ws)


def mount_ui() -> None:
    @app.get("/")
    def index() -> FileResponse:
        index_path = UI_DIST / "index.html"
        if not index_path.is_file():
            raise HTTPException(404, "UI not built")
        return FileResponse(index_path)

    @app.get("/assets/{rest:path}")
    def ui_asset(rest: str) -> FileResponse:
        assets = (UI_DIST / "assets").resolve()
        path = (assets / rest).resolve()
        try:
            path.relative_to(assets)
        except ValueError as exc:
            raise HTTPException(404) from exc
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)


mount_ui()
