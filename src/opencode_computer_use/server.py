"""OpenCode Computer Use MCP server (stdio).

Agent loop: SCREENSHOT -> ANALYZE -> ACTION -> SCREENSHOT -> VERIFY ...
Actions accept screenshot_after=true so the model sees the result inline
without an extra tool call.
"""
from __future__ import annotations

import functools
import time

from mcp.server.mcpserver import MCPServer
from mcp.types import ImageContent, TextContent

from . import capture as _cap
from . import keyboard as _kbd
from . import mouse as _mouse
from . import safety as _safety
from . import windows_mgr as _win
from .capture import CaptureResult
from .config import Settings, log
from .coords import enforce_single_monitor, model_to_screenshot, screenshot_to_virtual
from .monitors import get_monitor, list_monitors, monitor_at_point

server = MCPServer("opencode-computer-use", version="0.1.1")


# ---------- helpers ----------

def _active_ctx() -> str:
    try:
        a = _win.get_active_window()
        if not a:
            return "Active window: (none)"
        return (f"Active window: {a['title']} [{a['process']} pid={a['pid']}] "
                f"rect=({a['x']},{a['y']},{a['width']}x{a['height']})")
    except Exception:
        return "Active window: (unknown)"


def _cursor_ctx() -> str:
    try:
        x, y = _mouse.position()
        m = monitor_at_point(list_monitors(), x, y)
        mon = f" on monitor {m.id}" if m else ""
        return f"Cursor: ({x},{y}){mon}"
    except Exception:
        return "Cursor: (unknown)"


def _resolve_capture_monitor(monitor) -> tuple[list, bool]:
    """Return (monitors_to_capture, is_all). Enforces single-monitor lock."""
    mons = list_monitors()
    if Settings.single_monitor_mode():
        locked = Settings.locked_monitor()
        return [get_monitor(mons, locked)], False
    if isinstance(monitor, str) and monitor.lower() == "all":
        return mons, True
    mid = int(monitor) if monitor is not None else 0
    return [get_monitor(mons, mid)], False


def _clamp_to_policy(vx: int, vy: int):
    """Single-monitor lock: clamp + report. Returns (vx, vy, note)."""
    if not Settings.single_monitor_mode():
        return vx, vy, ""
    mons = list_monitors()
    locked = get_monitor(mons, Settings.locked_monitor())
    cx, cy, clamped = enforce_single_monitor(vx, vy, locked)
    note = (f" [clamped to locked monitor {locked.id} ({cx},{cy})]"
            if clamped else f" [locked monitor {locked.id}]")
    if clamped:
        log.warning(f"point ({vx},{vy}) clamped to monitor {locked.id} -> ({cx},{cy})")
    return cx, cy, note


def _parse_region(region) -> tuple[int, int, int, int] | None:
    if region is None:
        return None
    if isinstance(region, dict):
        return (int(region["x"]), int(region["y"]),
                int(region["w"]), int(region["h"]))
    if isinstance(region, (list, tuple)) and len(region) == 4:
        return (int(region[0]), int(region[1]), int(region[2]), int(region[3]))
    raise ValueError("region must be {x,y,w,h} or [x,y,w,h] in monitor-local pixels")


def _shot_text(cap: CaptureResult) -> str:
    if cap.monitor is not None:
        where = (f"monitor={cap.monitor.id} origin=({cap.monitor.x},{cap.monitor.y}) "
                 f"native={cap.monitor.width}x{cap.monitor.height}")
    else:
        where = "monitors=all (virtual desktop stitch)"
    if cap.region:
        where += f" region={cap.region}"
    return (f"Screenshot: {cap.width}x{cap.height} (scale={cap.scale:.3f}, "
            f"model coords x scale = native; divide by {cap.scale:.3f}). {where}. "
            f"To click what you see at model pixel (mx,my): "
            f"native=(mx/{cap.scale:.3f}, my/{cap.scale:.3f}) + origin.")


