"""Type one monkeytype game: words from argv, then screenshot results."""
import sys
import time


def log(*a):
    print(" ".join(str(x) for x in a).encode("ascii", "replace").decode(),
          flush=True)


from opencode_computer_use import capture, keyboard, monitors

words = sys.argv[1]
interval = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
mons = monitors.list_monitors()
m0 = next(m for m in mons if m.id == 0)
keyboard.type_text(words + " ", interval=interval)
time.sleep(3.0)
cap = capture.capture_monitor(m0, scale=0.6)
tag = sys.argv[2] if len(sys.argv) > 2 else "game"
open(r"C:\Users\NoName\Desktop\opencode-mcp\mt_%s.png" % tag, "wb").write(cap.png)
log("typed, results shot:", tag)
