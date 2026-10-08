"""Central configuration + stderr logging.

All settings come from environment variables so OpenCode config stays simple.
Stdout is RESERVED for MCP stdio framing — all logs go to stderr.
Sensitive typed text is never logged (only its length).
"""
from __future__ import annotations

import logging
import os
import sys


def get_log_level() -> int:
    return {
        "ERROR": logging.ERROR,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "TRACE": 5,
    }.get(os.getenv("COMPUTER_USE_LOG_LEVEL", "INFO").upper(), logging.INFO)


logging.addLevelName(5, "TRACE")
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
log = logging.getLogger("computer-use")
log.handlers.clear()
log.addHandler(_handler)
log.setLevel(get_log_level())
log.propagate = False


class Settings:
    """Runtime policy. Read once at startup, cheap to re-read env on demand."""

    @staticmethod
    def single_monitor_mode() -> bool:
        return os.getenv("COMPUTER_USE_SINGLE_MONITOR", "0").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def locked_monitor() -> int:
        try:
            return int(os.getenv("COMPUTER_USE_MONITOR", "0"))
        except ValueError:
            return 0

    @staticmethod
    def autonomous() -> bool:
        # SAFE by default: dangerous confirmations required.
        # Set COMPUTER_USE_AUTONOMOUS=1 to allow agent to work without confirmations.
        return os.getenv("COMPUTER_USE_AUTONOMOUS", "0").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def default_screenshot_after() -> bool:
        return os.getenv("COMPUTER_USE_SCREENSHOT_AFTER", "0").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def allow_mouse() -> bool:
        return os.getenv("COMPUTER_USE_ALLOW_MOUSE", "1").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def allow_keyboard() -> bool:
        return os.getenv("COMPUTER_USE_ALLOW_KEYBOARD", "1").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def allow_window_control() -> bool:
        return os.getenv("COMPUTER_USE_ALLOW_WINDOW", "1").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def jpeg_quality() -> int:
        try:
            q = int(os.getenv("COMPUTER_USE_JPEG_QUALITY", "80"))
        except ValueError:
            q = 80
        return max(30, min(95, q))

    @staticmethod
    def max_screenshot_width() -> int:
        try:
            w = int(os.getenv("COMPUTER_USE_MAX_WIDTH", "1920"))
        except ValueError:
            w = 1920
        return max(320, min(7680, w))

    @staticmethod
    def overlay_auto() -> bool:
        # Show "using your computer" banner on input, auto-hide when idle.
        return os.getenv("COMPUTER_USE_OVERLAY_AUTO", "1").strip().lower() in (
            "1", "true", "yes", "on",
        )

    @staticmethod
    def overlay_text() -> str:
        return os.getenv(
            "COMPUTER_USE_OVERLAY_TEXT", "OpenCode using your computer")

    @staticmethod
    def overlay_idle_sec() -> float:
        try:
            s = float(os.getenv("COMPUTER_USE_OVERLAY_IDLE_SEC", "10"))
        except ValueError:
            s = 10.0
        return max(2.0, min(300.0, s))
