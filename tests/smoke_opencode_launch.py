import json
import os
import subprocess
import sys
import threading

env = dict(os.environ,
           COMPUTER_USE_LOG_LEVEL="INFO",
           COMPUTER_USE_SINGLE_MONITOR="0",
           COMPUTER_USE_MONITOR="0",
           COMPUTER_USE_AUTONOMOUS="0",
           COMPUTER_USE_MAX_WIDTH="1920")
p = subprocess.Popen(
    ["python", "-m", "opencode_computer_use"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=r"C:\Users\NoName\Desktop\opencode-mcp",
    text=True, bufsize=1, encoding="utf-8", env=env)


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
    if not out or not out[0]:
        raise RuntimeError("no response; stderr=" + p.stderr.read(2000)[-1000:])
    return json.loads(out[0])


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "opencode-check", "version": "1"}}})
r = read_one()
assert "result" in r, r
print("initialize: OK", flush=True)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
tools = read_one()["result"]["tools"]
names = [t["name"] for t in tools]
print("tools:", len(names), flush=True)
assert len(names) == 33, names

checks = [
    ("computer_list_monitors", {}),
    ("computer_mouse_position", {}),
    ("computer_get_active_window", {}),
    ("computer_list_windows", {"limit": 5}),
    ("computer_screenshot", {"monitor": 1, "scale": 0.4}),
    ("computer_ui_tree", {"depth": 1, "max_elements": 10}),
    ("computer_wait", {"seconds": 0.2}),
]
for i, (name, args) in enumerate(checks, start=10):
    send({"jsonrpc": "2.0", "id": i, "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    r = read_one()
    assert "result" in r, (name, r)
    cs = r["result"]["content"]
    kinds = sorted({c["type"] for c in cs})
    txt = next((c.get("text", "") for c in cs if c["type"] == "text"), "")
    print(f"{name}: OK {kinds} :: {txt[:130]}".encode("cp1251", "replace").decode("cp1251"),
          flush=True)
p.kill()
print("OPENCODE-LAUNCH SMOKE: PASS", flush=True)
