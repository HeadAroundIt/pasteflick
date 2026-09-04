"""Win32 focus + Ctrl+V paste (trimmed from Hush)."""

from __future__ import annotations

import ctypes
import re
import time
from ctypes import wintypes

from app import OVERLAY_TITLE

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GA_ROOT = 2
GW_OWNER = 4
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
SW_RESTORE = 9
ASFW_ANY = 0xFFFFFFFF
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

BROWSER_EXES = {
    "chrome.exe",
    "brave.exe",
    "msedge.exe",
    "firefox.exe",
    "chromium.exe",
    "arc.exe",
    "opera.exe",
    "vivaldi.exe",
}
CURSOR_EXES = {"cursor.exe"}
SKIP_PASTE_EXES = {
    "razerappengine.exe",
    "textinputhost.exe",
    "systemsettings.exe",
    "applicationframehost.exe",
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
}
_BROWSER_TITLE_RE = re.compile(
    r" - (google chrome|brave( beta)?|microsoft edge|chromium|mozilla firefox|arc)$",
    re.I,
)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL
user32.SwitchToThisWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
user32.SwitchToThisWindow.restype = None
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.SendInput.restype = wintypes.UINT
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
user32.keybd_event.restype = None
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]

if ctypes.sizeof(ctypes.c_void_p) == 8:
    _get_window_long = user32.GetWindowLongPtrW
else:
    _get_window_long = user32.GetWindowLongW
_get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
_get_window_long.restype = ctypes.c_ssize_t


def hwnd_to_int(hwnd: object) -> int:
    if not hwnd:
        return 0
    try:
        return int(hwnd)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def get_foreground() -> int:
    return hwnd_to_int(user32.GetForegroundWindow())


def toplevel_hwnd(hwnd: int) -> int:
    if not hwnd:
        return 0
    root = hwnd_to_int(user32.GetAncestor(hwnd, GA_ROOT))
    parent = hwnd_to_int(user32.GetParent(hwnd))
    return root or parent or int(hwnd)


def is_window(hwnd: int) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


def window_title(hwnd: int) -> str:
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def overlay_title_match(title: str, needle: str = OVERLAY_TITLE) -> bool:
    """Exact overlay title only — not an editor named 'PasteFlick - Cursor'."""
    return str(title or "").strip().lower() == str(needle or "").strip().lower()


def browser_title_match(title: str) -> bool:
    """True only when the title ends with a browser name, not 'architecture' or 'brave.ts'."""
    return bool(_BROWSER_TITLE_RE.search(str(title or "").strip()))


def window_exe_name(hwnd: int) -> str:
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        path = buf.value.replace("/", "\\")
        return path.rsplit("\\", 1)[-1]
    finally:
        kernel32.CloseHandle(handle)


def window_style(hwnd: int) -> int:
    if not hwnd:
        return 0
    return int(_get_window_long(hwnd, GWL_STYLE)) & 0xFFFFFFFF


def window_exstyle(hwnd: int) -> int:
    if not hwnd:
        return 0
    return int(_get_window_long(hwnd, GWL_EXSTYLE)) & 0xFFFFFFFF


def is_paste_app(hwnd: int) -> bool:
    """Real captioned app — not the tray, a Razer overlay, IME, or a browser."""
    if not hwnd or not is_window(hwnd):
        return False
    if not user32.IsWindowVisible(hwnd):
        return False
    if is_browser_hwnd(hwnd):
        return False
    if window_exe_name(hwnd).lower() in SKIP_PASTE_EXES:
        return False
    if not window_title(hwnd).strip():
        return False
    ex = window_exstyle(hwnd)
    if ex & WS_EX_TOOLWINDOW or ex & WS_EX_NOACTIVATE:
        return False
    if not (window_style(hwnd) & WS_CAPTION):
        return False
    return True


def find_hwnds_by_title(substr: str = OVERLAY_TITLE) -> set[int]:
    found: set[int] = set()

    @WNDENUMPROC
    def _enum(hwnd, _lparam):  # type: ignore[misc]
        handle = hwnd_to_int(hwnd)
        if not user32.IsWindowVisible(hwnd):
            return True
        if overlay_title_match(window_title(handle), substr):
            found.add(handle)
        return True

    user32.EnumWindows(_enum, 0)
    return found


