"""Multi-threaded orchestration: sample -> scan -> flag -> report."""
from __future__ import annotations

import logging
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import Config
from .detectors import build_detectors
from .scanner import ScanResult, scan_file

log = logging.getLogger(__name__)


def _route_flagged(result: ScanResult, repo_root: Path, out_cfg: dict) -> None:
    """Copy or move a flagged file into the output directory."""
    mode = out_cfg.get("copy_mode", "copy")
    if mode == "none":
        return
    dest_dir = Path(out_cfg["flagged_dir"])
    if out_cfg.get("preserve_tree", True):
        try:
            rel = result.path.resolve().relative_to(repo_root.resolve())
            dest = dest_dir / rel
        except ValueError:
            dest = dest_dir / result.path.name
    else:
        dest = dest_dir / result.path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == "move":
        shutil.move(str(result.path), str(dest))
    else:
        shutil.copy2(str(result.path), str(dest))


def run(files: list[Path], repo_root: Path, config: Config,
        progress=None) -> list[ScanResult]:
    """Scan ``files`` concurrently and route flagged files. Returns all results.

    A fresh detector set is built per worker thread because detector instances,
    while logically stateless per document, are cheap and this avoids any
    accidental shared mutable state.
    """
    threads = int(config.processing.get("threads", 8))
    ocr_cfg = config.ocr
    results: list[ScanResult] = []
    lock = threading.Lock()
    done = 0

    # Detectors are stateless across documents, so one shared set is safe and
    # avoids rebuilding regexes for every file.
    detectors = build_detectors(config.detectors)

    def work(path: Path) -> ScanResult:
        return scan_file(path, detectors, ocr_cfg)

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {pool.submit(work, f): f for f in files}
        for fut in as_completed(futures):
            result = fut.result()
            if result.flagged:
                try:
                    _route_flagged(result, repo_root, config.output)
                except Exception as exc:
                    log.warning("Failed to route %s: %s", result.path, exc)
            with lock:
                results.append(result)
                done += 1
                if progress:
                    progress(done, len(files), result)
    return results
