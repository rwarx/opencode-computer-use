"""Step 2: dismiss translate popup, focus words, screenshot test."""
import time


def log(*a):
    print(" ".join(str(x) for x in a).encode("ascii", "replace").decode(),
          flush=True)


from opencode_computer_use import capture, coords, keyboard, monitors, mouse

mons = monitors.list_monitors()
m0 = next(m for m in mons if m.id == 0)
keyboard.press_key("ESC")  # dismiss translate popup
time.sleep(0.5)
# click on words area to focus (model px in 0.5 shot)
sx, sy = coords.model_to_screenshot(300, 235, 0.5)
vx, vy = coords.screenshot_to_virtual(sx, sy, m0)
mouse.click_at(vx, vy)
time.sleep(0.8)
cap = capture.capture_monitor(m0, scale=0.6)
open(r"C:\Users\NoName\Desktop\opencode-mcp\mt_03_test.png", "wb").write(cap.png)
log("shot", cap.width, cap.height)
