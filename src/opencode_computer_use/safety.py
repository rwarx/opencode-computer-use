"""Safety: policy enforcement + emergency stop + human modes.

- No shell/PowerShell/shutdown/reboot/delete tools are exposed at all.
  GUI control only — shell stays with OpenCode.
- Emergency stop: global kill-switch disabling mouse/keyboard until reset.
- Human modes: SAFE (default) flags risky text/actions as needing
  confirmation; AUTONOMOUS (COMPUTER_USE_AUTONOMOUS=1) skips the gate.
- Single-monitor lock: enforced at the coordinate layer.
"""
from __future__ import annotations

import re
import threading

from .config import Settings, log

_stop = threading.Event()

RISKY_PATTERNS = [
    # NOTE: no trailing \b — alternatives ending in non-word chars
    # (e.g. "format D:", "del /f") would never match with it.
    re.compile(r"\b(shutdown|reboot|restart|format\s+[a-z]:|diskpart|rm\s+-rf|del\s+/[fsq])", re.I),
    re.compile(r"(rm\s+-rf\s+/(home|root|\*)|mkfs|:?\(\)\s*\{\s*:\|\:&\s*\})", re.I),
    re.compile(r"\b(drop\s+table|delete\s+from\s+\w+)\b", re.I),
    re.compile(r"(buy\s+now|place\s+order|confirm\s+purchase|send\s+payment|transfer\s+money)", re.I),
    re.compile(r"(отформатировать|выключить\s+компьютер|перезагрузить|удалить\s+все)", re.I),
]

RISKY_KEYS = {
    # handled as informational only; actual blocking happens in server via policy
}


def emergency_stop(reason: str = "user request") -> dict:
    _stop.set()
    log.warning(f"EMERGENCY STOP engaged: {reason}")
    return {"stopped": True, "reason": reason,
            "message": "Mouse+keyboard disabled. Restart server or call computer_emergency_stop(reset=true)."}


def reset_stop() -> dict:
    _stop.clear()
    log.warning("Emergency stop CLEARED — input re-enabled")
    return {"stopped": False, "message": "Input re-enabled."}


def is_stopped() -> bool:
    return _stop.is_set()


def check_input_allowed(kind: str) -> None:
    if is_stopped():
        raise RuntimeError("EMERGENCY STOP active — input disabled. Reset before continuing.")
    if kind == "mouse" and not Settings.allow_mouse():
        raise RuntimeError("mouse input disabled by policy (COMPUTER_USE_ALLOW_MOUSE=0)")
    if kind == "keyboard" and not Settings.allow_keyboard():
        raise RuntimeError("keyboard input disabled by policy (COMPUTER_USE_ALLOW_KEYBOARD=0)")
    if kind == "window" and not Settings.allow_window_control():
        raise RuntimeError("window control disabled by policy (COMPUTER_USE_ALLOW_WINDOW=0)")
    if kind in ("mouse", "keyboard"):
        # Human signal: banner appears while the agent is driving.
        try:
            from . import overlay as _overlay
            _overlay.touch()
        except Exception:
            pass


def check_text_risk(text: str) -> dict:
    """Return {risky, matches, needs_confirmation} without logging the text."""
    hits = [p.pattern for p in RISKY_PATTERNS if p.search(text or "")]
    risky = bool(hits)
    needs_confirmation = risky and not Settings.autonomous()
    return {"risky": risky, "matches": len(hits),
            "needs_confirmation": needs_confirmation,
            "mode": "autonomous" if Settings.autonomous() else "safe"}
