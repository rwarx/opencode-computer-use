# OpenCode Computer Use — локальный визуальный контроль Windows-ПК

MCP-сервер (stdio), дающий OpenCode **«глаза и руки»**: скриншоты,
DPI-корректная мышь, Unicode-клавиатура (латиница + кириллица), управление
окнами, UI Automation, OCR-fallback, batch-действия, ожидания/проверки,
safety-слой и emergency stop.

Без облаков. Без выполнения shell-команд. Только управление GUI.

![баннер](docs/images/01-banner.png)

- Транспорт: **stdio** · Клиент: **OpenCode** (совместим с другими MCP-клиентами)
- Платформа: **Windows 10/11 x64** (разработано и проверено на Windows 10)
- Язык: **Python 3.10+** (`ctypes` + `mss` + официальный MCP SDK)

## Возможности

- `computer_screenshot` — монитор / все мониторы / регион, downscaling с
  сообщением масштаба, результат — MCP-**изображение**
- 8 инструментов мыши: move, click, double-click, down, up, drag, scroll,
  position (`left|right|middle`), точность через `SendInput VIRTUALDESK|ABSOLUTE`
- 5 инструментов клавиатуры: type (Unicode), key, hotkey, key down/up;
  clipboard-fallback для длинного текста
- 6 оконных инструментов: list, active, focus, minimize, maximize, restore
- OCR: `computer_ocr`, `computer_find_text`, `computer_click_text`
  (опционально `rapidocr-onnxruntime`, офлайн)
- UI Automation: `computer_ui_tree`, `computer_find_element`,
  `computer_invoke_element` (опционально `comtypes`, офлайн)
- Приоритет поиска элемента: **UIA → OCR → визуальные координаты**
- `screenshot_after` у действий: скриншот результата сразу в ответе
- `computer_batch` — последовательность действий, остановка на первой ошибке
- `computer_wait`, `computer_wait_for_text`, `computer_wait_for_window`,
  `computer_element_exists`
- **Single-monitor lock**: агент физически не может выйти за пределы монитора
- Экранный баннер **«OpenCode using your computer»** в тёмной теме OpenCode
  (click-through, сам появляется при работе, сам прячется в простое)
- Безопасность: нет shell/PowerShell/shutdown-инструментов; safe/autonomous
  режимы; `computer_emergency_stop`

## Архитектура

```text
OpenCode ── MCP/stdio ──► Computer Use MCP Server (server.py)
                              ├── capture.py      скриншоты через mss
                              ├── mouse.py        SendInput VIRTUALDESK|ABSOLUTE
                              ├── keyboard.py     SendInput UNICODE + clipboard
                              ├── monitors.py     EnumDisplayMonitors + DPI
                              ├── windows_mgr.py  EnumWindows/focus/show
                              ├── ocr.py          RapidOCR (опционально)
                              ├── uia.py          UIAutomationCore (опционально)
                              ├── coords.py       CoordinateMapper
                              ├── safety.py       политики + emergency stop
                              └── config.py       настройки + лог в stderr
```

Конвейер координат (никогда не считаем screenshot px == screen px):

```text
координаты модели ──(/scale)──► px скриншота ──(+origin)──► виртуальный десктоп
      ──► абсолютные единицы SendInput / физические rect UIA
```

Цикл агента: `SCREENSHOT → ANALYZE → ACTION(+screenshot_after) → VERIFY → …`

## Установка

```powershell
git clone <repo> opencode-computer-use
cd opencode-computer-use
pip install -e .
pip install -e ".[ocr]"    # поиск текста (опционально, офлайн)
pip install -e ".[uia]"    # дерево UI Automation (опционально, офлайн)
pip install -e ".[all]"    # всё сразу
```

Права Windows: нужна **активная desktop-сессия** (разблокированный экран).
Админ не требуется (кроме управления elevated-окнами). Файрвол может спросить
разрешение — только локально.

## Конфигурация OpenCode

В `opencode.json` (см. `opencode.json.example`):

```json
{
  "mcp": {
    "computer-use": {
      "type": "local",
      "command": ["python", "-m", "opencode_computer_use"],
      "enabled": true,
      "timeout": 60000
    }
  }
}
```

Перезапустите OpenCode → появятся `computer_*` инструменты. Проверка:
«покажи мониторы» → `computer_list_monitors`.

## Инструменты (35)

