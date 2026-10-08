import json
import subprocess
import sys
import threading

p = subprocess.Popen(
    [sys.executable, "-u", "-m", "opencode_computer_use"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    cwd=r"C:\Users\NoName\Desktop\opencode-mcp",
    text=True, bufsize=1, encoding="utf-8")


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
        raise RuntimeError("no response")
    return json.loads(out[0])


def call(i, name, args):
    send({"jsonrpc": "2.0", "id": i, "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    r = read_one()
    cs = r["result"]["content"]
    txt = next((c.get("text", "") for c in cs if c["type"] == "text"), "")
    print(f"[{name}] {txt[:200]}".encode("cp1251", "replace").decode("cp1251"),
          flush=True)
    return txt


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "t", "version": "1"}}})
read_one()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
names = [t["name"] for t in read_one()["result"]["tools"]]
print("tools:", len(names), "overlay_show" in names, "overlay_hide" in names, flush=True)
assert len(names) == 35
call(3, "computer_overlay_show", {"text": "MCP banner test"})
call(4, "computer_mouse_position", {})
call(5, "computer_overlay_hide", {})
p.kill()
print("OVERLAY MCP: PASS", flush=True)
