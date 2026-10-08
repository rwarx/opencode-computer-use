"""Windows UI Automation layer (optional, graceful degradation).

Uses comtypes + UIAutomationCore directly (no hard pywinauto dependency)
so core install stays light. Exposes:
  - ui_tree(hwnd=None, depth, max_elements): control/content tree with rects
  - find_element(name, control_type, hwnd): bounding box in virtual-desktop px
  - invoke_element(...): Click/Invoke pattern without coordinates.

If UIA is unavailable the agent falls back to OCR -> visual coordinates.
"""
from __future__ import annotations

from .config import log

TREE_SCOPE_CHILDREN = 2
TREE_SCOPE_DESCENDANTS = 4

CONTROL_TYPE_NAMES = {
    50000: "Invoke", 50001: "SelectionItem", 50002: "Text", 50003: "Header",
    50004: "HeaderItem", 50005: "Table", 50006: "TitleBar", 50007: "MenuBar",
    50008: "Menu", 50009: "MenuItem", 50010: "DropTarget", 50011: "DropSource",
    50012: "Link", 50013: "Image", 50014: "List", 50015: "ListItem",
    50016: "Pane", 50017: "ScrollBar", 50018: "Separator", 50019: "Slider",
    50020: "Spinner", 50021: "StatusBar", 50022: "Tab", 50023: "TabItem",
    50024: "Text", 50025: "ToolBar", 50026: "ToolTip", 50027: "Tree",
    50028: "TreeItem", 50029: "Custom", 50030: "Group", 50031: "Thumb",
    50032: "DataGrid", 50033: "DataItem", 50034: "Document", 50035: "SplitButton",
    50036: "Window", 50037: "Pane", 50038: "Header", 50039: "HeaderItem",
    50002 + 0: "Button",  # Button=50000 handled above; keep map explicit below
}

# Correct UIA_ControlTypeIds (MSDN):
UIA_IDS = {
    "Button": 50000, "Calendar": 50001, "CheckBox": 50002, "ComboBox": 50003,
    "Edit": 50004, "Hyperlink": 50005, "Image": 50006, "ListItem": 50007,
    "List": 50008, "Menu": 50009, "MenuBar": 50010, "MenuItem": 50011,
    "ProgressBar": 50012, "RadioButton": 50013, "ScrollBar": 50014,
    "Slider": 50015, "Spinner": 50016, "StatusBar": 50017, "Tab": 50018,
    "TabItem": 50019, "Text": 50020, "ToolBar": 50021, "ToolTip": 50022,
    "Tree": 50023, "TreeItem": 50024, "Custom": 50025, "Group": 50026,
    "Thumb": 50027, "DataGrid": 50028, "DataItem": 50029, "Document": 50030,
    "SplitButton": 50031, "Window": 50032, "Pane": 50033, "Header": 50034,
    "HeaderItem": 50035, "Table": 50036, "TitleBar": 50037, "Separator": 50038,
}
ID_TO_NAME = {v: k for k, v in UIA_IDS.items()}

_uia = None
_uia_error: str | None = None


def _get_uia():
    global _uia, _uia_error
    if _uia is not None:
        return _uia
    if _uia_error is not None:
        raise RuntimeError(f"UI Automation unavailable: {_uia_error}")
    try:
        import comtypes.client as _cc
        # Generate typed wrapper from UIAutomationCore's embedded TLB so we
        # get IUIAutomation methods instead of a bare IUnknown pointer.
        _cc.GetModule("UIAutomationCore.dll")
        from comtypes.gen.UIAutomationClient import IUIAutomation
        _uia = _cc.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}",
                                interface=IUIAutomation)
        return _uia
    except Exception as e:  # noqa: BLE001
        _uia_error = str(e)
        raise RuntimeError(
            f"UI Automation unavailable (pip install opencode-computer-use[uia]): {e}")


def is_available() -> bool:
    try:
        _get_uia()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning(f"UIA unavailable: {e}")
        return False


