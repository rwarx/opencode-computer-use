"""Live overlay test: show -> screenshot top strip -> verify pixels -> hide."""
import time

from opencode_computer_use import capture, monitors, overlay

print(overlay.show("OpenCode using your computer\nTest banner - click-through check"),
      flush=True)
time.sleep(1.5)
mons = monitors.list_monitors()
prim = next(m for m in mons if m.primary)
# top strip where the banner lives
cap = capture.capture_monitor(prim, region=(prim.width // 2 - 320, 0, 640, 120))
open(r"C:\Users\NoName\Desktop\opencode-mcp\overlay_proof.png", "wb").write(cap.png)
print("strip saved", cap.width, cap.height, flush=True)
# banner must be non-trivial (not black/empty): check brightness spread
from PIL import Image
import io
img = Image.open(io.BytesIO(cap.png)).convert("L")
px = list(img.getdata())
print("brightness min/max:", min(px), max(px), flush=True)
assert max(px) - min(px) > 40, "banner area looks empty"
print(overlay.hide(), flush=True)
print("OVERLAY: PASS", flush=True)