def _img(cap: CaptureResult) -> ImageContent:
    return ImageContent(type="image", data=cap.b64(), mimeType=cap.mime)


def safe(fn):
    """Never let a tool raise: MCPServer hangs on some tool exceptions,
    and agents handle inline ERROR text better than protocol errors.
    Returns plain str (every tool annotation accepts str content)."""
    @functools.wraps(fn)
    def _w(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:  # noqa: BLE001
            log.warning(f"tool {fn.__name__} error: {e}")
            return f"ERROR ({fn.__name__}): {e}"
    return _w


def _maybe_shot(screenshot_after: bool, monitor, scale: float = 1.0):
    if not screenshot_after:
        return []
    mons, is_all = _resolve_capture_monitor(monitor)
    cap = _cap.capture_all(mons, scale=scale) if is_all else _cap.capture_monitor(mons[0], scale=scale)
    return [TextContent(type="text", text=_shot_text(cap)), _img(cap)]


# ---------- screen / monitors ----------

@server.tool()
@safe
def computer_screenshot(monitor: int | str = 0, region: dict | list | None = None,
                        scale: float = 1.0, jpeg: bool = False) -> list:
    """Capture a screenshot. monitor: id or 'all'. region: {x,y,w,h} monitor-local px.
    Returns text context + PNG image. Model coords map to native via /scale.
    FAST LOOP: scale=0.5 + jpeg=true is ~6x faster and ~25x smaller."""
    mons, is_all = _resolve_capture_monitor(monitor)
    rg = _parse_region(region)
    if is_all:
        cap = _cap.capture_all(mons, scale=scale or 1.0, jpeg=jpeg)
    else:
        cap = _cap.capture_monitor(mons[0], scale=scale or 1.0, region=rg, jpeg=jpeg)
    log.info(f"Screenshot monitor={monitor} {cap.width}x{cap.height}")
    return [TextContent(type="text",
                        text=f"{_shot_text(cap)}\n{_active_ctx()}\n{_cursor_ctx()}"),
            _img(cap)]


@server.tool()
@safe
def computer_list_monitors() -> str:
    """List monitors: id, name, x/y origin, size, primary, DPI scale."""
    import json
    mons = list_monitors()
    data = [{"id": m.id, "name": m.name, "x": m.x, "y": m.y,
             "width": m.width, "height": m.height, "primary": m.primary,
             "scale": m.scale, "dpi": [m.dpi_x, m.dpi_y],
             "resolution": f"{m.width}x{m.height}"} for m in mons]
    if Settings.single_monitor_mode():
        data.append({"locked": True, "locked_monitor": Settings.locked_monitor(),
                     "note": "single-monitor mode: all input clamped to locked monitor"})
    return json.dumps(data, ensure_ascii=False)


# ---------- mouse ----------

@server.tool()
@safe
def computer_mouse_move(x: int, y: int, screenshot_after: bool = False,
                        monitor: int | str = 0) -> list:
    """Move cursor to virtual-desktop pixel (x,y)."""
    _safety.check_input_allowed("mouse")
    x, y, note = _clamp_to_policy(int(x), int(y))
    _mouse.move_to(x, y)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Moved to ({x},{y}).{note}\n{_cursor_ctx()}\n{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_mouse_click(x: int, y: int, button: str = "left",
                         screenshot_after: bool = True,
                         monitor: int | str = 0) -> list:
    """Click at (x,y). button: left|right|middle."""
    _safety.check_input_allowed("mouse")
    x, y, note = _clamp_to_policy(int(x), int(y))
    _mouse.click_at(x, y, button)
    time.sleep(0.15)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Click {button} at ({x},{y}) done.{note}\n"
                             f"{_cursor_ctx()}\n{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_mouse_double_click(x: int, y: int, button: str = "left",
                                screenshot_after: bool = True,
                                monitor: int | str = 0) -> list:
    """Double-click at (x,y)."""
    _safety.check_input_allowed("mouse")
    x, y, note = _clamp_to_policy(int(x), int(y))
    _mouse.double_click_at(x, y, button)
    time.sleep(0.2)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Double-click {button} at ({x},{y}) done.{note}\n"
                             f"{_cursor_ctx()}\n{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_mouse_down(button: str = "left") -> str:
    """Press and hold a mouse button (pair with computer_mouse_up / drag)."""
    _safety.check_input_allowed("mouse")
    _mouse.button_down(button)
    return f"Mouse {button} down."


@server.tool()
@safe
def computer_mouse_up(button: str = "left") -> str:
    """Release a held mouse button."""
    _safety.check_input_allowed("mouse")
    _mouse.button_up(button)
    return f"Mouse {button} up."


@server.tool()
@safe
def computer_mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int,
                        button: str = "left", screenshot_after: bool = True,
                        monitor: int | str = 0) -> list:
    """Drag from (from_x,from_y) to (to_x,to_y). Virtual-desktop pixels."""
    _safety.check_input_allowed("mouse")
    fx, fy, n1 = _clamp_to_policy(int(from_x), int(from_y))
    tx, ty, n2 = _clamp_to_policy(int(to_x), int(to_y))
    _mouse.drag(fx, fy, tx, ty, button)
    time.sleep(0.15)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Drag ({fx},{fy})->({tx},{ty}) {button} done.{n1}{n2}\n"
                             f"{_cursor_ctx()}\n{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_mouse_scroll(x: int, y: int, clicks: int = 3, horizontal: bool = False,
                          screenshot_after: bool = True,
                          monitor: int | str = 0) -> list:
    """Scroll at (x,y). clicks>0 up/right, <0 down/left."""
    _safety.check_input_allowed("mouse")
    x, y, note = _clamp_to_policy(int(x), int(y))
    _mouse.scroll_at(x, y, int(clicks), bool(horizontal))
    time.sleep(0.15)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Scroll at ({x},{y}) clicks={clicks} "
                             f"{'horizontal' if horizontal else 'vertical'} done.{note}\n"
                             f"{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_mouse_position() -> str:
    """Return cursor position (virtual-desktop px) + monitor + active window."""
    import json
    x, y = _mouse.position()
    m = monitor_at_point(list_monitors(), x, y)
    return json.dumps({"x": x, "y": y,
                       "monitor": m.id if m else None,
                       "active": _win.get_active_window()},
                      ensure_ascii=False)


