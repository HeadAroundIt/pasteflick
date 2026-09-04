"""Native folder picker. Explorer-style on Windows, so Settings can choose a save folder."""

from __future__ import annotations

import os
from pathlib import Path


def pick_folder(initial: Path | str | None = None) -> Path | None:
    start = Path(initial) if initial else None
    if os.name == "nt":
        try:
            return _pick_win32(start)
        except OSError:
            pass
    try:
        return _pick_tk(start)
    except Exception:
        return None


def _pick_tk(initial: Path | None) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.wm_attributes("-topmost", True)
    except tk.TclError:
        pass
    start = str(initial) if initial and initial.is_dir() else str(Path.home() / "Documents")
    chosen = filedialog.askdirectory(
        parent=root,
        initialdir=start,
        title="Save copies to",
        mustexist=False,
    )
    root.destroy()
    return Path(chosen) if chosen else None


def _pick_win32(initial: Path | None) -> Path | None:
    import ctypes
    from ctypes import HRESULT, POINTER, WINFUNCTYPE, byref, c_void_p, c_wchar_p, c_ulong

    CLSCTX_INPROC_SERVER = 1
    COINIT_APARTMENTTHREADED = 0x2
    FOS_PICKFOLDERS = 0x20
    FOS_FORCEFILESYSTEM = 0x40
    SIGDN_FILESYSPATH = 0x80058000

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    ole32 = ctypes.WinDLL("ole32")
    shell32 = ctypes.WinDLL("shell32")
    ole32.CLSIDFromString.argtypes = [c_wchar_p, POINTER(GUID)]
    ole32.CLSIDFromString.restype = HRESULT
    ole32.CoInitializeEx.argtypes = [c_void_p, ctypes.c_ulong]
    ole32.CoInitializeEx.restype = HRESULT
    ole32.CoCreateInstance.argtypes = [POINTER(GUID), c_void_p, ctypes.c_ulong, POINTER(GUID), POINTER(c_void_p)]
    ole32.CoCreateInstance.restype = HRESULT
    ole32.CoTaskMemFree.argtypes = [c_void_p]
    ole32.CoTaskMemFree.restype = None
    shell32.SHCreateItemFromParsingName.argtypes = [c_wchar_p, c_void_p, POINTER(GUID), POINTER(c_void_p)]
    shell32.SHCreateItemFromParsingName.restype = HRESULT

    def guid(text: str) -> GUID:
        value = GUID()
        ole32.CLSIDFromString(text, byref(value))
        return value

    clsid = guid("{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}")
    iid_dialog = guid("{D57C7288-D4AD-4768-BE02-9D969532D960}")
    iid_item = guid("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")

    ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    dialog = c_void_p()
    created = ole32.CoCreateInstance(byref(clsid), None, CLSCTX_INPROC_SERVER, byref(iid_dialog), byref(dialog))
    if created != 0 or not dialog.value:
        raise OSError("folder dialog unavailable")

    vtbl = ctypes.cast(dialog, POINTER(POINTER(c_void_p))).contents

    def call(index, restype, *argtypes):
        return WINFUNCTYPE(restype, c_void_p, *argtypes)(vtbl[index])

    set_options = call(9, HRESULT, c_ulong)
    set_title = call(17, HRESULT, c_wchar_p)
    set_folder = call(12, HRESULT, c_void_p)
    show = call(3, HRESULT, c_void_p)
    get_result = call(20, HRESULT, POINTER(c_void_p))
    release_dialog = call(2, c_ulong)

    set_options(dialog, FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM)
    set_title(dialog, "Save copies to")

    folder_item = c_void_p()
    start = initial if initial and initial.is_dir() else None
    if start:
        if shell32.SHCreateItemFromParsingName(str(start), None, byref(iid_item), byref(folder_item)) == 0:
            set_folder(dialog, folder_item)

    user32 = ctypes.WinDLL("user32")
    hwnd = user32.GetForegroundWindow()
    shown = show(dialog, hwnd)
    path: Path | None = None
    if shown == 0:
        result = c_void_p()
        if get_result(dialog, byref(result)) == 0 and result.value:
            item_vtbl = ctypes.cast(result, POINTER(POINTER(c_void_p))).contents
            get_name = WINFUNCTYPE(HRESULT, c_void_p, c_ulong, POINTER(c_void_p))(item_vtbl[5])
            release_item = WINFUNCTYPE(c_ulong, c_void_p)(item_vtbl[2])
            raw = c_void_p()
            if get_name(result, SIGDN_FILESYSPATH, byref(raw)) == 0 and raw.value:
                path = Path(ctypes.wstring_at(raw))
                ole32.CoTaskMemFree(raw)
            release_item(result)

    if folder_item.value:
        item_vtbl = ctypes.cast(folder_item, POINTER(POINTER(c_void_p))).contents
        WINFUNCTYPE(c_ulong, c_void_p)(item_vtbl[2])(folder_item)
    release_dialog(dialog)

    code = shown & 0xFFFFFFFF
    if code == 0:
        return path
    if code == 0x800704C7:
        return None
    raise OSError("folder dialog failed")
