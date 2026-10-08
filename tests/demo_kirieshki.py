"""Live demo: open Notepad, type test word, save on Desktop, leave open."""
import os
import time

from opencode_computer_use import capture, keyboard, monitors, mouse, windows_mgr

TARGET = os.path.join(os.path.expanduser("~"), "Desktop", "kirieshki.txt")
if os.path.exists(TARGET):
    os.remove(TARGET)

print("cursor before:", mouse.position(), flush=True)
keyboard.hotkey("WIN", "R")
time.sleep(0.8)
keyboard.type_text("notepad")
keyboard.press_key("ENTER")
# wait for Notepad window (poll, max 15 s)
notepad = None
for _ in range(30):
    time.sleep(0.5)
    wins = windows_mgr.list_windows(limit=200)
    notepad = next((w for w in wins
                    if "notepad.exe" in (w["process"] or "").lower()), None)
    if notepad:
        break
assert notepad, "notepad did not open"
print("notepad:", notepad["title"], notepad["hwnd"], flush=True)
windows_mgr.focus_window(notepad["hwnd"])
time.sleep(0.5)
keyboard.type_text("kirieshki")
keyboard.hotkey("CTRL", "S")
time.sleep(1.0)
keyboard.type_text(TARGET)
keyboard.press_key("ENTER")
time.sleep(1.0)
assert os.path.exists(TARGET), "save failed"
print("saved bytes:", os.path.getsize(TARGET), flush=True)
# proof screenshot of primary monitor
mons = monitors.list_monitors()
prim = next(m for m in mons if m.primary)
cap = capture.capture_monitor(prim, scale=0.5)
open(r"C:\Temp\opencode\kirieshki.png", "wb").write(cap.png)
print("screenshot saved", cap.width, cap.height, flush=True)
print("cursor after:", mouse.position(), flush=True)
print("DEMO DONE — notepad left open", flush=True)
