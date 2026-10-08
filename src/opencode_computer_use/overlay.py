"""On-screen "OpenCode using your computer" banner.

Why: while the agent drives the GUI, the human must see that the machine is
busy and keep hands off mouse/keyboard. The banner is:
- topmost + borderless pill at the top-center of the primary (or locked) monitor,
- click-through (WS_EX_TRANSPARENT): agent clicks and user clicks pass under it,
  it is purely informational and can never block automation,
- controlled by MCP tools (show/hide) and optional auto-mode: appears on the
  first mouse/keyboard action, hides after N idle seconds.

Runs in a daemon thread; all Tk calls happen in that thread, commands go
through a queue. If tkinter is missing, everything degrades gracefully.
"""
from __future__ import annotations

import ctypes
import queue
import threading

from .config import Settings, log

BG = "#0B0B0C"      # opencode surface black
FG = "#EDEDED"      # opencode primary text
DOT = "#22C55E"     # live indicator
SUB = "#A1A1AA"     # opencode muted text
BORDER = "#27272A"  # opencode subtle border
WIDTH, HEIGHT = 560, 62

_messages: queue.Queue = queue.Queue()
_manager = None
_lock = threading.Lock()


class _OverlayThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__(name="computer-use-overlay", daemon=True)
        self.root = None
        self._after_id = None

    def run(self) -> None:
        try:
            import tkinter as tk
        except Exception as e:  # noqa: BLE001
            log.warning(f"overlay unavailable (no tkinter): {e}")
            return
        root = tk.Tk()
        self.root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=BG)

        frame = tk.Frame(root, bg=BG, padx=18, pady=9,
                         highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=True)
        dot = tk.Label(frame, text="\u25cf", fg=DOT, bg=BG,
                       font=("Segoe UI", 13))
        dot.pack(side="left")
        texts = tk.Frame(frame, bg=BG)
        texts.pack(side="left", padx=(10, 0))
        self._title = tk.Label(texts, text="OpenCode using your computer",
                               fg=FG, bg=BG, font=("Segoe UI", 11, "bold"))
        self._title.pack(anchor="w")
        self._sub = tk.Label(texts, fg=SUB, bg=BG, font=("Segoe UI", 9))
        self._sub.pack(anchor="w")
        self._sub.config(text="Do not touch mouse / keyboard \u2014 \u043d\u0435 \u043c\u0435\u0448\u0430\u0439\u0442\u0435")
        # Alpha-based visibility: the window stays mapped from birth (this is
        # the only reliably-working path for overrideredirect on Win10).
        # Hidden = fully transparent; shown = 0.94. Never withdraw/deiconify.
        self._place()
        try:
            root.attributes("-alpha", 0.0)
            root.update_idletasks()
            root.update()
        except Exception:
            pass
        self._click_through()
        root.after(100, self._pump)
        log.info("overlay thread started")
        root.mainloop()

    def _click_through(self) -> None:
        try:
            user32 = ctypes.windll.user32
            hwnd = self.root.winfo_id()
            ex = user32.GetWindowLongW(hwnd, -20)
            user32.SetWindowLongW(hwnd, -20, ex | 0x80000 | 0x20)
        except Exception as e:  # noqa: BLE001
            log.debug(f"overlay click-through failed: {e}")

    def _place(self) -> None:
        try:
            from .monitors import get_monitor, list_monitors
            mons = list_monitors()
            if Settings.single_monitor_mode():
                m = get_monitor(mons, Settings.locked_monitor())
            else:
                m = next((x for x in mons if x.primary), mons[0])
            x = m.x + (m.width - WIDTH) // 2
            y = m.y + 16
        except Exception:
            x, y = 100, 16
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    def _show(self, text: str | None) -> None:
        if text:
            parts = text.split("\n", 1)
            self._title.config(text=parts[0][:90])
            if len(parts) > 1:
                self._sub.config(text=parts[1][:110])
        self._place()
        try:
            self.root.update_idletasks()
            self.root.lift()
            self.root.attributes("-alpha", 0.94)
            self.root.update()
        except Exception:
            pass
        self._click_through()

    def _hide(self) -> None:
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            self.root.attributes("-alpha", 0.0)
        except Exception:
            pass

    def _touch(self, idle_sec: float) -> None:
        self._show(Settings.overlay_text())
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        ms = max(1, int(idle_sec * 1000))
        self._after_id = self.root.after(ms, self._hide)

    def _pump(self) -> None:
        try:
            while True:
                cmd = _messages.get_nowait()
                op = cmd[0]
                if op == "show":
                    self._show(cmd[1])
                elif op == "hide":
                    self._hide()
                elif op == "touch":
                    self._touch(cmd[1])
                elif op == "exit":
                    self._hide()
                    self.root.after(100, self.root.destroy)
                    return
        except queue.Empty:
            pass
        except Exception as e:  # noqa: BLE001
            log.debug(f"overlay pump: {e}")
        try:
            self.root.after(100, self._pump)
        except Exception:
            pass


def _ensure() -> bool:
    global _manager
    with _lock:
        if _manager is not None:
            return _manager.is_alive()
        try:
            import tkinter  # noqa: F401
        except Exception as e:  # noqa: BLE001
            log.warning(f"overlay unavailable: {e}")
            return False
        _manager = _OverlayThread()
        _manager.start()
        return True


def show(text: str | None = None) -> dict:
    """Show banner sticky (until hide)."""
    if not _ensure():
        return {"shown": False, "reason": "tkinter unavailable"}
    _messages.put(("show", text or Settings.overlay_text()))
    log.info("overlay shown")
    return {"shown": True, "sticky": True}


def hide() -> dict:
    if _manager is None or not _manager.is_alive():
        return {"shown": False}
    _messages.put(("hide",))
    log.info("overlay hidden")
    return {"shown": False}


def touch() -> None:
    """Show (if hidden) + restart idle auto-hide timer. Cheap; call often."""
    if not Settings.overlay_auto():
        return
    if not _ensure():
        return
    _messages.put(("touch", Settings.overlay_idle_sec()))
