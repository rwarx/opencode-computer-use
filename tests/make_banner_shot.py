"""Re-capture banner (EN-only) and tight-crop to the pill, no wallpaper."""
import time

from PIL import Image

from opencode_computer_use import capture, monitors, overlay

print(overlay.show(), flush=True)
time.sleep(1.5)
mons = monitors.list_monitors()
prim = next(m for m in mons if m.primary)
cap = capture.capture_monitor(prim, region=(prim.width // 2 - 450, 0, 900, 110))
img = Image.open(__import__("io").BytesIO(cap.png)).convert("RGB")
# banner geometry: 560x62 at primary x=(1920-560)//2=680, y=16
# strip origin x=510 -> banner in strip coords: x 170..730, y 16..78
crop = img.crop((170, 16, 730, 78))
crop.save(r"C:\Users\NoName\Desktop\opencode-mcp\docs\images\01-banner.png")
print("cropped size:", crop.size, flush=True)
print(overlay.hide(), flush=True)
