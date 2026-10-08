# Phase 1 research — existing Computer Use solutions (Oct 2026)

Evaluated before writing any code. Conclusion: no existing project meets all
requirements (DPI-correct multi-monitor + single-monitor lock + screenshot_after
loop + safety separation + 15–25 agent-oriented tools), so a clean Python
implementation was built, reusing proven ideas.

## 1. Reference architectures

- **OpenAI CUA / Operator**: pure-vision loop (screenshot as observation;
  coord / content / function actions), user confirmations before side effects,
  watch mode on sensitive sites. Adopted: screenshot-first loop, safe-by-default.
- **OpenCUA paper (Stanford/UW/CMU)**: formalizes observation=screenshot,
  action=mouse+keyboard. Confirms vision-first design.
- **Microsoft Windows 365 for Agents MCP**: desktop interaction + UIA tree +
  fuzzy window match + protection of critical processes + timing/sync tools.
  Closest public tool-surface reference for our tool naming.

## 2. Existing MCP servers (and why each falls short)

| Project | Stack | Gap |
|---|---|---|
| `tdav/Mcp.ComputerUse` | C# .NET 10 Native AOT, 16 tools, vision-first scaled coords, SendInput VIRTUALDESK, stderr logging | Exposes files + PowerShell (violates GUI-only safety); no single-monitor lock, no OCR/UIA depth, no batch/wait/verify loop |
| `danielsimonjr/Windows-MCP` | C#, 60+ tools | 60+ tools = agent confusion; mixes shell/file/registry/disk/network — security risk; opposite of minimal surface |
| `epnielsen/Winapp-MCP` | C# FlaUI UIA3 | UIA only: no mouse/keyboard/screenshot loop — blind without screenshots |
| `felipethecosta/computer-use-mcp` | TS, PowerShell `Add-Type` per call | 200–500 ms overhead per action; primary monitor only; no DPI handling |
| `chigwell/pyautogui-mcp`, `mcp-pyautogui` | Python PyAutoGUI | PyAutoGUI multi-monitor DPI bugs (asweigart/pyautogui#413, pywinauto#1281); corner failsafe kills agents; no UIA/OCR/window mgmt |
| `AB498/computer-control-mcp` | PyAutoGUI + RapidOCR + ONNX | Same PyAutoGUI coordinate bugs underneath |
| `winvision-mcp` | Python, annotated screenshots + UIA invoke + MCP sampling QA | Good ideas (adopted: annotated context, invoke-without-coords); but QA-oriented, not a full control loop |
| `Yueqi-Wang-795/opencode-gui-bridge` | UIA/OCR/CDP snapshots | No clean single-monitor enforcement story |
| `kathizeal/WinUI_MCP` | C# WinUI3-only | Single-framework scope |

## 3. Key technical findings applied to this project

1. **DPI scaling breaks naive automation.** PyAutoGUI assumes uniform scaling
   and mis-clicks on mixed-DPI desktops (#413); pywinauto clicks drift per
   monitor (#1281); UIA returns physical coords while unaware clients read
   logical ones (MSDN). → Dedicated `CoordinateMapper` + per-monitor-V2 DPI
   awareness + `GetPhysicalCursorPos` + `VIRTUALDESK|ABSOLUTE` SendInput.
2. **PowerShell-per-action is too slow.** → Pure `ctypes` SendInput, no
   subprocesses on the input hot path.
3. **`INPUT` struct size matters.** `INPUT` with keyboard member alone is
   32 bytes; Windows requires 40 (union size). Wrong size → `ERROR_INVALID_PARAMETER`
   (87), all keyboard input dead. Found by our own E2E, fixed with padded union.
4. **MCP SDK Elyria hangs on raising tools / validates returns.** → Tools never
   raise; errors return as inline text (better for the agent loop anyway).
5. **Tool count vs completeness.** Guidance says 15–25; the required surface
   (mouse×8, keys×5, windows×6, OCR×3, UIA×3, wait/verify×4, batch, stop,
   screenshot, monitors) lands at 33 focused tools. Kept all — each maps to a
   distinct agent need; shell/file/registry tools deliberately excluded.
6. **Language: Python.** `ctypes` covers Win32 input/monitor/window APIs with
   zero overhead; `mss` = fastest GDI/DXGI capture; `comtypes` = UIA;
   `rapidocr-onnxruntime` = offline OCR. No NativeAOT toolchain, trivial
   `pip install`, OpenCode users already have Python. C# AOT (~10 MB exe)
   advantage not worth the iteration cost; Rust/C++ unnecessary.
