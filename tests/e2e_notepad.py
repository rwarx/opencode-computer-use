"""Acceptance E2E: Notepad Hello World via MCP (criterion #34).

Opens Notepad with Win+R, types Latin + Cyrillic, saves to Desktop,
verifies file content, screenshots, closes Notepad, cleans up.
"""
import json
import os
import subprocess
import sys
import threading

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
TARGET = os.path.join(DESKTOP, "opencode_computer_use_test.txt")
for f in [TARGET]:
    if os.path.exists(f):
        os.remove(f)

p = subprocess.Popen(
    [sys.executable, "-u", "-m", "opencode_computer_use"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    cwd=r"C:\Users\NoName\Desktop\opencode-mcp", text=True, bufsize=1, encoding="utf-8")
_n = [10]


def send(obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def read_one(timeout_s=60):
    out = []

    def _rd():
        try:
            out.append(p.stdout.readline())
        except Exception as e:
            out.append("EXC:" + str(e))

    t = threading.Thread(target=_rd, daemon=True)
    t.start()
    t.join(timeout_s)
    if not out or out[0] in ("", None):
        raise RuntimeError("no response from server")
    return json.loads(out[0])


def call(name, args, show=160):
    _n[0] += 1
    send({"jsonrpc": "2.0", "id": _n[0], "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    r = read_one()
    if "error" in r:
        raise RuntimeError(f"{name}: {r['error']}")
    cs = r["result"]["content"]
    txt = " | ".join(c.get("text", "")[:show] for c in cs if c["type"] == "text")
    nimg = sum(1 for c in cs if c["type"] == "image")
    print(f"[{name}] images={nimg} :: {txt[:220]}", flush=True)
    return r


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "e2e", "version": "1"}}})
read_one()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})

call("computer_hotkey", {"keys": ["WIN", "R"], "screenshot_after": False})
call("computer_wait", {"seconds": 0.8})
call("computer_type", {"text": "notepad", "screenshot_after": False})
call("computer_key", {"key": "ENTER"})
call("computer_wait_for_window", {"title": "Notepad", "timeout": 15})
call("computer_type", {"text": "Hello from OpenCode! \u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440! ",
                       "screenshot_after": False})
call("computer_hotkey", {"keys": ["CTRL", "S"], "screenshot_after": False})
call("computer_wait", {"seconds": 1.0})
call("computer_type", {"text": TARGET, "screenshot_after": False})
call("computer_key", {"key": "ENTER"})
call("computer_wait", {"seconds": 1.0})

assert os.path.exists(TARGET), "save failed: file not on Desktop"
content = open(TARGET, encoding="utf-8-sig").read()
print("FILE CONTENT:", repr(content[:80]), flush=True)
assert "Hello from OpenCode" in content, "typed text mismatch"

call("computer_screenshot", {"monitor": 1, "scale": 0.5})
# Close notepad: Ctrl+W via focus + hotkey, then kill leftovers by title is out
# of scope (no shell) — use window close via ALT+F4 key combo.
call("computer_hotkey", {"keys": ["ALT", "F4"], "screenshot_after": False})
call("computer_wait", {"seconds": 0.8})
os.remove(TARGET)
print("NOTEPAD E2E: PASS", flush=True)
p.kill()
