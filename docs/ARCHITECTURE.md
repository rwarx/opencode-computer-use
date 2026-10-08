# Architecture

## Big picture

```text
OpenCode (LLM + built-in tools)
   │  MCP / stdio (JSON-RPC, newline-delimited)
   ▼
opencode_computer_use.server (MCPServer, 35 tools, never raises)
   ├── capture.py      mss screenshots: monitor / all / region, PNG, scale report
   ├── mouse.py        SendInput MOUSEEVENTF_VIRTUALDESK|ABSOLUTE (DPI-correct)
   ├── keyboard.py     SendInput KEYEVENTF_UNICODE + clipboard fallback
   ├── monitors.py     EnumDisplayMonitors + GetDpiForMonitor, per-monitor-V2 aware
   ├── windows_mgr.py  EnumWindows, focus/min/max/restore, active window
   ├── ocr.py          RapidOCR wrapper (optional dep, graceful without it)
   ├── uia.py          UIAutomationCore via comtypes (optional dep)
   ├── coords.py       CoordinateMapper — single source of truth (pure, tested)
   ├── overlay.py      tkinter banner thread (topmost, click-through, auto-hide)
   ├── safety.py       policy gates + emergency stop + risky-text filter
   └── config.py       env settings + stderr-only logging
```

## Coordinate pipeline

The one rule: **screenshot pixel ≠ screen pixel**. Every click flows through:

```text
model pixel (mx,my) in the DOWNscaled image it saw
   ── ÷ scale ──► screenshot-native pixel
   ── + monitor origin (+ region offset) ──► virtual-desktop pixel
   ── enforce_single_monitor (clamp when locked) ──► SendInput 0..65535
```

- `coords.py` holds the pure math (`model_to_screenshot`,
  `screenshot_to_virtual`, `virtual_to_abs`, `enforce_single_monitor`).
- `monitors.py` supplies origins (negative allowed) and per-monitor DPI scale.
- Cursor is read with `GetPhysicalCursorPos` (DPI-correct).
- Unit tests in `tests/test_coords.py` pin: 100/125/150% DPI, negative
  origins, region offsets, absolute-unit corners.

## Why tools never raise

The MCP Python SDK can hang a `tools/call` when the handler raises. Every
tool is wrapped in `@safe`: exceptions become inline `ERROR (tool): ...`
text, which is also better UX for the agent loop (the model reads the error
and retries instead of seeing a protocol failure).

## Element resolution order

```text
UI Automation (exact rects, no vision)
        ↓ miss / unavailable
OCR (text → center coords)
        ↓ miss
visual coordinates (model reads screenshot, divides by reported scale)
```

## Overlay design

`overlay.py` runs tkinter in a daemon thread; all Tk calls stay in that
thread, commands arrive via queue. Visibility is alpha-based (0.0 hidden /
0.94 shown) because withdraw/deiconify on overrideredirect windows is
unreliable on Win10. `WS_EX_TRANSPARENT` makes it click-through so it can
never block automation. Auto-mode hooks into `safety.check_input_allowed`:
any mouse/keyboard tool call touches the banner and restarts the idle timer.

## Safety model

- No shell/PowerShell/file/registry/shutdown tools exist in this server.
  Shell stays OpenCode's responsibility.
- `COMPUTER_USE_ALLOW_MOUSE/KEYBOARD/WINDOW` disable input classes.
- Safe mode (default): risky text patterns (shutdown/format/delete/purchase,
  EN+RU) are refused; `COMPUTER_USE_AUTONOMOUS=1` opts out.
- Emergency stop is a process-global flag; input tools refuse while set.
- Typed text is never logged (length only); logs go to stderr (stdout is
  reserved for MCP framing).
