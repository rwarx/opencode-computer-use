"""DPI-correct mouse via SendInput with VIRTUALDESK|ABSOLUTE.

Why not PyAutoGUI: PyAutoGUI breaks on mixed-DPI multi-monitor setups
(asweigart/pyautogui#413, pywinauto#1281) because it assumes uniform scaling.
We compute absolute units from the real virtual-desktop rect ourselves.
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from .config import log
from .coords import VirtualDesktop
from .monitors import get_virtual_desktop

user32 = ctypes.windll.user32

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_MOVE_NOCOALESCE = 0x2000
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
WHEEL_DELTA = 120


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]


BUTTONS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def _send(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
    inp = INPUT(type=INPUT_MOUSE,
                mi=MOUSEINPUT(dx=dx, dy=dy, mouseData=data, dwFlags=flags,
                              time=0, dwExtraInfo=None))
    n = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    if n != 1:
        raise RuntimeError(f"SendInput failed (sent {n}) err={ctypes.GetLastError()}")


def to_absolute(vx: int, vy: int, vdesk: VirtualDesktop | None = None) -> tuple[int, int]:
    from .coords import virtual_to_abs
    vdesk = vdesk or get_virtual_desktop()
    return virtual_to_abs(vx, vy, vdesk)


def move_to(vx: int, vy: int) -> None:
    ax, ay = to_absolute(vx, vy)
    _send(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, ax, ay)
    log.info(f"Mouse move x={vx} y={vy}")


def click_at(vx: int, vy: int, button: str = "left") -> None:
    button = button.lower()
    if button not in BUTTONS:
        raise ValueError(f"button must be one of {sorted(BUTTONS)}")
    down, up = BUTTONS[button]
    ax, ay = to_absolute(vx, vy)
    base = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    _send(MOUSEEVENTF_MOVE | base, ax, ay)
    time.sleep(0.02)
    _send(down | base, ax, ay)
    time.sleep(0.03)
    _send(up | base, ax, ay)
    log.info(f"Mouse click x={vx} y={vy} button={button}")


def double_click_at(vx: int, vy: int, button: str = "left") -> None:
    click_at(vx, vy, button)
    time.sleep(0.08)
    click_at(vx, vy, button)
    log.info(f"Mouse double-click x={vx} y={vy} button={button}")


def button_down(button: str = "left") -> None:
    button = button.lower()
    if button not in BUTTONS:
        raise ValueError(f"button must be one of {sorted(BUTTONS)}")
    pos = position()
    ax, ay = to_absolute(*pos)
    _send(BUTTONS[button][0] | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, ax, ay)
    log.info(f"Mouse down button={button}")


def button_up(button: str = "left") -> None:
    button = button.lower()
    if button not in BUTTONS:
        raise ValueError(f"button must be one of {sorted(BUTTONS)}")
    pos = position()
    ax, ay = to_absolute(*pos)
    _send(BUTTONS[button][1] | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, ax, ay)
    log.info(f"Mouse up button={button}")


def drag(from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left",
         steps: int = 12, step_delay: float = 0.008) -> None:
    button = button.lower()
    if button not in BUTTONS:
        raise ValueError(f"button must be one of {sorted(BUTTONS)}")
    down, up = BUTTONS[button]
    base = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    vdesk = get_virtual_desktop()
    ax0, ay0 = to_absolute(from_x, from_y, vdesk)
    _send(MOUSEEVENTF_MOVE | base, ax0, ay0)
    time.sleep(0.03)
    _send(down | base, ax0, ay0)
    time.sleep(0.05)
    for i in range(1, steps + 1):
        ix = from_x + (to_x - from_x) * i // steps
        iy = from_y + (to_y - from_y) * i // steps
        ax, ay = to_absolute(ix, iy, vdesk)
        _send(MOUSEEVENTF_MOVE | base, ax, ay)
        time.sleep(step_delay)
    ax1, ay1 = to_absolute(to_x, to_y, vdesk)
    _send(up | base, ax1, ay1)
    log.info(f"Mouse drag ({from_x},{from_y})->({to_x},{to_y}) button={button}")


def scroll_at(vx: int, vy: int, clicks: int, horizontal: bool = False) -> None:
    """clicks>0 = up/right, clicks<0 = down/left. 1 click = one WHEEL_DELTA notch."""
    ax, ay = to_absolute(vx, vy)
    base = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    _send(MOUSEEVENTF_MOVE | base, ax, ay)
    time.sleep(0.02)
    flags = (MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL) | base
    direction = 1 if clicks >= 0 else -1
    for _ in range(abs(clicks)):
        _send(flags, ax, ay, WHEEL_DELTA * direction)
        time.sleep(0.02)
    log.info(f"Mouse scroll x={vx} y={vy} clicks={clicks} horizontal={horizontal}")


def position() -> tuple[int, int]:
    pt = wintypes.POINT()
    # Physical pos = DPI-correct (unlike GetCursorPos on scaled processes).
    if not user32.GetPhysicalCursorPos(ctypes.byref(pt)):
        user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)
