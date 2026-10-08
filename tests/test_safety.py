"""Unit tests for the safety layer (pure logic, no GUI side effects)."""
import pytest

from opencode_computer_use import safety


@pytest.fixture(autouse=True)
def _clean_stop():
    safety.reset_stop()
    yield
    safety.reset_stop()


def test_emergency_stop_blocks_input():
    assert not safety.is_stopped()
    r = safety.emergency_stop("test")
    assert r["stopped"] is True
    assert safety.is_stopped()
    with pytest.raises(RuntimeError, match="EMERGENCY STOP"):
        safety.check_input_allowed("mouse")
    with pytest.raises(RuntimeError, match="EMERGENCY STOP"):
        safety.check_input_allowed("keyboard")


def test_reset_reenables():
    safety.emergency_stop("test")
    r = safety.reset_stop()
    assert r["stopped"] is False
    safety.check_input_allowed("mouse")  # no raise


def test_risky_text_safe_mode(monkeypatch):
    monkeypatch.setenv("COMPUTER_USE_AUTONOMOUS", "0")
    for txt in ["shutdown computer now", "format D:", "buy now, place order",
                "rm -rf /home", "удалить все файлы", "выключить компьютер"]:
        r = safety.check_text_risk(txt)
        assert r["risky"] and r["needs_confirmation"], txt


def test_benign_text_allowed(monkeypatch):
    monkeypatch.setenv("COMPUTER_USE_AUTONOMOUS", "0")
    for txt in ["Hello from OpenCode!", "notepad", "C:\\Users\\x\\Desktop\\a.txt"]:
        r = safety.check_text_risk(txt)
        assert not r["needs_confirmation"], txt


def test_autonomous_mode_skips_confirmation(monkeypatch):
    monkeypatch.setenv("COMPUTER_USE_AUTONOMOUS", "1")
    r = safety.check_text_risk("shutdown computer now")
    assert r["risky"] and not r["needs_confirmation"]
    assert r["mode"] == "autonomous"


def test_policy_gates(monkeypatch):
    monkeypatch.setenv("COMPUTER_USE_ALLOW_MOUSE", "0")
    with pytest.raises(RuntimeError, match="mouse"):
        safety.check_input_allowed("mouse")
    monkeypatch.setenv("COMPUTER_USE_ALLOW_MOUSE", "1")
    monkeypatch.setenv("COMPUTER_USE_ALLOW_KEYBOARD", "0")
    with pytest.raises(RuntimeError, match="keyboard"):
        safety.check_input_allowed("keyboard")
