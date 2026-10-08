# Changelog

## 0.1.0 — 2026-10-08

First public release. Verified live on Windows 10 (dual-monitor).

- 35 MCP tools (stdio): screenshot, 8× mouse, 5× keyboard, 6× window,
  3× OCR, 3× UI Automation, 4× wait/verify, batch, emergency stop, 2× overlay
- DPI-correct `CoordinateMapper` (100/125/150/200%, negative origins,
  per-monitor DPI) with unit tests
- Single-monitor lock mode (`COMPUTER_USE_SINGLE_MONITOR` + `COMPUTER_USE_MONITOR`)
- `screenshot_after` inline result images for the agent loop
- Unicode typing (Latin + Cyrillic verified byte-exact) + clipboard fallback
- UI Automation via comtypes (tree/find/invoke), RapidOCR fallback (optional deps)
- Safety: GUI-only (no shell), safe/autonomous modes, emergency stop kill-switch
- Click-through "OpenCode using your computer" banner in OpenCode dark theme,
  auto-show on input, auto-hide when idle
- Docs: README (EN/RU), ARCHITECTURE, RESEARCH, OpenCode config examples
- E2E verified: Notepad open→type→save→screenshot→close, Cyrillic roundtrip,
  cursor circles, overlay show/hide, single-monitor clamp
