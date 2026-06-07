"""Load and validate the YAML scan configuration."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "detectors": {
        "tfn": {"enabled": True, "require_valid": True},
        "pii": {"enabled": False, "types": ["email", "phone_au", "credit_card"]},
        "gri": {"enabled": False, "types": ["medicare", "abn"]},
    },
    "sampling": {
        "percent": 10.0,
        "strategy": "proportional",  # proportional | equal
        "seed": None,
        "min_per_folder": 1,
    },
    "ocr": {
        "enabled": True,        # only kicks in for pages with no text layer
        "dpi": 300,
        "language": "eng",
    },
    "processing": {
        "threads": 8,
    },
    "output": {
        "flagged_dir": "./output/flagged",
        "copy_mode": "copy",    # copy | move | none
        "preserve_tree": True,
        "report": "./output/report.json",
        "mask_values": True,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Config:
    detectors: dict[str, Any] = field(default_factory=dict)
    sampling: dict[str, Any] = field(default_factory=dict)
    ocr: dict[str, Any] = field(default_factory=dict)
    processing: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None) -> "Config":
        data: dict = {}
        if path:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        merged = _deep_merge(DEFAULTS, data)
        cls._validate(merged)
        return cls(
            detectors=merged["detectors"],
            sampling=merged["sampling"],
            ocr=merged["ocr"],
            processing=merged["processing"],
            output=merged["output"],
            raw=merged,
        )

    @staticmethod
    def _validate(cfg: dict) -> None:
        pct = cfg["sampling"]["percent"]
        if not (0 < pct <= 100):
            raise ValueError(f"sampling.percent must be in (0, 100], got {pct}")
        if cfg["sampling"]["strategy"] not in {"proportional", "equal"}:
            raise ValueError("sampling.strategy must be 'proportional' or 'equal'")
        if cfg["output"]["copy_mode"] not in {"copy", "move", "none"}:
            raise ValueError("output.copy_mode must be 'copy', 'move' or 'none'")
        if int(cfg["processing"]["threads"]) < 1:
            raise ValueError("processing.threads must be >= 1")
        if not any(d.get("enabled", True) for d in cfg["detectors"].values()):
            raise ValueError("at least one detector must be enabled")