Экран/мониторы: `computer_screenshot`, `computer_list_monitors`.
Мышь: `computer_mouse_move/click/double_click/down/up/drag/scroll/position`.
Клавиатура: `computer_type/key/hotkey/key_down/key_up`.
Окна: `computer_list_windows/get_active_window/focus_window/minimize_window/maximize_window/restore_window`.
OCR: `computer_ocr/find_text/click_text`.
UIA: `computer_ui_tree/find_element/invoke_element`.
Синхронизация: `computer_wait/wait_for_text/wait_for_window/element_exists`.
Поток: `computer_batch`, `computer_emergency_stop`.
Баннер: `computer_overlay_show`, `computer_overlay_hide`.

## Экранный баннер

Пока агент управляет компьютером, сверху по центру висит topmost-плашка
в тёмной теме OpenCode: зелёная точка + «OpenCode using your computer» +
«Do not touch mouse / keyboard». Она **click-through**
(`WS_EX_TRANSPARENT`): клики проходят сквозь неё, автоматизации она не мешает.
Авто-режим показывает её при первом действии ввода и прячет через
`COMPUTER_USE_OVERLAY_IDLE_SEC` секунд простоя; `computer_overlay_show`
закрепляет, `computer_overlay_hide` убирает.

Ответы — agent-friendly: что произошло, позиция курсора, активное окно,
опционально скриншот inline.

## Примеры

Notepad end-to-end (реально проверено):

![демо notepad](docs/images/02-notepad-demo.png)

```text
hotkey WIN+R → type "notepad" → key ENTER → wait_for_window "Notepad"
→ type "Hello from OpenCode! Привет мир!" → hotkey CTRL+S
→ type "C:\Users\you\Desktop\hello.txt" → key ENTER → screenshot
```

Работа только с одним монитором (`config/opencode.single-monitor.json.example`):

```json
{ "env": { "COMPUTER_USE_SINGLE_MONITOR": "1", "COMPUTER_USE_MONITOR": "1" } }
```

## Multi-monitor и DPI

- Мониторы с виртуальными origin (возможны отрицательные), per-monitor DPI
  (1.0/1.25/1.5/2.0), флаг primary.
- Процесс — per-monitor-V2 DPI aware; курсор через `GetPhysicalCursorPos`.
- Юнит-тесты (`tests/test_coords.py`): отрицательные смещения, регионы,
  DPI 150%, углы абсолютных координат.
- `monitor="all"` склеивает виртуальный десктоп.

## Безопасность

- Нет shell, PowerShell, файловых, реестровых, shutdown/reboot инструментов.
- `COMPUTER_USE_ALLOW_MOUSE/KEYBOARD/WINDOW` (по умолчанию 1) отключают классы ввода.
- Safe mode (по умолчанию): рискованный текст (shutdown/format/delete/покупки,
  EN+RU паттерны) отклоняется; `COMPUTER_USE_AUTONOMOUS=1` разрешает.
- `computer_emergency_stop` отключает мышь+клавиатуру; `reset=true` включает.
- Введённый текст не логируется (только длина). Логи — только в **stderr**.

## Troubleshooting

| Симптом | Решение |
|---|---|
| `SendInput keyboard failed err=87` | Исправлено в 0.1.0 (union 40 байт); обновитесь |
| Клики мимо на mixed-DPI | Проверьте `computer_list_monitors` (scale), уберите DPI-unaware хуки |
| OCR/UIA возвращают ERROR | `pip install -e ".[ocr]"` / `".[uia]"` |
| Таймауты вызовов | Timeout клиента 60000; скриншоты со `scale` 0.5 в 4 раза легче |
| Чёрные скриншоты | Сессия заблокирована или RDP свёрнут — нужен активный десктоп |

## Разработка и тесты

```powershell
pip install -e ".[all]"
python -m pytest tests/test_coords.py -q
python tests/e2e_mcp_calls.py
$env:COMPUTER_USE_SINGLE_MONITOR=1; $env:COMPUTER_USE_MONITOR=1; python tests/e2e_lock.py
python tests/e2e_notepad.py     # полный цикл: Notepad → файл на Desktop
python tests/e2e_cyrillic.py    # побайтовая проверка кириллицы
```

Переменные окружения — см. английскую README (раздел Environment variables).

## Лицензия

MIT. См. LICENSE.