# ---------- keyboard ----------

@server.tool()
@safe
def computer_type(text: str, interval: float = 0.0, use_clipboard: bool = False,
                  screenshot_after: bool = True, monitor: int | str = 0) -> list:
    """Type text (Unicode: Latin+Cyrillic). Long text uses clipboard+Ctrl+V fallback."""
    _safety.check_input_allowed("keyboard")
    risk = _safety.check_text_risk(text)
    if risk["needs_confirmation"]:
        return [TextContent(type="text", text=(
            "REFUSED (safe mode): text looks risky (shutdown/delete/purchase pattern). "
            "Set COMPUTER_USE_AUTONOMOUS=1 to allow, or rephrase."))]
    # Never log the text itself — only length/method.
    res = _kbd.type_text(text, interval=float(interval or 0.0),
                         use_clipboard=bool(use_clipboard) or None
                         if use_clipboard else None)
    time.sleep(0.15)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Typed {res['typed']} chars via {res['method']}.\n"
                             f"{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_key(key: str, screenshot_after: bool = False,
                 monitor: int | str = 0) -> list:
    """Press a special key: ENTER TAB ESC BACKSPACE DELETE UP/DOWN/LEFT/RIGHT HOME END PAGEUP/PAGEDOWN F1-F12..."""
    _safety.check_input_allowed("keyboard")
    _kbd.press_key(key)
    time.sleep(0.1)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text", text=f"Key {key.upper()} pressed.\n{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_hotkey(keys: list[str], screenshot_after: bool = False,
                    monitor: int | str = 0) -> list:
    """Press a chord, e.g. keys=['CTRL','C'] or ['CTRL','SHIFT','ESC']."""
    _safety.check_input_allowed("keyboard")
    if not keys or not isinstance(keys, list):
        raise ValueError("keys must be a non-empty list, e.g. ['CTRL','C']")
    _kbd.hotkey(*keys)
    time.sleep(0.15)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Hotkey {'+'.join(k.upper() for k in keys)} pressed.\n"
                             f"{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_key_down(key: str) -> str:
    """Hold a key down (pair with computer_key_up)."""
    _safety.check_input_allowed("keyboard")
    _kbd.key_down(key)
    return f"Key {key.upper()} down."


@server.tool()
@safe
def computer_key_up(key: str) -> str:
    """Release a held key."""
    _safety.check_input_allowed("keyboard")
    _kbd.key_up(key)
    return f"Key {key.upper()} up."


# ---------- windows ----------

@server.tool()
@safe
def computer_list_windows(limit: int = 50) -> str:
    """List visible windows: title, process, pid, rect, is_active."""
    import json
    _safety.check_input_allowed("window")
    return json.dumps(_win.list_windows(int(limit)), ensure_ascii=False)


@server.tool()
@safe
def computer_get_active_window() -> str:
    """Return the foreground window info."""
    import json
    return json.dumps(_win.get_active_window(), ensure_ascii=False)


@server.tool()
@safe
def computer_focus_window(target: str | int) -> str:
    """Focus a window by hwnd or (sub)title. Returns active window after."""
    import json
    _safety.check_input_allowed("window")
    return json.dumps(_win.focus_window(target), ensure_ascii=False)


@server.tool()
@safe
def computer_minimize_window(target: str | int) -> str:
    """Minimize a window by hwnd or title."""
    import json
    _safety.check_input_allowed("window")
    return json.dumps(_win.set_window_state(target, "minimize"), ensure_ascii=False)


@server.tool()
@safe
def computer_maximize_window(target: str | int) -> str:
    """Maximize a window by hwnd or title."""
    import json
    _safety.check_input_allowed("window")
    return json.dumps(_win.set_window_state(target, "maximize"), ensure_ascii=False)


@server.tool()
@safe
def computer_restore_window(target: str | int) -> str:
    """Restore a window by hwnd or title."""
    import json
    _safety.check_input_allowed("window")
    return json.dumps(_win.set_window_state(target, "restore"), ensure_ascii=False)


# ---------- OCR ----------

def _capture_for_ocr(monitor, scale: float) -> tuple[CaptureResult, object]:
    mons, is_all = _resolve_capture_monitor(monitor)
    cap = (_cap.capture_all(mons, scale=scale or 1.0)
           if is_all else _cap.capture_monitor(mons[0], scale=scale or 1.0))
    return cap, mons[0] if not is_all else None


@server.tool()
@safe
def computer_ocr(monitor: int | str = 0, scale: float = 1.0) -> str:
    """OCR the screen. Returns [{text,x,y,width,height,confidence,cx,cy}] in virtual-desktop px."""
    import json
    from . import ocr as _ocr
    mons, is_all = _resolve_capture_monitor(monitor)
    cap = (_cap.capture_all(mons, scale=scale or 1.0)
           if is_all else _cap.capture_monitor(mons[0], scale=scale or 1.0))
    items = _ocr.ocr_image(cap.png)
    # ocr returns image-px; convert to virtual-desktop px.
    ox, oy = 0, 0
    if not is_all:
        ox, oy = mons[0].x, mons[0].y
    else:
        ox = min(m.x for m in mons); oy = min(m.y for m in mons)
    out = []
    for r in items:
        sx, sy = model_to_screenshot(r["x"], r["y"], cap.scale)
        w = int(round(r["width"] / cap.scale)); h = int(round(r["height"] / cap.scale))
        vx, vy = ox + sx, oy + sy
        out.append({**r, "x": vx, "y": vy, "width": w, "height": h,
                    "cx": vx + w // 2, "cy": vy + h // 2})
    return json.dumps({"count": len(out), "items": out[:200]}, ensure_ascii=False)


@server.tool()
@safe
def computer_find_text(text: str, monitor: int | str = 0, scale: float = 1.0) -> str:
    """Find text on screen via OCR. Returns {found,x,y,width,height,cx,cy,confidence} in virtual-desktop px."""
    import json
    from . import ocr as _ocr
    mons, is_all = _resolve_capture_monitor(monitor)
    cap = (_cap.capture_all(mons, scale=scale or 1.0)
           if is_all else _cap.capture_monitor(mons[0], scale=scale or 1.0))
    hit = _ocr.find_text(cap.png, text)
    if not hit:
        return json.dumps({"found": False, "text": text})
    ox, oy = (mons[0].x, mons[0].y) if not is_all else (
        min(m.x for m in mons), min(m.y for m in mons))
    sx, sy = model_to_screenshot(hit["x"], hit["y"], cap.scale)
    w = int(round(hit["width"] / cap.scale)); h = int(round(hit["height"] / cap.scale))
    vx, vy = ox + sx, oy + sy
    log.info(f"OCR found {text!r} at ({vx},{vy})")
    return json.dumps({"found": True, "text": hit["text"], "x": vx, "y": vy,
                       "width": w, "height": h, "cx": vx + w // 2, "cy": vy + h // 2,
                       "confidence": hit["confidence"]}, ensure_ascii=False)


@server.tool()
@safe
def computer_click_text(text: str, monitor: int | str = 0, button: str = "left",
                        screenshot_after: bool = True) -> list:
    """Find text via OCR and click its center."""
    import json
    from . import ocr as _ocr
    _safety.check_input_allowed("mouse")
    mons, is_all = _resolve_capture_monitor(monitor)
    cap = (_cap.capture_all(mons, scale=scale or 1.0)
           if is_all else _cap.capture_monitor(mons[0], scale=1.0))
    # NOTE: capture at full scale for OCR precision.
    hit = _ocr.find_text(cap.png, text)
    if not hit:
        return [TextContent(type="text", text=f"Text {text!r} not found on screen.")]
    ox, oy = (mons[0].x, mons[0].y) if not is_all else (
        min(m.x for m in mons), min(m.y for m in mons))
    sx, sy = model_to_screenshot(hit["cx"], hit["cy"], cap.scale)
    vx, vy = ox + sx, oy + sy
    vx, vy, note = _clamp_to_policy(vx, vy)
    _mouse.click_at(vx, vy, button)
    time.sleep(0.2)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Clicked text {hit['text']!r} at ({vx},{vy}) "
                             f"conf={hit['confidence']}.{note}\n"
                             f"{_cursor_ctx()}\n{_active_ctx()}")] + tail


# ---------- UI Automation ----------

@server.tool()
@safe
def computer_ui_tree(hwnd: int | None = None, depth: int = 3,
                     max_elements: int = 200) -> str:
    """UI Automation tree of a window (default: foreground). Names, types, rects, enabled."""
    import json
    from . import uia as _uia
    if hwnd in (0, "0", ""):
        hwnd = None
    tree = _uia.ui_tree(int(hwnd) if hwnd else None, int(depth), int(max_elements))
    s = json.dumps(tree, ensure_ascii=False)
    return s[:120000]  # cap payload


@server.tool()
@safe
def computer_find_element(name: str | None = None, control_type: str | None = None,
                          hwnd: int | None = None) -> str:
    """Find a UIA element by name/control_type. Returns virtual-desktop rect + center."""
    import json
    from . import uia as _uia
    hit = _uia.find_element(name, control_type, int(hwnd) if hwnd else None)
    if not hit:
        return json.dumps({"found": False, "name": name, "control_type": control_type})
    log.info(f"UIA found {name!r}/{control_type!r} at ({hit['cx']},{hit['cy']})")
    return json.dumps({"found": True, **hit}, ensure_ascii=False)


@server.tool()
@safe
def computer_invoke_element(name: str | None = None, control_type: str | None = None,
                            hwnd: int | None = None,
                            screenshot_after: bool = True,
                            monitor: int | str = 0) -> list:
    """Invoke a UIA element (InvokePattern, no coordinates needed)."""
    _safety.check_input_allowed("mouse")
    from . import uia as _uia
    import json
    res = _uia.invoke_element(name, control_type, int(hwnd) if hwnd else None)
    time.sleep(0.2)
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"Invoked {name!r} ({control_type}): "
                             f"{json.dumps(res)}\n{_active_ctx()}")] + tail


