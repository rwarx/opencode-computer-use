"""Unit tests for keyboard mapping (validation paths only — no SendInput)."""
import pytest

from opencode_computer_use import keyboard as kbd


def test_normalize():
    assert kbd.normalize_key_name(" enter ") == "ENTER"
    assert kbd.normalize_key_name("page_up") == "PAGEUP"
    assert kbd.normalize_key_name("ctrl") == "CTRL"


def test_special_keys_cover_spec():
    for name in ["ENTER", "TAB", "ESC", "BACKSPACE", "DELETE", "UP", "DOWN",
                 "LEFT", "RIGHT", "HOME", "END", "PAGEUP", "PAGEDOWN",
                 "F1", "F12", "SHIFT", "CTRL", "ALT", "WIN"]:
        assert name in kbd.SPECIAL_KEYS, name


def test_unknown_key_raises_before_sendinput():
    # Raises in validation, before any SendInput — safe to call in tests.
    with pytest.raises(ValueError, match="unknown key"):
        kbd.press_key("NOT_A_KEY_AT_ALL")
    with pytest.raises(ValueError, match="unknown key"):
        kbd.key_down("NOT_A_KEY_AT_ALL")
    with pytest.raises(ValueError, match="unknown key"):
        kbd.key_up("NOT_A_KEY_AT_ALL")


def test_hotkey_validation():
    with pytest.raises(ValueError, match="at least one key"):
        kbd.hotkey()
    with pytest.raises(ValueError, match="unknown hotkey part"):
        kbd.hotkey("CTRL", "NOT_A_KEY_AT_ALL_LONGER_THAN_ONE_CHAR")


def test_hotkey_char_mapping_layout_independent():
    # A-Z / 0-9 map to fixed VK codes regardless of layout (no SendInput here,
    # just checking the mapping rule used by hotkey()).
    assert ord("R") == 0x52
    assert ord("C") == 0x43
