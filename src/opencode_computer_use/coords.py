"""Single source of truth for all coordinate transforms.

Pipeline:
    Model coords (possibly downscaled screenshot space)
        -> screenshot native pixels
        -> monitor-local pixels
        -> Windows virtual-desktop pixels
        -> SendInput absolute units (0..65535, VIRTUALDESK)

Key rule: NEVER assume screenshot pixel == physical screen pixel.
Screenshot may be downscaled (scale<1), DPI scaling changes effective sizes,
monitors may sit at negative virtual-desktop offsets.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MonitorInfo:
    id: int
    name: str
    x: int  # virtual-desktop origin
    y: int
    width: int
    height: int
    primary: bool
    scale: float  # DPI scale, e.g. 1.0 / 1.25 / 1.5 / 2.0
    dpi_x: int = 96
    dpi_y: int = 96

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains_point(self, vx: int, vy: int) -> bool:
        return self.x <= vx < self.right and self.y <= vy < self.bottom

    def clamp_point(self, vx: int, vy: int) -> tuple[int, int]:
        return (
            max(self.x, min(vx, self.right - 1)),
            max(self.y, min(vy, self.bottom - 1)),
        )


@dataclass
class VirtualDesktop:
    x: int
    y: int
    width: int
    height: int


def model_to_screenshot(mx: float, my: float, scale: float) -> tuple[int, int]:
    """Model saw a downscaled image (scale = out_w / native_w). Map back."""
    if scale <= 0:
        raise ValueError("scale must be > 0")
    return int(round(mx / scale)), int(round(my / scale))


def screenshot_to_virtual(
    sx: int, sy: int, monitor: MonitorInfo, region: tuple[int, int, int, int] | None = None
) -> tuple[int, int]:
    """Screenshot-native pixel -> virtual desktop pixel.

    region = (rx, ry, rw, rh) in monitor-local coords when region capture used.
    """
    ox, oy = (region[0], region[1]) if region else (0, 0)
    return monitor.x + ox + sx, monitor.y + oy + sy


def virtual_to_abs(
    vx: int, vy: int, vdesk: VirtualDesktop
) -> tuple[int, int]:
    """Virtual desktop pixel -> SendInput absolute units (0..65535)."""
    if vdesk.width <= 1 or vdesk.height <= 1:
        raise ValueError("invalid virtual desktop size")
    ax = int(round((vx - vdesk.x) * 65535 / (vdesk.width - 1)))
    ay = int(round((vy - vdesk.y) * 65535 / (vdesk.height - 1)))
    return max(0, min(65535, ax)), max(0, min(65535, ay))


def virtual_to_monitor_relative(
    vx: int, vy: int, monitor: MonitorInfo
) -> tuple[int, int]:
    return vx - monitor.x, vy - monitor.y


def enforce_single_monitor(
    vx: int, vy: int, monitor: MonitorInfo
) -> tuple[int, int, bool]:
    """Clamp point into locked monitor. Returns (cx, cy, was_clamped)."""
    cx, cy = monitor.clamp_point(vx, vy)
    return cx, cy, (cx != vx or cy != vy)
