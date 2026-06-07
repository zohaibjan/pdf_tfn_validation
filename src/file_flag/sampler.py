"""Stratified sampling of files across a nested document repository.

The repository contains folders and sub-folders. To avoid a single large
folder dominating the sample, files are grouped by their containing folder and
sampled per-folder ("stratified" sampling).

Two strategies are supported:

``proportional``
    Take ``percent`` of the files in *each* folder (rounded up, at least
    ``min_per_folder``). Folders keep their relative weight.

``equal``
    Compute a global budget of ``percent`` of all files, then draw the *same*
    number of files from every folder (subject to availability). This matches a
    literal reading of "equal number of files from each folder".
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path


def discover(root: str | Path, extensions=(".pdf",)) -> dict[Path, list[Path]]:
    """Return a mapping of folder -> list of matching files directly inside it."""
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"Repository not found: {root}")
    exts = {e.lower() for e in extensions}
    by_folder: dict[Path, list[Path]] = defaultdict(list)
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            by_folder[p.parent].append(p)
    return dict(by_folder)


def sample(
    by_folder: dict[Path, list[Path]],
    percent: float,
    strategy: str = "proportional",
    seed: int | None = None,
    min_per_folder: int = 1,
) -> list[Path]:
    """Return the sampled files according to ``strategy``."""
    rng = random.Random(seed)
    selected: list[Path] = []

    if strategy == "equal":
        total = sum(len(v) for v in by_folder.values())
        budget = math.ceil(total * percent / 100.0)
        n_folders = len(by_folder) or 1
        per_folder = max(min_per_folder, math.ceil(budget / n_folders))
        for files in by_folder.values():
            k = min(per_folder, len(files))
            selected.extend(rng.sample(files, k))
        return sorted(selected)

    # proportional (default)
    for files in by_folder.values():
        if not files:
            continue
        k = max(min_per_folder, math.ceil(len(files) * percent / 100.0))
        k = min(k, len(files))
        selected.extend(rng.sample(files, k))
    return sorted(selected)


def plan(root, percent, strategy="proportional", seed=None,
         min_per_folder=1, extensions=(".pdf",)) -> tuple[list[Path], dict]:
    """Convenience wrapper returning (sampled_files, stats)."""
    by_folder = discover(root, extensions)
    files = sample(by_folder, percent, strategy, seed, min_per_folder)
    stats = {
        "folders": len(by_folder),
        "total_files": sum(len(v) for v in by_folder.values()),
        "sampled_files": len(files),
        "strategy": strategy,
        "percent": percent,
    }
    return files, stats
