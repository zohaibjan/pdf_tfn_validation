"""Detector registry. New detectors register themselves here by name so the
YAML config can switch them on/off purely by key.
"""
from __future__ import annotations

from .base import Detector, Finding
from .tfn import TFNDetector
from .pii import PIIDetector
from .gri import GRIDetector

# Maps the YAML flag name -> detector class.
REGISTRY: dict[str, type[Detector]] = {
    "tfn": TFNDetector,
    "pii": PIIDetector,
    "gri": GRIDetector,
}


def build_detectors(config: dict) -> list[Detector]:
    """Instantiate every enabled detector from a ``detectors`` config block.

    ``config`` looks like ``{"tfn": {"enabled": True}, "pii": {...}}``.
    Unknown keys raise so typos in the YAML surface immediately.
    """
    detectors: list[Detector] = []
    for name, opts in (config or {}).items():
        opts = opts or {}
        if not opts.get("enabled", True):
            continue
        if name not in REGISTRY:
            raise ValueError(
                f"Unknown detector '{name}'. Available: {sorted(REGISTRY)}"
            )
        detectors.append(REGISTRY[name](options=opts))
    return detectors


__all__ = ["Detector", "Finding", "REGISTRY", "build_detectors"]
