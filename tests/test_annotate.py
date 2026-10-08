"""Unit tests for annotated screenshots (pure mapping, synthetic images)."""
import io

from PIL import Image

from opencode_computer_use import annotate
from opencode_computer_use.coords import MonitorInfo


class _FakeCap:
    def __init__(self, w=800, h=600, scale=1.0, monitor=None, region=None):
        img = Image.new("RGB", (w, h), "black")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        self.png = buf.getvalue()
        self.scale = scale
        self.monitor = monitor
        self.region = region


def _mon():
    return MonitorInfo(id=1, name="P", x=0, y=0, width=1920, height=1080,
                       primary=True, scale=1.0)


def test_badge_math_full_scale():
    cap = _FakeCap(800, 600, 1.0, _mon())
    marks = [{"id": 1, "name": "Save", "control_type": "Button",
              "x": 100, "y": 100, "width": 80, "height": 30,
              "cx": 140, "cy": 115}]
    png, sc, out = annotate.annotate_capture(cap, marks, max_width=2000)
    assert sc == 1.0
    assert out[0]["mx"] == 140 and out[0]["my"] == 115
    img = Image.open(io.BytesIO(png))
    assert img.size == (800, 600)
    # badge painted green-ish pixels around center
    px = img.load()
    assert px[140, 115][1] > 100  # green channel lit


def test_downscale_maps_marks():
    cap = _FakeCap(1600, 900, 1.0, _mon())
    marks = [{"id": 1, "name": "B", "control_type": "Button",
              "x": 0, "y": 0, "width": 80, "height": 30,
              "cx": 800, "cy": 450}]
    png, sc, out = annotate.annotate_capture(cap, marks, max_width=800)
    assert sc == 0.5
    assert out[0]["mx"] == 400 and out[0]["my"] == 225


def test_off_image_excluded():
    cap = _FakeCap(800, 600, 1.0, _mon())
    marks = [{"id": 1, "name": "Far", "control_type": "Button",
              "x": 5000, "y": 5000, "width": 80, "height": 30,
              "cx": 5040, "cy": 5015}]
    _, _, out = annotate.annotate_capture(cap, marks)
    assert out[0]["mx"] == -1 and out[0]["my"] == -1


def test_region_offset():
    cap = _FakeCap(400, 300, 1.0, _mon(), region=(200, 100, 400, 300))
    marks = [{"id": 1, "name": "B", "control_type": "Button",
              "x": 250, "y": 150, "width": 80, "height": 30,
              "cx": 290, "cy": 165}]
    _, _, out = annotate.annotate_capture(cap, marks, max_width=2000)
    assert (out[0]["mx"], out[0]["my"]) == (90, 65)
