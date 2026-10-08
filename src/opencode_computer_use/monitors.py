"""Monitor enumeration + virtual desktop metrics via ctypes (no pywin32 needed).

Per-monitor DPI via shcore.GetDpiForMonitor, with WMI/fallback to 96.
Process is marked per-monitor-V2 DPI aware at import so all APIs return
physical pixels.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from .config import log
from .coords import MonitorInfo, VirtualDesktop

user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore if hasattr(ctypes.windll, "shcore") else None

try:
    # PROCESS_PER_MONITOR_DPI_AWARE = 2
    shcore.SetProcessDpiAwareness(2)  # type: ignore[union-attr]
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

MONITORINFOF_PRIMARY = 1
MDT_EFFECTIVE_DPI = 0


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
                ("szDevice", wintypes.WCHAR * 32)]


MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
    ctypes.POINTER(RECT), wintypes.LPARAM,
)


def get_virtual_desktop() -> VirtualDesktop:
    return VirtualDesktop(
        x=user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
        y=user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
        width=user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
        height=user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
    )


def _dpi_for_monitor(hmon: int) -> tuple[int, int]:
    if shcore is not None:
        try:
            dpi_x = wintypes.UINT()
            dpi_y = wintypes.UINT()
            hr = shcore.GetDpiForMonitor(
                wintypes.HMONITOR(hmon), MDT_EFFECTIVE_DPI,
                ctypes.byref(dpi_x), ctypes.byref(dpi_y),
            )
            if hr == 0 and dpi_x.value:
                return int(dpi_x.value), int(dpi_y.value)
        except Exception:
            pass
    return 96, 96


def list_monitors() -> list[MonitorInfo]:
    found: list[tuple[int, MONITORINFOEXW]] = []

    def _cb(hmon, hdc, rect, lparam):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            found.append((int(hmon), mi))
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_cb), 0)
    # Deterministic order: sort by x then y so ids are stable.
    found.sort(key=lambda t: (t[1].rcMonitor.left, t[1].rcMonitor.top))
    out: list[MonitorInfo] = []
    for idx, (hmon, mi) in enumerate(found):
        r = mi.rcMonitor
        dpi_x, dpi_y = _dpi_for_monitor(hmon)
        out.append(MonitorInfo(
            id=idx,
            name=mi.szDevice or f"Monitor{idx}",
            x=int(r.left), y=int(r.top),
            width=int(r.right - r.left), height=int(r.bottom - r.top),
            primary=bool(mi.dwFlags & MONITORINFOF_PRIMARY),
            scale=round(dpi_x / 96.0, 3),
            dpi_x=dpi_x, dpi_y=dpi_y,
        ))
    if not out:  # last-resort fallback
        w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        out.append(MonitorInfo(0, "Primary", 0, 0, w, h, True, 1.0, 96, 96))
    log.debug(f"monitors: {[(m.id, m.x, m.y, m.width, m.height, m.scale) for m in out]}")
    return out


def get_monitor(monitors: list[MonitorInfo], monitor_id: int) -> MonitorInfo:
    for m in monitors:
        if m.id == monitor_id:
            return m
    raise ValueError(f"unknown monitor id {monitor_id}; available: {[m.id for m in monitors]}")


def monitor_at_point(monitors: list[MonitorInfo], vx: int, vy: int) -> MonitorInfo | None:
    for m in monitors:
        if m.contains_point(vx, vy):
            return m
    return None
