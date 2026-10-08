"""Fast per-monitor screenshots via mss -> Pillow.

Supports: single monitor, all-monitors (stitched), region capture,
downscaling (scale<1) with coordinate-scale reporting so the model
can return coords in the space it actually saw.
"""
from __future__ import annotations

import base64
import io

import mss
from PIL import Image

from .config import Settings, log
from .coords import MonitorInfo


class CaptureResult:
    def __init__(self, png: bytes, width: int, height: int, scale: float,
                 monitor: MonitorInfo | None, region=None):
        self.png = png
        self.width = width
        self.height = height
        self.scale = scale  # out/native; model divides by scale via model_to_screenshot
        self.monitor = monitor
        self.region = region

    def b64(self) -> str:
        return base64.b64encode(self.png).decode("ascii")


def _to_png(img: Image.Image, scale: float, max_width: int, jpeg: bool = False) -> tuple[bytes, float, int, int]:
    native_w, native_h = img.size
    target_w = min(native_w, max_width)
    eff_scale = target_w / native_w if native_w else 1.0
    if scale and 0 < scale < 1.0:
        # explicit scale requested: combine with max_width clamp
        s = min(scale, eff_scale)
    else:
        s = eff_scale
    if s < 1.0:
        img = img.resize((max(1, int(native_w * s)), max(1, int(native_h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    if jpeg:
        img.convert("RGB").save(buf, "JPEG", quality=Settings.jpeg_quality())
        mime_note = "jpeg"
    else:
        img.save(buf, "PNG")
        mime_note = "png"
    log.debug(f"capture encoded {mime_note} {img.size[0]}x{img.size[1]} scale={s:.3f}")
    return buf.getvalue(), s, img.size[0], img.size[1]


def capture_monitor(monitor: MonitorInfo, scale: float = 1.0,
                    region: tuple[int, int, int, int] | None = None,
                    jpeg: bool = False) -> CaptureResult:
    """region = (x, y, w, h) in monitor-local coords."""
    with mss.mss() as sct:
        if region is not None:
            rx, ry, rw, rh = region
            grab = {"left": monitor.x + rx, "top": monitor.y + ry,
                    "width": rw, "height": rh}
        else:
            grab = {"left": monitor.x, "top": monitor.y,
                    "width": monitor.width, "height": monitor.height}
        shot = sct.grab(grab)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    png, eff, w, h = _to_png(img, scale, Settings.max_screenshot_width(), jpeg)
    return CaptureResult(png, w, h, eff, monitor, region)


def capture_all(monitors: list[MonitorInfo], scale: float = 1.0,
                jpeg: bool = False) -> CaptureResult:
    """Stitch all monitors into one virtual-desktop image."""
    min_x = min(m.x for m in monitors)
    min_y = min(m.y for m in monitors)
    max_r = max(m.right for m in monitors)
    max_b = max(m.bottom for m in monitors)
    with mss.mss() as sct:
        shot = sct.grab({"left": min_x, "top": min_y,
                         "width": max_r - min_x, "height": max_b - min_y})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    png, eff, w, h = _to_png(img, scale, Settings.max_screenshot_width(), jpeg)
    return CaptureResult(png, w, h, eff, None, None)


def capture_window_rect(vrect: tuple[int, int, int, int], scale: float = 1.0) -> CaptureResult:
    x, y, w, h = vrect
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    png, eff, ow, oh = _to_png(img, scale, Settings.max_screenshot_width())
    return CaptureResult(png, ow, oh, eff, None, (x, y, w, h))
