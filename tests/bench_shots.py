"""Benchmark: mss grab + Pillow resize + PNG/JPEG encode + base64."""
import base64
import io
import time

import mss
from PIL import Image

N = 5


def bench(name, fn):
    ts = []
    out = None
    for _ in range(N):
        t0 = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t0) * 1000)
    size = len(out) if isinstance(out, (bytes, str)) else 0
    print(f"{name:34s} {min(ts):7.1f} ms min / {sum(ts)/len(ts):7.1f} ms avg | {size/1024:8.1f} KB",
          flush=True)


with mss.mss() as sct:
    mon = sct.monitors[2]  # primary 1920x1080
    t0 = time.perf_counter()
    for _ in range(N):
        sct.grab(mon)
    print(f"mss grab 1920x1080: {(time.perf_counter()-t0)/N*1000:.1f} ms avg", flush=True)
    shot = sct.grab(mon)
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

small_lanczos = img.resize((960, 540), Image.LANCZOS)
small_bilinear = img.resize((960, 540), Image.BILINEAR)
small_bicubic = img.resize((960, 540), Image.BICUBIC)


def enc_png(im, level):
    buf = io.BytesIO()
    im.save(buf, "PNG", compress_level=level)
    return buf.getvalue()


def enc_jpeg(im, q):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=q)
    return buf.getvalue()


bench("resize LANCZOS 1920->960", lambda: img.resize((960, 540), Image.LANCZOS))
bench("resize BICUBIC 1920->960", lambda: img.resize((960, 540), Image.BICUBIC))
bench("resize BILINEAR 1920->960", lambda: img.resize((960, 540), Image.BILINEAR))
bench("PNG enc 960 (level 6)", lambda: enc_png(small_bilinear, 6))
bench("PNG enc 960 (level 3)", lambda: enc_png(small_bilinear, 3))
bench("PNG enc 960 (level 1)", lambda: enc_png(small_bilinear, 1))
bench("PNG enc 1920 (level 6)", lambda: enc_png(img, 6))
bench("PNG enc 1920 (level 1)", lambda: enc_png(img, 1))
bench("JPEG enc 960 (q80)", lambda: enc_jpeg(small_bilinear, 80))
bench("JPEG enc 1920 (q80)", lambda: enc_jpeg(img, 80))
raw = enc_jpeg(small_bilinear, 80)
bench("base64 100KB", lambda: base64.b64encode(raw))
raw2 = enc_png(img, 6)
bench("base64 2MB", lambda: base64.b64encode(raw2))
print("DONE", flush=True)