# ---------- wait / verify / batch ----------

@server.tool()
@safe
def computer_wait(seconds: float = 1.0) -> str:
    """Sleep N seconds (prefer wait_for_text/window when possible). Max 60."""
    s = max(0.0, min(60.0, float(seconds)))
    time.sleep(s)
    return f"Waited {s:.1f}s."


@server.tool()
@safe
def computer_wait_for_text(text: str, timeout: float = 30.0,
                           monitor: int | str = 0) -> str:
    """Poll OCR until text appears or timeout (sec, max 300)."""
    import json
    from . import ocr as _ocr
    deadline = time.time() + max(1.0, min(300.0, float(timeout)))
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            mons, is_all = _resolve_capture_monitor(monitor)
            cap = (_cap.capture_all(mons, scale=0.75)
                   if is_all else _cap.capture_monitor(mons[0], scale=0.75))
            hit = _ocr.find_text(cap.png, text, min_confidence=0.2)
            if hit:
                return json.dumps({"found": True, "text": text,
                                   "attempts": attempt}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            log.debug(f"wait_for_text poll failed: {e}")
        time.sleep(1.5)
    return json.dumps({"found": False, "text": text, "timeout": timeout})


@server.tool()
@safe
def computer_wait_for_window(title: str, timeout: float = 30.0) -> str:
    """Poll window list until a title substring appears or timeout."""
    import json
    deadline = time.time() + max(1.0, min(300.0, float(timeout)))
    while time.time() < deadline:
        for w in _win.list_windows(limit=200):
            if title.lower() in w["title"].lower():
                log.info(f"Window appeared: {w['title']}")
                return json.dumps({"found": True, "window": w}, ensure_ascii=False)
        time.sleep(1.0)
    return json.dumps({"found": False, "title": title})


@server.tool()
@safe
def computer_element_exists(name: str | None = None,
                            control_type: str | None = None,
                            hwnd: int | None = None) -> str:
    """Check UIA element existence (verification primitive)."""
    import json
    from . import uia as _uia
    try:
        hit = _uia.find_element(name, control_type, int(hwnd) if hwnd else None,
                                max_elements=800)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"exists": False, "error": str(e)[:200]})
    return json.dumps({"exists": bool(hit),
                       "name": name, "control_type": control_type,
                       "element": hit})


