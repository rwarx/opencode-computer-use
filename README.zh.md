# OpenCode Computer Use — Windows 本地可视化桌面控制

[English](README.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Deutsch](README.de.md)

MCP 服务器（stdio），为 OpenCode 提供 Windows PC 的**眼睛和双手**：
屏幕截图、DPI 精确鼠标、Unicode 键盘、窗口管理、UI Automation、OCR 兜底、
批量动作、等待/校验原语，以及带紧急停止的安全层。

无云服务。不执行 shell。仅控制 GUI。

- 传输：**stdio** · 客户端：**OpenCode**（兼容其他 MCP 客户端）
- 平台：**Windows 10/11 x64**（在 Windows 10 上开发与验证）
- 语言：**Python 3.10+**（`ctypes` + `mss` + 官方 MCP SDK）

## 功能

- `computer_screenshot` — 单显示器 / 全部 / 区域截图，附带缩放比例，
  以 MCP **图像**返回
- 8 个鼠标工具：move、click、double-click、down、up、drag、scroll、position
 （`left|right|middle`），经 `SendInput VIRTUALDESK|ABSOLUTE` 精确定位
- 5 个键盘工具：type（Unicode：拉丁 + 西里尔）、key、hotkey、key down/up；
  长文本走剪贴板兜底
- 6 个窗口工具：list、active、focus、minimize、maximize、restore
- OCR：`computer_ocr`、`computer_find_text`、`computer_click_text`
 （可选 `rapidocr-onnxruntime`，离线）
- UI Automation：`computer_ui_tree`、`computer_find_element`、
  `computer_invoke_element`（可选 `comtypes`，离线）
- 元素查找优先级：**UIA → OCR → 视觉坐标**
- 动作支持 `screenshot_after`：结果截图直接内联返回
- `computer_batch` — 顺序动作，出错即停
- `computer_wait`、`computer_wait_for_text`、`computer_wait_for_window`、
  `computer_element_exists`
- **单显示器锁定**：agent 物理上无法离开指定显示器
- 屏显横幅 **"OpenCode using your computer"**（深色主题、可点击穿透、
  有操作时自动显示、空闲自动隐藏）
- 安全：无 shell/PowerShell/关机工具；safe/autonomous 模式；
  `computer_emergency_stop`

## 架构

```text
OpenCode ── MCP/stdio ──► 服务器 (server.py)
   ├── capture.py      按显示器截图 (mss)
   ├── mouse.py        SendInput VIRTUALDESK|ABSOLUTE
   ├── keyboard.py     SendInput UNICODE + 剪贴板
   ├── monitors.py     EnumDisplayMonitors + 按显示器 DPI
   ├── windows_mgr.py  EnumWindows/focus/show
   ├── ocr.py          RapidOCR（可选）
   ├── uia.py          comtypes UIAutomationCore（可选）
   ├── coords.py       CoordinateMapper（有测试覆盖）
   ├── overlay.py      tkinter 横幅（置顶、可穿透）
   ├── safety.py       策略 + 紧急停止
   └── config.py       环境变量 + 仅 stderr 日志
```

Agent 循环：`SCREENSHOT → ANALYZE → ACTION(+screenshot_after) → VERIFY → …`

![横幅](docs/images/01-banner.png)

## 安装

```powershell
git clone <repo> opencode-computer-use
cd opencode-computer-use
pip install -e .
pip install -e ".[ocr]"    # 文本搜索（可选，离线）
pip install -e ".[uia]"    # UI Automation 树（可选，离线）
pip install -e ".[all]"    # 全部
```

Windows：需要**活动的桌面会话**（未锁屏）。不需要管理员权限
（操作提权窗口除外）。

## OpenCode 配置

写入 `opencode.json`（见 `opencode.json.example`）：

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

重启 OpenCode → 出现 `computer_*` 工具。

## 工具（36 个）

屏幕：`computer_screenshot`、`computer_list_monitors`。
鼠标：`computer_mouse_move/click/double_click/down/up/drag/scroll/position`。
键盘：`computer_type/key/hotkey/key_down/key_up`。
窗口：`computer_list_windows/get_active_window/focus_window/minimize_window/maximize_window/restore_window`。
OCR：`computer_ocr/find_text/click_text`。
UIA：`computer_ui_tree/find_element/invoke_element`。
同步：`computer_wait/wait_for_text/wait_for_window/element_exists`。
流程：`computer_batch`、`computer_emergency_stop`。
横幅：`computer_overlay_show`、`computer_overlay_hide`。

## 示例

记事本端到端（已实机验证）：

```text
hotkey WIN+R → type "notepad" → key ENTER → wait_for_window "Notepad"
→ type "Hello from OpenCode!" → hotkey CTRL+S → 输入路径 → key ENTER
```

## 多显示器与 DPI

支持负坐标原点、按显示器 DPI（1.0/1.25/1.5/2.0），进程为
per-monitor-V2 DPI 感知，经 `GetPhysicalCursorPos` 读取光标。
测试见 `tests/test_coords.py`。`monitor="all"` 拼接虚拟桌面。

## 安全

无 shell、PowerShell、文件、注册表、关机/重启工具——仅 GUI。
`COMPUTER_USE_ALLOW_MOUSE/KEYBOARD/WINDOW` 可关闭输入类别。
默认 safe 模式：危险文本被拒绝；`COMPUTER_USE_AUTONOMOUS=1` 放行。
输入文本永不记入日志。日志只写 **stderr**。

## 开发与测试

```powershell
pip install -e ".[all]"
python -m pytest tests/test_coords.py -q
python tests/e2e_notepad.py     # 完整循环：记事本 → 保存到桌面
python tests/e2e_cyrillic.py    # 西里尔字节级往返
```

## 许可证

MIT。见 LICENSE。