def _el_info(el, depth: int, max_e: list[int]):
    if max_e[0] <= 0:
        return None
    max_e[0] -= 1
    try:
        name = el.CurrentName or ""
        cid = int(el.CurrentControlType)
        rect = el.CurrentBoundingRectangle
        enabled = bool(el.CurrentIsEnabled)
        offscreen = bool(el.CurrentIsOffscreen)
    except Exception:
        return None
    return {
        "name": name, "control_type": ID_TO_NAME.get(cid, str(cid)),
        "control_type_id": cid,
        "x": int(rect.left), "y": int(rect.top),
        "width": int(rect.right - rect.left),
        "height": int(rect.bottom - rect.top),
        "enabled": enabled, "offscreen": offscreen,
        "cx": int(rect.left + (rect.right - rect.left) // 2),
        "cy": int(rect.top + (rect.bottom - rect.top) // 2),
        "depth": depth,
    }


def ui_tree(hwnd: int | None = None, depth: int = 4, max_elements: int = 300) -> dict:
    uia = _get_uia()
    if hwnd:
        root = uia.ElementFromHandle(hwnd)
    else:
        root = uia.GetRootElement()
    counter = [max_elements]
    tree = _walk(uia, root, 0, depth, counter)
    log.info(f"UIA tree depth={depth} elements~{max_elements - counter[0]}")
    return {"tree": tree, "truncated": counter[0] <= 0}


def _walk(uia, el, cur: int, max_depth: int, counter: list[int]):
    node = _el_info(el, cur, counter)
    if node is None:
        return None
    if cur >= max_depth or counter[0] <= 0:
        node["children"] = []
        return node
    kids = []
    try:
        cond = uia.CreateTrueCondition()
        walker = uia.CreateTreeWalker(cond)
        child = walker.GetFirstChildElement(el)
        while child is not None and counter[0] > 0:
            sub = _walk(uia, child, cur + 1, max_depth, counter)
            if sub is not None:
                kids.append(sub)
            try:
                child = walker.GetNextSiblingElement(child)
            except Exception:
                break
    except Exception:
        pass
    node["children"] = kids
    return node


def find_element(name: str | None = None, control_type: str | None = None,
                 hwnd: int | None = None, max_depth: int = 8,
                 max_elements: int = 2000) -> dict | None:
    uia = _get_uia()
    root = uia.ElementFromHandle(hwnd) if hwnd else uia.GetRootElement()
    want_ct = UIA_IDS.get((control_type or "").strip(), None) if control_type else None
    needle = (name or "").strip().lower()
    counter = [max_elements]
    return _dfs(uia, root, 0, max_depth, counter, needle, want_ct)


def _dfs(uia, el, cur, max_depth, counter, needle, want_ct):
    if counter[0] <= 0 or cur > max_depth:
        return None
    counter[0] -= 1
    try:
        ename = (el.CurrentName or "").lower()
        cid = int(el.CurrentControlType)
        ok = True
        if needle and needle not in ename:
            ok = False
        if want_ct is not None and cid != want_ct:
            ok = False
        if ok and (needle or want_ct is not None):
            rect = el.CurrentBoundingRectangle
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if w > 0 and h > 0 and not el.CurrentIsOffscreen:
                return {
                    "found": True, "name": el.CurrentName,
                    "control_type": ID_TO_NAME.get(cid, str(cid)),
                    "x": int(rect.left), "y": int(rect.top),
                    "width": int(w), "height": int(h),
                    "cx": int(rect.left + w // 2), "cy": int(rect.top + h // 2),
                    "enabled": bool(el.CurrentIsEnabled),
                }
    except Exception:
        pass
    try:
        walker = uia.CreateTreeWalker(uia.CreateTrueCondition())
        child = walker.GetFirstChildElement(el)
        while child is not None and counter[0] > 0:
            hit = _dfs(uia, child, cur + 1, max_depth, counter, needle, want_ct)
            if hit:
                return hit
            try:
                child = walker.GetNextSiblingElement(child)
            except Exception:
                break
    except Exception:
        pass
    return None


def invoke_element(name: str | None = None, control_type: str | None = None,
                   hwnd: int | None = None) -> dict:
    """Invoke (click) element via UIA patterns — no coordinates needed."""
    import comtypes.gen.UIAutomationClient as _uia_gen  # noqa
    uia = _get_uia()
    el_raw = _find_raw(uia, name, control_type, hwnd)
    if el_raw is None:
        raise ValueError(f"element not found name={name!r} control_type={control_type!r}")
    # Try Invoke pattern, then SelectionItem/ExpandCollapse/Toggle, then legacy click.
    try:
        invoke = el_raw.GetCurrentPattern(10000)  # UIA_InvokePatternId
        invoke.Invoke()
        return {"invoked": True, "method": "InvokePattern"}
    except Exception:
        pass
    # Fallback: click center via SendInput.
    from . import mouse as _mouse
    rect = el_raw.CurrentBoundingRectangle
    cx = int(rect.left + (rect.right - rect.left) // 2)
    cy = int(rect.top + (rect.bottom - rect.top) // 2)
    _mouse.click_at(cx, cy)
    return {"invoked": True, "method": "click-fallback", "x": cx, "y": cy}


def _find_raw(uia, name, control_type, hwnd):
    root = uia.ElementFromHandle(hwnd) if hwnd else uia.GetRootElement()
    want_ct = UIA_IDS.get((control_type or "").strip(), None) if control_type else None
    needle = (name or "").strip().lower()
    stack = [root]
    seen = 0
    while stack and seen < 5000:
        el = stack.pop()
        seen += 1
        try:
            ename = (el.CurrentName or "").lower()
            cid = int(el.CurrentControlType)
            if ((not needle or needle in ename)
                    and (want_ct is None or cid == want_ct)
                    and (needle or want_ct is not None)):
                return el
        except Exception:
            continue
        try:
            walker = uia.CreateTreeWalker(uia.CreateTrueCondition())
            child = walker.GetFirstChildElement(el)
            while child is not None:
                stack.append(child)
                try:
                    child = walker.GetNextSiblingElement(child)
                except Exception:
                    break
        except Exception:
            continue
    return None
