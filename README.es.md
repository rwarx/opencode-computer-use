# OpenCode Computer Use — control visual local del PC Windows

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [中文](README.zh.md)

Servidor MCP (stdio) que da a OpenCode **ojos y manos** sobre un PC Windows:
capturas de pantalla, ratón con DPI correcto, teclado Unicode, gestión de
ventanas, UI Automation, fallback OCR, acciones por lotes, primitivas de
espera/verificación y capa de seguridad con parada de emergencia.

Sin nube. Sin ejecución de shell. Solo control GUI.

- Transporte: **stdio** · Cliente: **OpenCode** (compatible con otros clientes MCP)
- Plataforma: **Windows 10/11 x64** (desarrollado y verificado en Windows 10)
- Lenguaje: **Python 3.10+** (`ctypes` + `mss` + SDK oficial de MCP)

## Capacidades

- `computer_screenshot` — por monitor / todos / región, con reporte de escala,
  devuelto como **imagen** MCP
- 8 herramientas de ratón: move, click, double-click, down, up, drag, scroll,
  position (`left|right|middle`), precisas vía `SendInput VIRTUALDESK|ABSOLUTE`
- 5 de teclado: type (Unicode: latín + cirílico), key, hotkey, key down/up;
  fallback al portapapeles para textos largos
- 6 de ventanas: list, active, focus, minimize, maximize, restore
- OCR: `computer_ocr`, `computer_find_text`, `computer_click_text`
  (opcional `rapidocr-onnxruntime`, offline)
- UI Automation: `computer_ui_tree`, `computer_find_element`,
  `computer_invoke_element` (opcional `comtypes`, offline)
- Prioridad de búsqueda: **UIA → OCR → coordenadas visuales**
- `screenshot_after` en acciones: captura del resultado en la respuesta
- `computer_batch` — acciones secuenciales, se detiene al primer error
- `computer_wait`, `computer_wait_for_text`, `computer_wait_for_window`,
  `computer_element_exists`
- **Bloqueo a un monitor**: el agente físicamente no puede salir de un monitor
- Banner en pantalla **«OpenCode using your computer»** (tema oscuro,
  click-through, auto-visible con actividad, auto-oculto en inactividad)
- Seguridad: sin shell/PowerShell/apagado; modos safe/autonomous;
  `computer_emergency_stop`

## Arquitectura

```text
OpenCode ── MCP/stdio ──► servidor (server.py)
   ├── capture.py      capturas por monitor (mss)
   ├── mouse.py        SendInput VIRTUALDESK|ABSOLUTE
   ├── keyboard.py     SendInput UNICODE + portapapeles
   ├── monitors.py     EnumDisplayMonitors + DPI por monitor
   ├── windows_mgr.py  EnumWindows/focus/show
   ├── ocr.py          RapidOCR (opcional)
   ├── uia.py          UIAutomationCore vía comtypes (opcional)
   ├── coords.py       CoordinateMapper (verificado con tests)
   ├── overlay.py      banner tkinter (topmost, click-through)
   ├── safety.py       políticas + parada de emergencia
   └── config.py       ajustes env + log solo a stderr
```

Bucle del agente: `SCREENSHOT → ANALYZE → ACTION(+screenshot_after) → VERIFY → …`

![banner](docs/images/01-banner.png)

## Instalación

```powershell
git clone <repo> opencode-computer-use
cd opencode-computer-use
pip install -e .
pip install -e ".[ocr]"    # búsqueda de texto (opcional, offline)
pip install -e ".[uia]"    # árbol UI Automation (opcional, offline)
pip install -e ".[all]"    # todo
```

Windows: se necesita una **sesión de escritorio activa** (pantalla
desbloqueada). Sin admin (salvo para ventanas elevadas).

## Configuración OpenCode

En `opencode.json` (ver `opencode.json.example`):

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

Reinicia OpenCode → aparecen las herramientas `computer_*`.

## Herramientas (36)

Pantalla: `computer_screenshot`, `computer_list_monitors`.
Ratón: `computer_mouse_move/click/double_click/down/up/drag/scroll/position`.
Teclado: `computer_type/key/hotkey/key_down/key_up`.
Ventanas: `computer_list_windows/get_active_window/focus_window/minimize_window/maximize_window/restore_window`.
OCR: `computer_ocr/find_text/click_text`.
UIA: `computer_ui_tree/find_element/invoke_element`.
Sincronización: `computer_wait/wait_for_text/wait_for_window/element_exists`.
Flujo: `computer_batch`, `computer_emergency_stop`.
Banner: `computer_overlay_show`, `computer_overlay_hide`.

## Ejemplo

Notepad de principio a fin (verificado en vivo):

```text
hotkey WIN+R → type "notepad" → key ENTER → wait_for_window "Notepad"
→ type "Hello from OpenCode!" → hotkey CTRL+S → type ruta → key ENTER
```

## Multi-monitor y DPI

Orígenes negativos permitidos, DPI por monitor (1.0/1.25/1.5/2.0), proceso
per-monitor-V2 DPI aware, cursor vía `GetPhysicalCursorPos`. Tests en
`tests/test_coords.py`. `monitor="all"` une el escritorio virtual.

## Seguridad

Sin shell, PowerShell, archivos, registro, apagado ni reinicio — solo GUI.
`COMPUTER_USE_ALLOW_MOUSE/KEYBOARD/WINDOW` desactivan clases de entrada.
Modo safe (defecto): texto riesgoso rechazado;
`COMPUTER_USE_AUTONOMOUS=1` lo permite. El texto tecleado nunca se registra.
Logs solo a **stderr**.

## Desarrollo y tests

```powershell
pip install -e ".[all]"
python -m pytest tests/test_coords.py -q
python tests/e2e_notepad.py     # ciclo completo: Notepad → archivo en Desktop
python tests/e2e_cyrillic.py    # roundtrip cirílico byte-exacto
```

## Licencia

MIT. Ver LICENSE.
