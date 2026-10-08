"""Restart test (Tab+Enter) and screenshot the new words."""
import time


def log(*a):
    print(" ".join(str(x) for x in a).encode("ascii", "replace").decode(),
          flush=True)


from opencode_computer_use import capture, keyboard, monitors

mons = monitors.list_monitors()
m0 = next(m for m in mons if m.id == 0)
keyboard.press_key("TAB")
time.sleep(0.3)
keyboard.press_key("ENTER")
time.sleep(1.2)
cap = capture.capture_monitor(m0, scale=0.6)
open(r"C:\Users\NoName\Desktop\opencode-mcp\mt_words.png", "wb").write(cap.png)
log("next words shot")
