"""Text extraction from PDFs, including OCR fallback and redaction awareness.

Two tricky cases this module handles:

* **Redacted-but-readable** — a black rectangle is drawn over the text but the
  underlying text layer is intact, so plain extraction still returns it. We also
  expose the redaction rectangles so the scanner can mark such findings.
* **Scanned (image-only) pages** — no text layer at all. The page is rendered to
  an image and run through Tesseract OCR (when enabled and available).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import fitz  # PyMuPDF

log = logging.getLogger(__name__)

# Cache whether the tesseract binary is usable so we only probe once.
_OCR_AVAILABLE: bool | None = None


def ocr_available() -> bool:
    global _OCR_AVAILABLE
    if _OCR_AVAILABLE is None:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            _OCR_AVAILABLE = True
        except Exception as exc:  # binary missing or import failure
            log.warning("OCR unavailable (%s); scanned pages will be skipped", exc)
            _OCR_AVAILABLE = False
    return _OCR_AVAILABLE


@dataclass
class PageText:
    number: int          # 1-based
    text: str
    via_ocr: bool = False


def _ocr_page(page: "fitz.Page", dpi: int, language: str) -> str:
    import pytesseract
    from PIL import Image
    import io

    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang=language)


def extract_page(page: "fitz.Page", number: int, ocr_cfg: dict) -> PageText:
    """Return text for a single page, using OCR only when no text layer exists."""
    text = page.get_text("text") or ""
    if text.strip():
        return PageText(number=number, text=text, via_ocr=False)

    # No text layer: this is a scanned/image page.
    if ocr_cfg.get("enabled", True) and ocr_available():
        try:
            ocr_text = _ocr_page(page, ocr_cfg.get("dpi", 300),
                                 ocr_cfg.get("language", "eng"))
            return PageText(number=number, text=ocr_text, via_ocr=True)
        except Exception as exc:
            log.warning("OCR failed on page %s: %s", number, exc)
    return PageText(number=number, text="", via_ocr=False)


def redaction_rects(page: "fitz.Page") -> list["fitz.Rect"]:
    """Return filled, dark rectangles that look like redaction marks."""
    rects: list[fitz.Rect] = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return rects
    for d in drawings:
        fill = d.get("fill")
        if not fill:
            continue
        # Treat near-black fills as redaction marks.
        if max(fill) > 0.35:
            continue
        for item in d.get("items", []):
            if item[0] == "re":  # rectangle
                rects.append(fitz.Rect(item[1]))
    return rects


def is_value_redacted(page: "fitz.Page", value: str,
                      rects: list["fitz.Rect"]) -> bool:
    """True if ``value`` on the page overlaps one of the redaction rectangles."""
    if not rects:
        return False
    try:
        hits = page.search_for(value.strip())
    except Exception:
        return False
    for hit in hits:
        for r in rects:
            if r.intersects(hit):
                return True
    return False
