"""Focused Cyrillic roundtrip: type into Notepad, save, compare codepoints."""
import json
import os
import subprocess
import sys
import threading

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
TARGET = os.path.join(DESKTOP, "opencode_cyrillic_test.txt")
if os.path.exists(TARGET):
    os.remove(TARGET)
TEXT = "Привет мир! Hello! 123"

p = subprocess.Popen(
    [sys.executable, "-u", "-m", "opencode_computer_use"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    cwd=r"C:\Users\NoName\Desktop\opencode-mcp", text=True, bufsize=1, encoding='utf-8')
_n = [0]


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


def call(name, args):
    _n[0] += 1
    send({"jsonrpc": "2.0", "id": _n[0], "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    return read_one()


send({"jsonrpc": "2.0", "id": 99, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "e2e", "version": "1"}}})
read_one()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
call("computer_hotkey", {"keys": ["WIN", "R"], "screenshot_after": False})
call("computer_wait", {"seconds": 0.8})
call("computer_type", {"text": "notepad", "screenshot_after": False})
call("computer_key", {"key": "ENTER", "screenshot_after": False})
call("computer_wait_for_window", {"title": "\u0411\u043b\u043e\u043a\u043d\u043e\u0442", "timeout": 15})
call("computer_type", {"text": TEXT, "screenshot_after": False})
call("computer_hotkey", {"keys": ["CTRL", "S"], "screenshot_after": False})
call("computer_wait", {"seconds": 1.0})
call("computer_type", {"text": TARGET, "screenshot_after": False})
call("computer_key", {"key": "ENTER", "screenshot_after": False})
call("computer_wait", {"seconds": 1.0})
raw = open(TARGET, "rb").read()
print("raw bytes:", raw[:80], flush=True)
content = raw.decode("utf-8-sig")
print("match:", content.strip() == TEXT, "| got codepoints:",
      [hex(ord(c)) for c in content.strip()][:12], flush=True)
assert content.strip() == TEXT, "cyrillic mismatch"
call("computer_hotkey", {"keys": ["ALT", "F4"], "screenshot_after": False})
call("computer_wait", {"seconds": 0.8})
os.remove(TARGET)
print("CYRILLIC E2E: PASS", flush=True)
p.kill()
