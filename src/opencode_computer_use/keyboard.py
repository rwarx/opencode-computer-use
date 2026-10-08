"""Keyboard via SendInput.

- Printable/Unicode text (Latin + Cyrillic + any BMP/astral char):
  KEYEVENTF_UNICODE per code unit — layout-independent.
- Special keys (ENTER/TAB/ESC/arrows/F1-F12/...): virtual-key codes.
- Long text fallback: clipboard + Ctrl+V (reliable for big pastes/Cyrillic
  in apps with quirky IME handling).
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from .config import log

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)]


class _INPUT_UNION(ctypes.Union):
    # Union must be 32 bytes (size of MOUSEINPUT, the largest member)
    # so that INPUT is 40 bytes like the Windows struct.
    _fields_ = [("ki", KEYBDINPUT),
                ("_pad", ctypes.c_ubyte * 32)]


class INPUT(ctypes.Structure):
    # Must match Windows INPUT exactly (40 bytes on x64): DWORD + union.
    # A sequential struct with KEYBDINPUT alone is only 32 bytes and
    # SendInput rejects it with ERROR_INVALID_PARAMETER (87).
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


SPECIAL_KEYS: dict[str, int] = {
    "ENTER": 0x0D, "RETURN": 0x0D, "TAB": 0x09, "ESC": 0x1B, "ESCAPE": 0x1B,
    "BACKSPACE": 0x08, "DELETE": 0x2E, "INSERT": 0x2D,
    "HOME": 0x24, "END": 0x23, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    "SPACE": 0x20, "CAPSLOCK": 0x14, "NUMLOCK": 0x90, "SCROLLLOCK": 0x91,
    "PRINTSCREEN": 0x2C, "PAUSE": 0x13,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
    "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F,
    "F17": 0x80, "F18": 0x81, "F19": 0x82, "F20": 0x83, "F21": 0x84,
    "F22": 0x85, "F23": 0x86, "F24": 0x87,
    "SHIFT": VK_SHIFT, "CTRL": VK_CONTROL, "CONTROL": VK_CONTROL,
    "ALT": VK_MENU, "WIN": VK_LWIN, "WINDOWS": VK_LWIN, "META": VK_LWIN, "CMD": VK_LWIN,
    "APPS": 0x5D,
}

MODIFIERS = {"SHIFT", "CTRL", "CONTROL", "ALT", "WIN", "WINDOWS", "META", "CMD"}
_MOD_VK = {"SHIFT": VK_SHIFT, "CTRL": VK_CONTROL, "CONTROL": VK_CONTROL,
           "ALT": VK_MENU, "WIN": VK_LWIN, "WINDOWS": VK_LWIN,
           "META": VK_LWIN, "CMD": VK_LWIN}


def _send_ki(vk: int, scan: int, flags: int) -> None:
    inp = INPUT(type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=None))
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError(f"SendInput keyboard failed err={ctypes.GetLastError()}")


def _vk_down(vk: int) -> None:
    _send_ki(vk, 0, 0)


def _vk_up(vk: int) -> None:
    _send_ki(vk, 0, KEYEVENTF_KEYUP)


def _unicode_char(ch: str) -> None:
    for unit in ch.encode("utf-16-le").decode("utf-16-le", errors="ignore"):
        pass
    # Send UTF-16 code units (handles astral chars as surrogate pairs).
    buf = ch.encode("utf-16-le")
    for i in range(0, len(buf), 2):
        unit = int.from_bytes(buf[i:i + 2], "little")
        _send_ki(0, unit, KEYEVENTF_UNICODE)
        time.sleep(0.001)
        _send_ki(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)


def normalize_key_name(key: str) -> str:
    return key.strip().upper().replace(" ", "").replace("_", "")


def press_key(key: str) -> None:
    name = normalize_key_name(key)
    # Single char without explicit mapping -> unicode type (layout-independent).
    if len(key) == 1 and name not in SPECIAL_KEYS:
        _unicode_char(key)
        time.sleep(0.01)
        log.info("Keyboard keypress (1 char)")
        return
    if name not in SPECIAL_KEYS:
        raise ValueError(f"unknown key {key!r}; known: {sorted(SPECIAL_KEYS)}; "
                         "use computer_type for text")
    vk = SPECIAL_KEYS[name]
    _vk_down(vk)
    time.sleep(0.03)
    _vk_up(vk)
    log.info(f"Keyboard keypress {name}")


def key_down(key: str) -> None:
    name = normalize_key_name(key)
    if name not in SPECIAL_KEYS:
        raise ValueError(f"unknown key {key!r}")
    _vk_down(SPECIAL_KEYS[name])
    log.info(f"Keyboard key down {name}")


def key_up(key: str) -> None:
    name = normalize_key_name(key)
    if name not in SPECIAL_KEYS:
        raise ValueError(f"unknown key {key!r}")
    _vk_up(SPECIAL_KEYS[name])
    log.info(f"Keyboard key up {name}")


def hotkey(*keys: str) -> None:
    if not keys:
        raise ValueError("hotkey requires at least one key")
    names = [normalize_key_name(k) for k in keys]
    for n in names:
        if n not in SPECIAL_KEYS and len(n) != 1:
            raise ValueError(f"unknown hotkey part {n!r}")
    vks: list[int] = []
    for n, orig in zip(names, keys):
        if n in SPECIAL_KEYS:
            vks.append(SPECIAL_KEYS[n])
        elif len(orig) == 1 and ("A" <= orig.upper() <= "Z" or "0" <= orig <= "9"):
            # Layout-independent: VK_A..VK_Z == ord('A')..ord('Z'),
            # VK_0..VK_9 == ord('0')..ord('9') on any layout.
            vks.append(ord(orig.upper()))
        elif len(orig) == 1:
            scan = user32.VkKeyScanW(ord(orig))
            if scan == -1 or scan == 0xFFFF:
                raise ValueError(f"cannot map hotkey char {orig!r} to virtual key")
            vks.append(scan & 0xFF)
        else:
            raise ValueError(f"unknown hotkey part {orig!r}")
    for vk in vks:
        _vk_down(vk)
        time.sleep(0.02)
    time.sleep(0.04)
    for vk in reversed(vks):
        _vk_up(vk)
        time.sleep(0.02)
    log.info(f"Keyboard hotkey {'+'.join(names)}")


def type_text(text: str, interval: float = 0.0, use_clipboard: bool | None = None) -> dict:
    """Type unicode text. Long text (>500 chars) or explicit flag -> clipboard paste."""
    if not text:
        return {"typed": 0, "method": "none"}
    if use_clipboard is None:
        use_clipboard = len(text) > 500
    if use_clipboard:
        _paste_via_clipboard(text)
        log.info(f"Keyboard type ({len(text)} chars via clipboard)")
        return {"typed": len(text), "method": "clipboard"}
    for ch in text:
        if ch == "\n":
            _vk_down(SPECIAL_KEYS["ENTER"]); time.sleep(0.02); _vk_up(SPECIAL_KEYS["ENTER"])
        elif ch == "\t":
            _vk_down(SPECIAL_KEYS["TAB"]); time.sleep(0.02); _vk_up(SPECIAL_KEYS["TAB"])
        else:
            _unicode_char(ch)
        if interval > 0:
            time.sleep(interval)
    log.info(f"Keyboard type ({len(text)} chars via unicode)")
    return {"typed": len(text), "method": "unicode"}


def _paste_via_clipboard(text: str) -> None:
    data = text.encode("utf-16-le") + b"\x00\x00"
    hmem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not hmem:
        raise RuntimeError("GlobalAlloc failed")
    ptr = kernel32.GlobalLock(hmem)
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(hmem)
    try:
        if not user32.OpenClipboard(None):
            raise RuntimeError("OpenClipboard failed")
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(CF_UNICODETEXT, hmem):
                raise RuntimeError("SetClipboardData failed")
            hmem = None  # ownership transferred to system
        finally:
            user32.CloseClipboard()
    finally:
        if hmem:
            kernel32.GlobalFree(hmem)
    time.sleep(0.1)
    # Ctrl+V
    _vk_down(VK_CONTROL)
    time.sleep(0.03)
    vk_v = user32.VkKeyScanW(ord("v")) & 0xFF
    _vk_down(vk_v); time.sleep(0.03); _vk_up(vk_v)
    time.sleep(0.03)
    _vk_up(VK_CONTROL)
    time.sleep(0.2)
