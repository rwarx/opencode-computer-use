"""Unit tests for CoordinateMapper (DPI + multi-monitor math).

These run anywhere (no Windows GUI needed) — they pin the transform chain:
model -> screenshot native -> virtual desktop -> SendInput absolute.
"""
from opencode_computer_use.coords import (
    MonitorInfo, VirtualDesktop, enforce_single_monitor, model_to_screenshot,
    screenshot_to_virtual, virtual_to_abs, virtual_to_monitor_relative,
)


def _primary():
    return MonitorInfo(id=0, name="Primary", x=0, y=0, width=1920, height=1080,
                       primary=True, scale=1.0)


def _right_125():
    # Second monitor to the right, 125% DPI.
    return MonitorInfo(id=1, name="Right", x=1920, y=0, width=2560, height=1440,
                       primary=False, scale=1.25, dpi_x=120, dpi_y=120)


def _left_negative():
    return MonitorInfo(id=0, name="Left", x=-1920, y=0, width=1920, height=1080,
                       primary=False, scale=1.0)


def test_model_to_screenshot_roundtrip():
    assert model_to_screenshot(960, 540, 1.0) == (960, 540)
    assert model_to_screenshot(960, 540, 0.5) == (1920, 1080)
    assert model_to_screenshot(0, 0, 0.75) == (0, 0)


def test_screenshot_to_virtual_primary():
    assert screenshot_to_virtual(100, 200, _primary()) == (100, 200)


def test_screenshot_to_virtual_second_monitor():
    m = _right_125()
    assert screenshot_to_virtual(0, 0, m) == (1920, 0)
    assert screenshot_to_virtual(100, 50, m) == (2020, 50)


def test_screenshot_region_offset():
    m = _primary()
    assert screenshot_to_virtual(10, 10, m, region=(500, 300, 400, 400)) == (510, 310)


def test_negative_monitor_offset():
    m = MonitorInfo(id=1, name="R", x=0, y=0, width=1920, height=1080,
                    primary=True, scale=1.0)
    left = _left_negative()
    assert screenshot_to_virtual(0, 0, left) == (-1920, 0)
    assert left.contains_point(-1, 500)
    assert not m.contains_point(-1, 500)


def test_virtual_to_abs_corners():
    vd = VirtualDesktop(x=0, y=0, width=1920, height=1080)
    assert virtual_to_abs(0, 0, vd) == (0, 0)
    assert virtual_to_abs(1919, 1079, vd) == (65535, 65535)


def test_virtual_to_abs_negative_origin():
    vd = VirtualDesktop(x=-1920, y=0, width=3840, height=1080)
    ax, ay = virtual_to_abs(-1920, 0, vd)
    assert (ax, ay) == (0, 0)
    ax2, _ = virtual_to_abs(0, 0, vd)
    assert 32000 < ax2 < 33000  # ~middle


def test_enforce_single_monitor_clamps():
    m = _primary()
    cx, cy, clamped = enforce_single_monitor(500, 500, m)
    assert (cx, cy, clamped) == (500, 500, False)
    cx, cy, clamped = enforce_single_monitor(5000, 500, m)
    assert clamped and (cx, cy) == (1919, 500)
    cx, cy, clamped = enforce_single_monitor(-50, -50, m)
    assert clamped and (cx, cy) == (0, 0)


def test_dpi_150_scales_reported_but_coords_stay_physical():
    # 150% DPI monitor: width/height from GetMonitorInfo are already physical.
    m = MonitorInfo(id=0, name="Hi", x=0, y=0, width=3840, height=2160,
                    primary=True, scale=1.5, dpi_x=144, dpi_y=144)
    assert m.scale == 1.5
    assert screenshot_to_virtual(3839, 2159, m) == (3839, 2159)


def test_monitor_relative():
    m = _right_125()
    assert virtual_to_monitor_relative(2020, 50, m) == (100, 50)
