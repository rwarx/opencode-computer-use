# OpenCode Computer Use — lokale visuelle Windows-PC-Steuerung

[English](README.md) · [Русский](README.ru.md) · [Español](README.es.md) · [中文](README.zh.md)

MCP-Server (stdio), der OpenCode **Augen + Hände** auf einem Windows-PC gibt:
Screenshots, DPI-korrekte Maus, Unicode-Tastatur, Fensterverwaltung,
UI Automation, OCR-Fallback, Batch-Aktionen, Wait/Verify-Primitive und
Sicherheitslayer mit Not-Stopp.

Keine Cloud. Keine Shell-Ausführung. Nur GUI-Steuerung.

- Transport: **stdio** · Client: **OpenCode** (andere MCP-Clients kompatibel)
- Plattform: **Windows 10/11 x64** (entwickelt und verifiziert auf Windows 10)
- Sprache: **Python 3.10+** (`ctypes` + `mss` + offizielles MCP-SDK)

## Funktionen

- `computer_screenshot` — pro Monitor / alle / Region, mit Scale-Report,
  als MCP-**Bild** zurückgegeben
- 8 Maus-Tools: move, click, double-click, down, up, drag, scroll, position
  (`left|right|middle`), präzise via `SendInput VIRTUALDESK|ABSOLUTE`
- 5 Tastatur-Tools: type (Unicode: Latein + Kyrillisch), key, hotkey,
  key down/up; Clipboard-Fallback für lange Texte
- 6 Fenster-Tools: list, active, focus, minimize, maximize, restore
- OCR: `computer_ocr`, `computer_find_text`, `computer_click_text`
  (optional `rapidocr-onnxruntime`, offline)
- UI Automation: `computer_ui_tree`, `computer_find_element`,
  `computer_invoke_element` (optional `comtypes`, offline)
- Elementsuche: **UIA → OCR → visuelle Koordinaten**
- `screenshot_after` bei Aktionen: Ergebnis-Screenshot inline
- `computer_batch` — sequenzielle Aktionen, Stopp beim ersten Fehler
- `computer_wait`, `computer_wait_for_text`, `computer_wait_for_window`,
  `computer_element_exists`
- **Single-Monitor-Lock**: der Agent kann einen Monitor physisch nicht verlassen
- On-Screen-Banner **„OpenCode using your computer“** (Dark-Theme,
  click-through, auto bei Aktivität, auto-hide im Idle)
- Sicherheit: kein Shell/PowerShell/Shutdown; Safe-/Autonomous-Modi;
  `computer_emergency_stop`

## Architektur

```text
OpenCode ── MCP/stdio ──► Server (server.py)
   ├── capture.py      Screenshots pro Monitor (mss)
   ├── mouse.py        SendInput VIRTUALDESK|ABSOLUTE
   ├── keyboard.py     SendInput UNICODE + Clipboard
   ├── monitors.py     EnumDisplayMonitors + DPI pro Monitor
   ├── windows_mgr.py  EnumWindows/focus/show
   ├── ocr.py          RapidOCR (optional)
   ├── uia.py          UIAutomationCore via comtypes (optional)
   ├── coords.py       CoordinateMapper (mit Tests abgesichert)
   ├── overlay.py      tkinter-Banner (topmost, click-through)
   ├── safety.py       Policies + Not-Stopp
   └── config.py       Env-Settings + Logging nur nach stderr
```

Agent-Loop: `SCREENSHOT → ANALYZE → ACTION(+screenshot_after) → VERIFY → …`

![Banner](docs/images/01-banner.png)

## Installation

```powershell
git clone <repo> opencode-computer-use
cd opencode-computer-use
pip install -e .
pip install -e ".[ocr]"    # Textsuche (optional, offline)
pip install -e ".[uia]"    # UI-Automation-Baum (optional, offline)
pip install -e ".[all]"    # alles
```

Windows: **aktive Desktop-Sitzung** erforderlich (entsperrter Bildschirm).
Kein Admin nötig (außer für elevated Fenster).

## OpenCode-Konfiguration

In `opencode.json` (siehe `opencode.json.example`):

```json
{
  "mcp": {
    "computer-use": {
      "type": "local",
      "command": ["python", "-m", "opencode_computer_use"],
      "enabled": true,
      "timeout": 60000,
      "environment": {
        "COMPUTER_USE_SINGLE_MONITOR": "0",
        "COMPUTER_USE_AUTONOMOUS": "0",
        "COMPUTER_USE_OVERLAY_AUTO": "1"
      }
    }
  }
}
```

OpenCode neu starten → `computer_*`-Tools erscheinen.

## Tools (36)

Screen: `computer_screenshot`, `computer_list_monitors`.
Maus: `computer_mouse_move/click/double_click/down/up/drag/scroll/position`.
Tastatur: `computer_type/key/hotkey/key_down/key_up`.
Fenster: `computer_list_windows/get_active_window/focus_window/minimize_window/maximize_window/restore_window`.
OCR: `computer_ocr/find_text/click_text`.
UIA: `computer_ui_tree/find_element/invoke_element`.
Sync: `computer_wait/wait_for_text/wait_for_window/element_exists`.
Flow: `computer_batch`, `computer_emergency_stop`.
Banner: `computer_overlay_show`, `computer_overlay_hide`.

## Beispiel

Notepad Ende-zu-Ende (live verifiziert):

```text
hotkey WIN+R → type "notepad" → key ENTER → wait_for_window "Notepad"
→ type "Hello from OpenCode!" → hotkey CTRL+S → Pfad tippen → key ENTER
```

## Multi-Monitor & DPI

Negative Origins erlaubt, DPI pro Monitor (1.0/1.25/1.5/2.0), Prozess
per-monitor-V2-DPI-aware, Cursor via `GetPhysicalCursorPos`. Tests in
`tests/test_coords.py`. `monitor="all"` verheftet den virtuellen Desktop.

## Sicherheit

Kein Shell, PowerShell, Dateien, Registry, Shutdown/Reboot — nur GUI.
`COMPUTER_USE_ALLOW_MOUSE/KEYBOARD/WINDOW` deaktivieren Eingabeklassen.
Safe-Modus (Default): riskanter Text wird abgelehnt;
`COMPUTER_USE_AUTONOMOUS=1` erlaubt ihn. Getippter Text wird nie geloggt.
Logs nur nach **stderr**.

## Entwicklung & Tests

```powershell
pip install -e ".[all]"
python -m pytest tests/test_coords.py -q
python tests/e2e_notepad.py     # Vollzyklus: Notepad → Datei auf Desktop
python tests/e2e_cyrillic.py    # byte-exakter Kyrillisch-Roundtrip
```

## Lizenz

MIT. Siehe LICENSE.
