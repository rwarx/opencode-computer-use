"""Annotated screenshots (set-of-marks): number every clickable element.

Why: guessing pixels from a raw screenshot is the #1 error source of vision
agents. UIA gives exact rects for buttons/links/tabs/checkboxes/edits — draw
numbered badges on the screenshot, return {id -> virtual-desktop coords}.
The agent then says "click #7" instead of estimating (x, y).

Pipeline: UIA elements (foreground window) -> filter visible/enabled/big
enough -> NMS dedupe -> draw badges (PIL) -> downscale -> image + JSON list.
Model coords map exactly like computer_screenshot (reported scale).
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from .config import Settings, log

CLICKABLE = {"Button", "Hyperlink", "MenuItem", "TabItem", "CheckBox",
             "RadioButton", "ComboBox", "SplitButton", "ListItem", "TreeItem",
             "Edit", "Slider", "Spinner", "ScrollBar"}

MAX_MARKS = 50
MIN_SIZE = 10


def collect_marks(hwnd: int | None = None, max_marks: int = MAX_MARKS,
                  bounds: tuple[int, int, int, int] | None = None) -> list[dict]:
    """bounds = (x, y, w, h) virtual-desktop rect; keeps only marks inside
    (e.g. the captured monitor) so other screens don't eat the budget."""
    from . import uia as _uia
    from .monitors import get_virtual_desktop
    vd = get_virtual_desktop()
    bx, by, bw, bh = bounds if bounds else (vd.x, vd.y, vd.width, vd.height)
    tree = _uia.ui_tree(hwnd, depth=8, max_elements=4000).get("tree")
    if not tree:
        return []
    flat: list[dict] = []

    def _inside_vdesk(n) -> bool:
        # UIA returns garbage rects for virtualized/offscreen items even when
        # IsOffscreen is False — drop anything outside the capture bounds.
        m = 8
        return (bx - m <= n["cx"] <= bx + bw + m
                and by - m <= n["cy"] <= by + bh + m)

    def _walk(node):
        if not isinstance(node, dict):
            return
        ct = node.get("control_type", "")
        w, h = node.get("width", 0), node.get("height", 0)
        if (ct in CLICKABLE and node.get("enabled", True)
                and not node.get("offscreen", False)
                and w >= MIN_SIZE and h >= MIN_SIZE
                and (node.get("name") or ct != "Custom")
                and _inside_vdesk(node)):
            flat.append(node)
        for k in node.get("children", []) or []:
            _walk(k)

    _walk(tree)
    # biggest first (containers win over slivers), then NMS by center distance
    flat.sort(key=lambda n: n["width"] * n["height"], reverse=True)
    kept: list[dict] = []
    for n in flat:
        cx, cy = n["cx"], n["cy"]
        if all(abs(cx - k["cx"]) > 14 or abs(cy - k["cy"]) > 14 for k in kept):
            kept.append(n)
        if len(kept) >= max_marks:
            break
    marks = [{"id": i + 1, "name": n["name"][:60], "control_type": n["control_type"],
              "x": n["x"], "y": n["y"], "width": n["width"], "height": n["height"],
              "cx": n["cx"], "cy": n["cy"]} for i, n in enumerate(kept)]
    log.info(f"annotated marks collected: {len(marks)}")
    return marks


def draw_badges(img: Image.Image, badges: list[tuple[int, int, str]]) -> None:
    """Draw numbered badges in-place. badges: [(image_px_x, y, label)]."""
    d = ImageDraw.Draw(img)
    for x, y, label in badges:
        r = 11
        d.ellipse([x - r, y - r, x + r, y + r], fill="#22C55E",
                  outline="black", width=2)
        d.text((x - 4 * len(label), y - 8), label, fill="black")


def annotate_capture(cap, marks: list[dict], max_width: int = 1280):
    """Draw badges, downscale for the model.
    Returns (png, out_scale, marks_in_model_px with mx/my)."""
    from .capture import _RESAMPLE
    img = Image.open(io.BytesIO(cap.png)).convert("RGB")
    ox, oy = (cap.monitor.x, cap.monitor.y) if cap.monitor is not None else (0, 0)
    rx, ry = (cap.region[0], cap.region[1]) if cap.region else (0, 0)
    badges = []
    for m in marks:
        bx = int(round((m["cx"] - ox - rx) * cap.scale))
        by = int(round((m["cy"] - oy - ry) * cap.scale))
        if 0 <= bx < img.size[0] and 0 <= by < img.size[1]:
            badges.append((bx, by, str(m["id"])))
            m["mx"], m["my"] = bx, by
        else:
            m["mx"], m["my"] = -1, -1
    draw_badges(img, badges)
    s = min(1.0, max_width / img.size[0])
    if s < 1.0:
        img = img.resize((int(img.size[0] * s), int(img.size[1] * s)),
                         _RESAMPLE.get(Settings.resample(), Image.BILINEAR))
        for m in marks:
            if m["mx"] >= 0:
                m["mx"] = int(round(m["mx"] * s))
                m["my"] = int(round(m["my"] * s))
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=Settings.png_compress())
    return buf.getvalue(), cap.scale * s, marks
