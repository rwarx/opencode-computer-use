"""Automated MCP protocol tests (spawns the real server over stdio).

Only non-intrusive tools are exercised: no mouse moves, no keypresses,
no window focus changes. Safe for CI on a Windows runner with a desktop.
Runtime ~30 s (screenshots dominate).
"""
import json
import subprocess
import sys
import threading

import pytest

CWD = r"C:\Users\NoName\Desktop\opencode-mcp"


class MCPClient:
    def __init__(self):
        self.p = subprocess.Popen(
            [sys.executable, "-u", "-m", "opencode_computer_use"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=CWD, text=True, bufsize=1, encoding="utf-8")
        self._id = 0

    def send(self, obj):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def read(self, timeout_s=60):
        out = []

        def _rd():
            try:
                out.append(self.p.stdout.readline())
            except Exception as e:  # noqa: BLE001
                out.append("EXC:" + str(e))

        t = threading.Thread(target=_rd, daemon=True)
        t.start()
        t.join(timeout_s)
        assert out and out[0], "no response from server"
        return json.loads(out[0])

    def call(self, name, args):
        self._id += 1
        self.send({"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                   "params": {"name": name, "arguments": args}})
        r = self.read()
        assert "result" in r, f"{name}: {r}"
        return r["result"]["content"]

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


@pytest.fixture(scope="module")
def client():
    c = MCPClient()
    c.send({"jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "pytest", "version": "1"}}})
    r = c.read()
    assert "result" in r
    c.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    c.send({"jsonrpc": "2.0", "id": -1, "method": "tools/list", "params": {}})
    tools = c.read()["result"]["tools"]
    assert len(tools) == 35, [t["name"] for t in tools]
    yield c
    c.close()


def _text(content):
    return next(c.get("text", "") for c in content if c["type"] == "text")


def test_list_monitors_schema(client):
    data = json.loads(_text(client.call("computer_list_monitors", {})))
    assert isinstance(data, list) and len(data) >= 1
    for m in data:
        if "locked" in m:
            continue
        for key in ("id", "x", "y", "width", "height", "primary", "scale"):
            assert key in m, key
        assert m["width"] > 0 and m["height"] > 0


def test_mouse_position_schema(client):
    data = json.loads(_text(client.call("computer_mouse_position", {})))
    assert isinstance(data["x"], int) and isinstance(data["y"], int)


def test_screenshot_png_and_jpeg_mime(client):
    content = client.call("computer_screenshot", {"monitor": 1, "scale": 0.25})
    kinds = {c["type"] for c in content}
    assert {"text", "image"} <= kinds
    img = next(c for c in content if c["type"] == "image")
    assert img["mimeType"] == "image/png"
    import base64
    raw = base64.b64decode(img["data"])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"

    content = client.call("computer_screenshot",
                          {"monitor": 1, "scale": 0.25, "jpeg": True})
    img = next(c for c in content if c["type"] == "image")
    assert img["mimeType"] == "image/jpeg", img["mimeType"]
    raw = base64.b64decode(img["data"])
    assert raw[:2] == b"\xff\xd8"


def test_screenshot_fast_loop_budget(client):
    import time
    t0 = time.perf_counter()
    client.call("computer_screenshot", {"monitor": 1, "scale": 0.5, "jpeg": True})
    dt = time.perf_counter() - t0
    print(f"\nfast screenshot roundtrip: {dt*1000:.0f} ms")
    assert dt < 10.0


def test_overlay_show_hide(client):
    txt = _text(client.call("computer_overlay_show", {"text": "pytest"}))
    assert json.loads(txt)["shown"] is True
    txt = _text(client.call("computer_overlay_hide", {}))
    assert json.loads(txt)["shown"] is False


def test_emergency_stop_blocks_and_resets(client):
    txt = _text(client.call("computer_emergency_stop", {"reason": "pytest"}))
    assert json.loads(txt)["stopped"] is True
    # input now refused as inline ERROR (never a protocol hang)
    txt = _text(client.call("computer_mouse_move",
                            {"x": 10, "y": 10, "screenshot_after": False}))
    assert txt.startswith("ERROR") and "EMERGENCY STOP" in txt
    txt = _text(client.call("computer_emergency_stop", {"reset": True}))
    assert json.loads(txt)["stopped"] is False


def test_batch_wait_only(client):
    txt = _text(client.call(
        "computer_batch",
        {"actions": [{"type": "wait", "seconds": 0.2}], "screenshot_after": False}))
    assert "BATCH OK" in txt


def test_safe_mode_refuses_risky_type(client):
    txt = _text(client.call("computer_type",
                            {"text": "shutdown computer now",
                             "screenshot_after": False}))
    assert "REFUSED" in txt
