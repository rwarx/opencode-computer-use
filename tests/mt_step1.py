"""Step 1: restore Chrome on monitor 0 and open monkeytype.com."""
import time


def log(*a):
    print(" ".join(str(x) for x in a).encode("ascii", "replace").decode(),
          flush=True)


from opencode_computer_use import keyboard, windows_mgr

wins = windows_mgr.list_windows(limit=100)
chromes = [w for w in wins if (w["process"] or "").lower() == "chrome.exe"]
log("chromes:", [(w["hwnd"], w["x"], w["y"], w["width"]) for w in chromes])
big = max(chromes, key=lambda w: w["width"] * w["height"])
res = windows_mgr.focus_window(big["hwnd"])
log("focus focused:", res["focused"])
time.sleep(1.0)
a = windows_mgr.get_active_window()
log("active:", a["process"], a["x"], a["y"], a["width"], a["height"])
assert a["process"].lower() == "chrome.exe", "chrome not active, abort typing"
keyboard.hotkey("CTRL", "L")
time.sleep(0.5)
keyboard.type_text("monkeytype.com")
time.sleep(0.3)
keyboard.press_key("ENTER")
time.sleep(4.0)
log("navigated")
