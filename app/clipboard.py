"""Windows clipboard helpers (pattern from Hush; no Tk)."""

from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_UNICODETEXT = 13
CF_HDROP = 15
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalSize.argtypes = [wintypes.HANDLE]
kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
kernel32.GlobalFree.restype = wintypes.HANDLE

user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wintypes.UINT


class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]


def _last_error() -> int:
    return int(ctypes.get_last_error())


def _open_clipboard(retries: int = 8) -> None:
    for attempt in range(retries):
        if user32.OpenClipboard(None):
            return
        time.sleep(0.02 * (attempt + 1))
    raise OSError(f"OpenClipboard failed ({_last_error()})")


def set_text(text: str) -> None:
    data = text.encode("utf-16-le") + b"\x00\x00"
    _open_clipboard()
    handle = None
    owned = False
    try:
        if not user32.EmptyClipboard():
            raise OSError(f"EmptyClipboard failed ({_last_error()})")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            raise OSError(f"GlobalAlloc failed ({_last_error()})")
        locked = kernel32.GlobalLock(handle)
        if not locked:
            raise OSError(f"GlobalLock failed ({_last_error()})")
        try:
            ctypes.memmove(locked, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise OSError(f"SetClipboardData failed ({_last_error()})")
        owned = True
    finally:
        if handle and not owned:
            kernel32.GlobalFree(handle)
        user32.CloseClipboard()


def get_text() -> str:
    try:
        _open_clipboard()
    except OSError:
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        locked = kernel32.GlobalLock(handle)
        if not locked:
            return ""
        try:
            size = kernel32.GlobalSize(handle)
            raw = ctypes.string_at(locked, size)
        finally:
            kernel32.GlobalUnlock(handle)
        return raw.decode("utf-16-le", errors="ignore").rstrip("\x00")
    finally:
        user32.CloseClipboard()


def _set_handle(fmt: int, data: bytes) -> None:
    handle = kernel32.GlobalAlloc(GHND, len(data))
    if not handle:
        raise OSError(f"GlobalAlloc failed ({_last_error()})")
    locked = kernel32.GlobalLock(handle)
    if not locked:
        kernel32.GlobalFree(handle)
        raise OSError(f"GlobalLock failed ({_last_error()})")
    try:
        ctypes.memmove(locked, data, len(data))
    finally:
        kernel32.GlobalUnlock(handle)
    if not user32.SetClipboardData(fmt, handle):
        kernel32.GlobalFree(handle)
        raise OSError(f"SetClipboardData failed ({_last_error()})")


def set_files(paths: list[str]) -> None:
    """Put real files on the clipboard so paste/drop can attach them.

    Do not also put the filename as Unicode text — editors paste that string
    instead of the file. Do not use Set-Clipboard -LiteralPath: it often adds
    a text fallback of the name.
    """
    names = [str(Path(p).resolve()) for p in paths if str(p).strip()]
    if not names:
        raise OSError("No file to copy")
    for name in names:
        if not Path(name).is_file():
            raise OSError("No file to copy")
    try:
        _set_files_native(names)
        return
    except OSError:
        pass
    if _set_files_powershell(names):
        return
    _set_files_hdrop(names)


def _ps_literal(path: str) -> str:
    return "'" + path.replace("'", "''") + "'"


def _set_files_powershell(paths: list[str]) -> bool:
    joined = ",".join(_ps_literal(p) for p in paths)
    cmd = (
        "Set-Clipboard -LiteralPath @(" + joined + ")"
        if len(paths) > 1
        else "Set-Clipboard -LiteralPath " + _ps_literal(paths[0])
    )
    try:
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-WindowStyle",
                "Hidden",
                "-Command",
                cmd,
            ],
            capture_output=True,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False


def _hdrop_blob(paths: list[str]) -> bytes:
    payload = ("\0".join(paths) + "\0\0").encode("utf-16-le")
    header = DROPFILES()
    header.pFiles = ctypes.sizeof(DROPFILES)
    header.fWide = True
    return bytes(header) + payload


FD_ATTRIBUTES = 0x00000004
FD_FILESIZE = 0x00000040
FILE_ATTRIBUTE_NORMAL = 0x00000080
MAX_PATH = 260
DROPEFFECT_COPY = 1


class FILEDESCRIPTORW(ctypes.Structure):
    _fields_ = [
        ("dwFlags", wintypes.DWORD),
        ("clsid", ctypes.c_ubyte * 16),
        ("sizel_cx", wintypes.LONG),
        ("sizel_cy", wintypes.LONG),
        ("pointl_x", wintypes.LONG),
        ("pointl_y", wintypes.LONG),
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("cFileName", wintypes.WCHAR * MAX_PATH),
    ]


def _file_group_descriptor(path: str, size: int) -> bytes:
    desc = FILEDESCRIPTORW()
    desc.dwFlags = FD_ATTRIBUTES | FD_FILESIZE
    desc.dwFileAttributes = FILE_ATTRIBUTE_NORMAL
    desc.nFileSizeHigh = (size >> 32) & 0xFFFFFFFF
    desc.nFileSizeLow = size & 0xFFFFFFFF
    desc.cFileName = Path(path).name[: MAX_PATH - 1]
    return ctypes.c_uint32(1).value.to_bytes(4, "little") + bytes(desc)


def _set_files_native(paths: list[str]) -> None:
    payloads = [Path(p).read_bytes() for p in paths]
    _open_clipboard()
    try:
        if not user32.EmptyClipboard():
            raise OSError(f"EmptyClipboard failed ({_last_error()})")
        _set_handle(CF_HDROP, _hdrop_blob(paths))
        effect = user32.RegisterClipboardFormatW("Preferred DropEffect")
        if effect:
            _set_handle(effect, DROPEFFECT_COPY.to_bytes(4, "little"))
        if len(paths) == 1:
            desc = user32.RegisterClipboardFormatW("FileGroupDescriptorW")
            contents = user32.RegisterClipboardFormatW("FileContents")
            if desc and contents:
                raw = payloads[0]
                _set_handle(desc, _file_group_descriptor(paths[0], len(raw)))
                _set_handle(contents, raw if raw else b"\x00")
    finally:
        user32.CloseClipboard()


def _set_files_hdrop(paths: list[str]) -> None:
    _open_clipboard()
    try:
        if not user32.EmptyClipboard():
            raise OSError(f"EmptyClipboard failed ({_last_error()})")
        _set_handle(CF_HDROP, _hdrop_blob(paths))
    finally:
        user32.CloseClipboard()


def set_png(data: bytes) -> None:
    if not data:
        raise OSError("No image to copy")
    fmt = user32.RegisterClipboardFormatW("PNG")
    if not fmt:
        raise OSError("PNG clipboard format unavailable")
    _open_clipboard()
    try:
        if not user32.EmptyClipboard():
            raise OSError(f"EmptyClipboard failed ({_last_error()})")
        _set_handle(fmt, data)
    finally:
        user32.CloseClipboard()
