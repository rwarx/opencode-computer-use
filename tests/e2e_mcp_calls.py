import json, subprocess

p = subprocess.Popen(
    ["python", "-m", "opencode_computer_use"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=r"C:\Users\NoName\Desktop\opencode-mcp", text=True, bufsize=1, encoding='utf-8')


def send(obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def call(i, name, args):
    send({"jsonrpc": "2.0", "id": i, "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    r = json.loads(p.stdout.readline())
    if "error" in r:
        print(name, "ERROR", str(r["error"])[:200])
        return r
    cs = r["result"]["content"]
    kinds = [c["type"] for c in cs]
    txt = " | ".join(c.get("text", "")[:150] for c in cs if c["type"] == "text")
    nimg = sum(1 for c in cs if c["type"] == "image")
    print(name, "->", kinds, "images:", nimg, "::", txt[:220])
    return r


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "t", "version": "1"}}})
p.stdout.readline()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
call(2, "computer_list_monitors", {})
call(3, "computer_mouse_position", {})
call(4, "computer_screenshot", {"monitor": 1, "scale": 0.5})
call(5, "computer_type", {"text": "shutdown computer now buy now",
                          "screenshot_after": False})
call(6, "computer_emergency_stop", {"reason": "test"})
call(7, "computer_mouse_move", {"x": 100, "y": 100})
call(8, "computer_emergency_stop", {"reset": True})
call(9, "computer_mouse_move", {"x": 100, "y": 100})
call(10, "computer_batch",
     {"actions": [{"type": "wait", "seconds": 0.2}], "screenshot_after": False})
p.kill()
print("E2E MCP CALLS DONE")
