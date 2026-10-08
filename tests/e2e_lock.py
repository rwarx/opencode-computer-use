import json
import os
import subprocess
import sys
import threading

env = dict(os.environ, COMPUTER_USE_SINGLE_MONITOR="1", COMPUTER_USE_MONITOR="1")
p = subprocess.Popen(
    [sys.executable, "-u", "-m", "opencode_computer_use"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    cwd=r"C:\Users\NoName\Desktop\opencode-mcp", text=True, bufsize=1, encoding='utf-8',
    env=env)


def send(obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def read_one(timeout_s=60):
    out = []

    def _rd():
        out.append(p.stdout.readline())

    t = threading.Thread(target=_rd, daemon=True)
    t.start()
    t.join(timeout_s)
    if not out or not out[0]:
        raise RuntimeError("no response")
    return json.loads(out[0])


def call(i, name, args):
    send({"jsonrpc": "2.0", "id": i, "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    r = read_one()
    cs = r["result"]["content"]
    txt = " | ".join(c.get("text", "")[:200] for c in cs if c["type"] == "text")
    print(f"[{name}] {txt[:260]}", flush=True)


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "t", "version": "1"}}})
read_one()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
call(2, "computer_list_monitors", {})
# (-1500, 500) lives on monitor 0 -> must be clamped into monitor 1.
call(3, "computer_mouse_move", {"x": -1500, "y": 500, "screenshot_after": False})
call(4, "computer_mouse_position", {})
# OCR / UIA optional deps not installed -> graceful errors, no hang.
call(5, "computer_ocr", {"monitor": 1})
call(6, "computer_ui_tree", {})
call(7, "computer_screenshot", {"monitor": "all", "scale": 0.4})
p.kill()
print("LOCK + GRACEFUL DEGRADE: DONE", flush=True)
