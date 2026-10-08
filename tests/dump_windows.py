"""Dump full window list to file (utf-8 safe)."""
import io
import json

from opencode_computer_use import windows_mgr

wins = windows_mgr.list_windows(limit=100)
with io.open(r"C:\Users\NoName\Desktop\opencode-mcp\wb_windows.json",
             "w", encoding="utf-8") as f:
    json.dump(wins, f, ensure_ascii=False, indent=1)
print("total:", len(wins), flush=True)
for w in wins:
    print(w["hwnd"], (w["process"] or ""), w["x"], w["y"], w["width"],
          w["height"], flush=True)
