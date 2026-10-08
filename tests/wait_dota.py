"""Wait for Dota 2 window (up to ~3 min, first launch may update)."""
import time

from opencode_computer_use import windows_mgr

for i in range(36):
    time.sleep(5.0)
    wins = windows_mgr.list_windows(limit=40)
    dota = [w for w in wins
            if "dota" in (w["process"] or "").lower()]
    steam = [w["title"][:30] for w in wins
             if "steam" in (w["process"] or "").lower()]
    if dota:
        w = dota[0]
        print("DOTA:", w["title"][:60], "|", w["process"], "|",
              w["x"], w["y"], w["width"], w["height"], flush=True)
        break
    print("wait", i, "steam:", steam, flush=True)
else:
    print("DOTA NOT FOUND", flush=True)
