"""OCR layer (optional dependency, graceful degradation).

Priority chain per spec: UI Automation -> OCR -> template -> visual coords.
OCR is a fallback: only loaded when rapidocr-onnxruntime is installed.
"""
from __future__ import annotations

import io
import threading

from .config import log

_lock = threading.Lock()
_engine = None
_engine_error: str | None = None


def is_available() -> bool:
    global _engine, _engine_error
    if _engine is not None:
        return True
    if _engine_error is not None:
        return False
    try:
        from rapidocr_onnxruntime import RapidOCR
        with _lock:
            if _engine is None:
                _engine = RapidOCR()
        return True
    except Exception as e:  # noqa: BLE001
        _engine_error = str(e)
        log.warning(f"OCR unavailable (pip install opencode-computer-use[ocr]): {e}")
        return False


def ocr_image(png_bytes: bytes) -> list[dict]:
    """Return [{text, x, y, width, height, confidence}] in image-pixel coords."""
    if not is_available():
        raise RuntimeError("OCR not installed. Run: pip install opencode-computer-use[ocr]")
    import numpy as np
    from PIL import Image
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    arr = np.array(img)
    with _lock:
        assert _engine is not None
        out, _ = _engine(arr)
    results: list[dict] = []
    for item in out or []:
        try:
            box, text, conf = item[0], item[1], float(item[2])
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            results.append({"text": str(text),
                            "x": int(x0), "y": int(y0),
                            "width": int(x1 - x0), "height": int(y1 - y0),
                            "confidence": round(conf, 3)})
        except Exception:
            continue
    log.info(f"OCR found {len(results)} text blocks")
    return results


def find_text(png_bytes: bytes, needle: str, min_confidence: float = 0.3) -> dict | None:
    needle_n = needle.strip().lower()
    best = None
    for r in ocr_image(png_bytes):
        if needle_n in r["text"].lower() and r["confidence"] >= min_confidence:
            if best is None or r["confidence"] > best["confidence"]:
                best = r
    if best is None:
        return None
    cx = best["x"] + best["width"] // 2
    cy = best["y"] + best["height"] // 2
    return {**best, "found": True, "cx": cx, "cy": cy}
