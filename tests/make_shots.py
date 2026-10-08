"""Capture repo screenshots: 01 banner strip, 02 notepad demo. Cleans up after."""
import os
import time

from opencode_computer_use import capture, keyboard, monitors, overlay, windows_mgr

IMG = r"C:\Users\NoName\Desktop\opencode-mcp\docs\images"
mons = monitors.list_monitors()
prim = next(m for m in mons if m.primary)

# 01 — banner over live desktop
overlay.show()
time.sleep(1.5)
cap = capture.capture_monitor(prim, region=(prim.width // 2 - 450, 0, 900, 110))
open(os.path.join(IMG, "01-banner.png"), "wb").write(cap.png)
overlay.hide()
print("01-banner saved", flush=True)

# 02 — notepad agent loop result
TARGET = os.path.join(os.path.expanduser("~"), "Desktop", "opencode_demo.txt")
if os.path.exists(TARGET):
    os.remove(TARGET)
keyboard.hotkey("WIN", "R")
time.sleep(0.8)
keyboard.type_text("notepad")
keyboard.press_key("ENTER")
for _ in range(30):
    time.sleep(0.5)
    wins = windows_mgr.list_windows(limit=200)
    np_ = next((w for w in wins if "notepad.exe" in (w["process"] or "").lower()), None)
    if np_:
        break
assert np_, "notepad did not open"
windows_mgr.focus_window(np_["hwnd"])
time.sleep(0.5)
keyboard.type_text("Hello from OpenCode!")
keyboard.press_key("ENTER")
keyboard.type_text("Screenshot -> Analyze -> Action -> Verify")
keyboard.hotkey("CTRL", "S")
time.sleep(1.0)
keyboard.type_text(TARGET)
keyboard.press_key("ENTER")
time.sleep(1.0)
assert os.path.exists(TARGET)
cap2 = capture.capture_monitor(prim, scale=0.5)
open(os.path.join(IMG, "02-notepad-demo.png"), "wb").write(cap2.png)
print("02-notepad-demo saved", cap2.width, cap2.height, flush=True)
keyboard.hotkey("ALT", "F4")
time.sleep(0.8)
os.remove(TARGET)
print("SHOTS DONE", flush=True)
