"""Generic PII detection (email, phone, credit card, etc.)."""
from __future__ import annotations

import re

from .base import Detector, Finding

_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    # Australian mobile / landline, with or without country code.
    "phone_au": re.compile(
        r"(?<!\d)(?:\+?61[ -]?|0)(?:4\d{2}[ -]?\d{3}[ -]?\d{3}|[2378][ -]?\d{4}[ -]?\d{4})(?!\d)"
    ),
    "credit_card": re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
}


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class PIIDetector(Detector):
    """Detect common PII types. ``options['types']`` restricts which run."""

    def __init__(self, options: dict | None = None):
        super().__init__(name="pii", options=options or {})
        types = self.options.get("types") or list(_PATTERNS)
        self.types = [t for t in types if t in _PATTERNS]

    def detect(self, text: str, page: int = 0) -> list[Finding]:
        findings: list[Finding] = []
        for kind in self.types:
            for m in _PATTERNS[kind].finditer(text):
                value = m.group(0)
                if kind == "credit_card" and not _luhn_ok(value):
                    continue
                start, end = m.start(), m.end()
                context = text[max(0, start - 30): end + 30].replace("\n", " ").strip()
                findings.append(
                    Finding(
                        detector=self.name,
                        kind=kind,
                        raw_value=value,
                        page=page,
                        context=context,
                    )
                )
        return findings
