"""Window enumeration + focus/minimize/maximize/restore via ctypes."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from .config import log

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
SW_SHOW = 5

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]


def _title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    n = user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value if n else ""


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    n = user32.GetClassNameW(hwnd, buf, 256)
    return buf.value if n else ""


def _pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _process_name(pid: int) -> str:
    try:
        import ctypes as _c
        PROCESS_QUERY_LIMITED = 0x1000
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if not h:
            return ""
        try:
            buf = _c.create_unicode_buffer(512)
            size = wintypes.DWORD(512)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return buf.value.split("\\")[-1]
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        pass
    return ""


def list_windows(limit: int = 50) -> list[dict]:
    out: list[dict] = []

    def _cb(hwnd, _lp):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            title = _title(hwnd)
            if not title.strip():
                return True
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if w <= 0 or h <= 0:
                return True
            pid = _pid(hwnd)
            out.append({
                "hwnd": int(hwnd),
                "title": title,
                "process": _process_name(pid),
                "pid": pid,
                "x": int(rect.left), "y": int(rect.top),
                "width": int(w), "height": int(h),
                "is_active": int(hwnd) == int(user32.GetForegroundWindow()),
                "class": _class_name(hwnd),
            })
        except Exception:
            pass
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    out.sort(key=lambda w: (not w["is_active"], w["title"].lower()))
    log.info(f"Window list ({len(out)} visible)")
    return out[: max(1, limit)]


def get_active_window() -> dict | None:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    title = _title(hwnd)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    pid = _pid(hwnd)
    return {
        "hwnd": int(hwnd), "title": title,
        "process": _process_name(pid), "pid": pid,
        "x": int(rect.left), "y": int(rect.top),
        "width": int(rect.right - rect.left),
        "height": int(rect.bottom - rect.top),
        "is_active": True, "class": _class_name(hwnd),
    }


def _find_window(hwnd_or_title) -> int | None:
    if isinstance(hwnd_or_title, int) and hwnd_or_title:
        return hwnd_or_title if user32.IsWindow(hwnd_or_title) else None
    needle = str(hwnd_or_title).lower()
    best = None
    for w in list_windows(limit=200):
        if needle in w["title"].lower():
            best = w["hwnd"]
            if w["title"].lower() == needle:
                break
    return best


def focus_window(hwnd_or_title) -> dict:
    hwnd = _find_window(hwnd_or_title)
    if not hwnd:
        raise ValueError(f"window not found: {hwnd_or_title!r}")
    # Restore if minimized, then foreground.
    user32.ShowWindow(hwnd, SW_RESTORE)
    # Best-effort foreground (may be restricted by Windows focus policy).
    user32.SetForegroundWindow(hwnd)
    import time
    time.sleep(0.15)
    active = get_active_window()
    log.info(f"Window focused: {active['title'] if active else hwnd}")
    return {"hwnd": hwnd, "focused": bool(active and active['hwnd'] == hwnd),
            "active": active}


def set_window_state(hwnd_or_title, state: str) -> dict:
    hwnd = _find_window(hwnd_or_title)
    if not hwnd:
        raise ValueError(f"window not found: {hwnd_or_title!r}")
    code = {"minimize": SW_MINIMIZE, "maximize": SW_MAXIMIZE,
            "restore": SW_RESTORE, "show": SW_SHOW}[state]
    user32.ShowWindow(hwnd, code)
    log.info(f"Window {state}: hwnd={hwnd}")
    return {"hwnd": hwnd, "state": state}


def window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    if not user32.IsWindow(hwnd):
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return int(rect.left), int(rect.top), int(rect.right - rect.left), int(rect.bottom - rect.top)