@server.tool()
@safe
def computer_batch(actions: list[dict], screenshot_after: bool = True,
                   monitor: int | str = 0) -> list:
    """Run actions atomically-in-sequence; STOP on first error.
    Each: {type: click|double_click|move|drag|scroll|type|key|hotkey|wait,
      x,y,button,from_x,from_y,to_x,to_y,clicks,text,key,keys,seconds}.
    Coords are virtual-desktop px (same as screenshot mapping)."""
    import json
    results: list[dict] = []
    try:
        for i, a in enumerate(actions or []):
            t = str(a.get("type", "")).lower()
            if _safety.is_stopped():
                raise RuntimeError("emergency stop active")
            if t == "click":
                _safety.check_input_allowed("mouse")
                x, y, _ = _clamp_to_policy(int(a["x"]), int(a["y"]))
                _mouse.click_at(x, y, a.get("button", "left")); results.append({"i": i, "ok": True})
            elif t == "double_click":
                _safety.check_input_allowed("mouse")
                x, y, _ = _clamp_to_policy(int(a["x"]), int(a["y"]))
                _mouse.double_click_at(x, y, a.get("button", "left")); results.append({"i": i, "ok": True})
            elif t == "move":
                _safety.check_input_allowed("mouse")
                x, y, _ = _clamp_to_policy(int(a["x"]), int(a["y"]))
                _mouse.move_to(x, y); results.append({"i": i, "ok": True})
            elif t == "drag":
                _safety.check_input_allowed("mouse")
                fx, fy, _ = _clamp_to_policy(int(a["from_x"]), int(a["from_y"]))
                tx, ty, _ = _clamp_to_policy(int(a["to_x"]), int(a["to_y"]))
                _mouse.drag(fx, fy, tx, ty, a.get("button", "left")); results.append({"i": i, "ok": True})
            elif t == "scroll":
                _safety.check_input_allowed("mouse")
                x, y, _ = _clamp_to_policy(int(a.get("x", 0)), int(a.get("y", 0)))
                _mouse.scroll_at(x, y, int(a.get("clicks", 3))); results.append({"i": i, "ok": True})
            elif t == "type":
                _safety.check_input_allowed("keyboard")
                r = _safety.check_text_risk(a.get("text", ""))
                if r["needs_confirmation"]:
                    raise RuntimeError(f"batch item {i}: risky text blocked in safe mode")
                _kbd.type_text(a.get("text", "")); results.append({"i": i, "ok": True})
            elif t in ("key", "keypress"):
                _safety.check_input_allowed("keyboard")
                _kbd.press_key(a.get("key", "ENTER")); results.append({"i": i, "ok": True})
            elif t == "hotkey":
                _safety.check_input_allowed("keyboard")
                keys = a.get("keys", [])
                _kbd.hotkey(*keys); results.append({"i": i, "ok": True})
            elif t == "wait":
                time.sleep(max(0.0, min(30.0, float(a.get("seconds", 1.0)))))
                results.append({"i": i, "ok": True})
            else:
                raise ValueError(f"batch item {i}: unknown type {t!r}")
            time.sleep(0.08)
    except Exception as e:  # noqa: BLE001
        results.append({"ok": False, "error": str(e)[:300]})
        tail = _maybe_shot(bool(screenshot_after), monitor)
        return [TextContent(type="text",
                            text=f"BATCH STOPPED at item {len(results)-1}: {e}\n"
                                 f"Results: {json.dumps(results)}\n{_active_ctx()}")] + tail
    tail = _maybe_shot(bool(screenshot_after), monitor)
    return [TextContent(type="text",
                        text=f"BATCH OK ({len(results)} actions).\n"
                             f"Results: {json.dumps(results)}\n"
                             f"{_cursor_ctx()}\n{_active_ctx()}")] + tail


@server.tool()
@safe
def computer_emergency_stop(reset: bool = False, reason: str = "user request") -> str:
    """Kill-switch: disables mouse+keyboard. reset=true re-enables."""
    import json
    if reset:
        return json.dumps(_safety.reset_stop())
    return json.dumps(_safety.emergency_stop(reason))


@server.tool()
@safe
def computer_overlay_show(text: str | None = None) -> str:
    """Show the 'OpenCode using your computer' banner (sticky until hide).
    Click-through: never blocks mouse/keyboard. Optional custom title text."""
    import json
    from . import overlay as _overlay
    return json.dumps(_overlay.show(text))


@server.tool()
@safe
def computer_overlay_hide() -> str:
    """Hide the 'using your computer' banner."""
    import json
    from . import overlay as _overlay
    return json.dumps(_overlay.hide())


def main() -> None:
    log.info(f"computer-use MCP v0.1.1 single_monitor={Settings.single_monitor_mode()} "
             f"monitor={Settings.locked_monitor()} autonomous={Settings.autonomous()}")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
