"""Scan a single PDF for sensitive content using the configured detectors."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .detectors import Detector, Finding
from . import extraction

log = logging.getLogger(__name__)


@dataclass
class ScanResult:
    path: Path
    flagged: bool = False
    findings: list[Finding] = field(default_factory=list)
    pages: int = 0
    used_ocr: bool = False
    error: str | None = None

    def to_dict(self, mask: bool = True) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "flagged": self.flagged,
            "pages": self.pages,
            "used_ocr": self.used_ocr,
            "error": self.error,
            "findings": [f.to_dict(mask=mask) for f in self.findings],
        }


def scan_file(path: Path, detectors: list[Detector], ocr_cfg: dict) -> ScanResult:
    """Open ``path``, run every detector over each page, and collect findings."""
    result = ScanResult(path=Path(path))
    try:
        doc = fitz.open(path)
    except Exception as exc:
        result.error = f"open failed: {exc}"
        log.warning("Could not open %s: %s", path, exc)
        return result

    try:
        result.pages = doc.page_count
        for idx, page in enumerate(doc, start=1):
            page_text = extraction.extract_page(page, idx, ocr_cfg)
            if page_text.via_ocr:
                result.used_ocr = True
            if not page_text.text.strip():
                continue

            page_findings: list[Finding] = []
            for det in detectors:
                page_findings.extend(det.detect(page_text.text, page=idx))

            if page_findings:
                rects = extraction.redaction_rects(page)
                for f in page_findings:
                    f.via_ocr = page_text.via_ocr
                    if rects and not page_text.via_ocr:
                        f.redacted = extraction.is_value_redacted(
                            page, f.raw_value, rects
                        )
                result.findings.extend(page_findings)
    except Exception as exc:
        result.error = f"scan failed: {exc}"
        log.warning("Error scanning %s: %s", path, exc)
    finally:
        doc.close()

    result.flagged = bool(result.findings)
    return result
