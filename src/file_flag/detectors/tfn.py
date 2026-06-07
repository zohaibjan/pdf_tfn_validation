"""Australian Tax File Number (TFN) detection and validation.

A TFN is an 8 or 9 digit identifier. Validity is established with a weighted
modulus-11 checksum published by the Australian Taxation Office: each digit is
multiplied by a positional weight, the products are summed, and a valid number
has a sum that is exactly divisible by 11.
"""
from __future__ import annotations

import re

from .base import Detector, Finding

# Positional weights defined by the ATO.
_WEIGHTS_9 = (1, 4, 3, 7, 5, 8, 6, 9, 10)
_WEIGHTS_8 = (10, 7, 8, 4, 6, 3, 5, 1)

# Candidate runs of 8-9 digits, optionally split into 3-3-3 / 3-3-2 groups by a
# single space or hyphen. Word boundaries keep us from matching inside longer
# numbers (e.g. credit cards or phone numbers).
_CANDIDATE = re.compile(
    r"(?<![\d])(\d{3})[ \-]?(\d{3})[ \-]?(\d{2,3})(?![\d])"
)


def is_valid_tfn(digits: str) -> bool:
    """Return ``True`` if ``digits`` (8 or 9 digit string) passes the checksum."""
    if not digits.isdigit():
        return False
    if len(digits) == 9:
        weights = _WEIGHTS_9
    elif len(digits) == 8:
        weights = _WEIGHTS_8
    else:
        return False
    total = sum(int(d) * w for d, w in zip(digits, weights))
    return total % 11 == 0


class TFNDetector(Detector):
    """Find numbers that look like TFNs and keep only those that validate."""

    def __init__(self, options: dict | None = None):
        super().__init__(name="tfn", options=options or {})
        # When False, any TFN-shaped number is reported even if the checksum
        # fails. Defaults to True so only genuinely valid TFNs are flagged.
        self.require_valid = self.options.get("require_valid", True)

    def detect(self, text: str, page: int = 0) -> list[Finding]:
        findings: list[Finding] = []
        for m in _CANDIDATE.finditer(text):
            digits = "".join(m.groups())
            valid = is_valid_tfn(digits)
            if self.require_valid and not valid:
                continue
            start, end = m.start(), m.end()
            context = text[max(0, start - 30): end + 30].replace("\n", " ").strip()
            findings.append(
                Finding(
                    detector=self.name,
                    kind="tfn",
                    raw_value=m.group(0),
                    page=page,
                    context=context,
                    confidence=1.0 if valid else 0.4,
                )
            )
        return findings