def find_hwnds_containing(substr: str) -> set[int]:
    found: set[int] = set()
    needle = substr.lower()

    @WNDENUMPROC
    def _enum(hwnd, _lparam):  # type: ignore[misc]
        handle = hwnd_to_int(hwnd)
        if not user32.IsWindowVisible(hwnd):
            return True
        title = window_title(handle).lower()
        if needle in title:
            found.add(handle)
        return True

    user32.EnumWindows(_enum, 0)
    return found


def is_browser_hwnd(hwnd: int) -> bool:
    exe = window_exe_name(hwnd).lower()
    if exe in CURSOR_EXES:
        return False
    if exe in BROWSER_EXES:
        return True
    return browser_title_match(window_title(hwnd))


def find_last_app_hwnd(skip: set[int] | None = None) -> int:
    """Topmost visible app behind the browser — where Auto-paste should land."""
    skip = set(skip or ())
    found = 0

    @WNDENUMPROC
    def _enum(hwnd, _lparam):  # type: ignore[misc]
        nonlocal found
        handle = hwnd_to_int(hwnd)
        if not handle or not user32.IsWindowVisible(hwnd):
            return True
        if hwnd_to_int(user32.GetWindow(hwnd, GW_OWNER)):
            return True
        top = toplevel_hwnd(handle) or handle
        if top in skip or handle in skip:
            return True
        if not is_paste_app(top):
            return True
        found = top
        return False

    user32.EnumWindows(_enum, 0)
    return found


def find_cursor_hwnd() -> int:
    found = 0

    @WNDENUMPROC
    def _enum(hwnd, _lparam):  # type: ignore[misc]
        nonlocal found
        handle = hwnd_to_int(hwnd)
        if not handle or not is_paste_app(handle):
            return True
        if window_exe_name(handle).lower() not in CURSOR_EXES:
            return True
        found = toplevel_hwnd(handle) or handle
        return False

    user32.EnumWindows(_enum, 0)
    if found:
        return found
    for hwnd in find_hwnds_containing(" - cursor"):
        if is_window(hwnd) and is_paste_app(hwnd):
            return toplevel_hwnd(hwnd) or hwnd
    for hwnd in find_hwnds_containing("cursor"):
        title = window_title(hwnd)
        if title == "Cursor" or title.endswith(" - Cursor"):
            if is_window(hwnd) and is_paste_app(hwnd):
                return toplevel_hwnd(hwnd) or hwnd
    return 0


def _same_window(a: int, b: int) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    return toplevel_hwnd(a) == toplevel_hwnd(b)


def focus_window(hwnd: int) -> bool:
    hwnd = toplevel_hwnd(hwnd) or hwnd
    if not is_window(hwnd):
        return False
    if _same_window(get_foreground(), hwnd):
        return True
    try:
        user32.AllowSetForegroundWindow(ASFW_ANY)
    except Exception:
        pass
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    fg = get_foreground()
    cur_thread = kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)

    attached_fg = False
    attached_target = False
    if fg_thread and fg_thread != cur_thread:
        attached_fg = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
    if target_thread and target_thread != cur_thread and target_thread != fg_thread:
        attached_target = bool(user32.AttachThreadInput(cur_thread, target_thread, True))

    try:
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        try:
            user32.SwitchToThisWindow(hwnd, True)
        except Exception:
            pass
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    finally:
        if attached_target:
            user32.AttachThreadInput(cur_thread, target_thread, False)
        if attached_fg:
            user32.AttachThreadInput(cur_thread, fg_thread, False)

    for _ in range(8):
        if _same_window(get_foreground(), hwnd):
            return True
        time.sleep(0.02)
        user32.SetForegroundWindow(hwnd)
    return _same_window(get_foreground(), hwnd)


def _key_input(vk: int, up: bool = False) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = 0
    return inp


def paste_text() -> None:
    time.sleep(0.05)
    events = (INPUT * 4)(
        _key_input(VK_CONTROL),
        _key_input(VK_V),
        _key_input(VK_V, up=True),
        _key_input(VK_CONTROL, up=True),
    )
    sent = user32.SendInput(4, events, ctypes.sizeof(INPUT))
    if sent != 4:
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def paste_into(hwnd: int) -> bool:
    target = toplevel_hwnd(hwnd) or hwnd
    if not is_window(target):
        return False
    if not focus_window(target):
        return False
    paste_text()
    return True
