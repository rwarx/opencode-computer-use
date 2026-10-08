# Changelog

## 0.1.1 — 2026-10-08

- Faster screenshots: bilinear downscale (was Lanczos), PNG `compress_level=3`
  (was 6), new `COMPUTER_USE_RESAMPLE` / `COMPUTER_USE_PNG_COMPRESS` knobs
- Fixed JPEG screenshots mislabeled as `image/png` (now `image/jpeg`)
- Fixed risky-text filter missing `format D:` (trailing `\b` bug, caught by tests)
- 29 automated pytest tests: coords, safety policy, keyboard mapping, live MCP
  protocol (PNG+JPEG magic bytes, overlay, e-stop, batch, safe-mode refusal)
- `tests/bench_shots.py` benchmark; fast-loop recipe `scale=0.5 + jpeg=true`
  (~30 ms / ~0.1 MB vs ~120 ms / ~2.1 MB default)

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
