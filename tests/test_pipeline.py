from pathlib import Path

from file_flag import scanner
from file_flag.config import Config
from file_flag.detectors import build_detectors
from file_flag import pipeline
from tools import generate_sample_pdfs as gen


def _detectors():
    return build_detectors({"tfn": {"enabled": True}})


def test_text_tfn_is_flagged(tmp_path):
    p = tmp_path / "a.pdf"
    gen.write_text_pdf(p, "123 456 782")
    res = scanner.scan_file(p, _detectors(), {"enabled": False})
    assert res.flagged
    assert res.findings[0].kind == "tfn"


def test_clean_file_not_flagged(tmp_path):
    p = tmp_path / "clean.pdf"
    gen.write_text_pdf(p, None)
    res = scanner.scan_file(p, _detectors(), {"enabled": False})
    assert not res.flagged


def test_redacted_tfn_still_detected_and_marked(tmp_path):
    p = tmp_path / "redacted.pdf"
    gen.write_redacted_pdf(p, "123 456 782")
    res = scanner.scan_file(p, _detectors(), {"enabled": False})
    assert res.flagged, "text under a redaction box must still be extracted"
    assert any(f.redacted for f in res.findings), "finding should be marked redacted"


def test_pipeline_routes_flagged_files(tmp_path):
    repo = tmp_path / "repo"
    gen.generate(repo, folders=2, per_folder=4, seed=3)
    files = sorted(repo.rglob("*.pdf"))

    cfg = Config.load(None)
    cfg.detectors = {"tfn": {"enabled": True}}
    cfg.ocr = {"enabled": False}
    cfg.output["flagged_dir"] = str(tmp_path / "out")
    cfg.output["copy_mode"] = "copy"

    results = pipeline.run(files, repo, cfg)
    flagged = [r for r in results if r.flagged]
    # text + redacted variants carry valid TFNs (scanned needs OCR, skipped here)
    assert len(flagged) >= 2
    copied = list((tmp_path / "out").rglob("*.pdf"))
    assert len(copied) == len(flagged)
