#!/usr/bin/env python3
"""Generate a sample document repository for testing the scanner.

Creates a nested folder tree of PDFs in four flavours:

* ``text``     - a valid TFN present as a normal text layer
* ``redacted`` - a valid TFN with a black box drawn over it (text still readable)
* ``scanned``  - a valid TFN rendered to an image only (no text layer -> needs OCR)
* ``clean``    - no sensitive data

Usage:
    python tools/generate_sample_pdfs.py ./sample_repo --folders 5 --per-folder 8
"""
from __future__ import annotations

import argparse
import io
import random
from pathlib import Path

import fitz  # PyMuPDF

# TFN 9-digit positional weights (must match the detector / ATO spec).
_WEIGHTS_9 = (1, 4, 3, 7, 5, 8, 6, 9, 10)


def make_valid_tfn(rng: random.Random) -> str:
    """Return a checksum-valid 9-digit TFN, formatted as ``XXX XXX XXX``."""
    while True:
        first8 = [rng.randint(0, 9) for _ in range(8)]
        total8 = sum(d * w for d, w in zip(first8, _WEIGHTS_9[:8]))
        d9 = total8 % 11           # weight of 9th digit is 10 == -1 (mod 11)
        if d9 < 10:
            digits = first8 + [d9]
            s = "".join(map(str, digits))
            assert sum(int(c) * w for c, w in zip(s, _WEIGHTS_9)) % 11 == 0
            return f"{s[:3]} {s[3:6]} {s[6:]}"


def _body(tfn: str | None) -> list[str]:
    lines = [
        "CONFIDENTIAL - Employee Record",
        "",
        "Name: Jordan Sample",
        "Address: 42 Example St, Sydney NSW 2000",
        "Date of birth: 01/01/1990",
    ]
    if tfn:
        lines.append(f"Tax File Number: {tfn}")
    lines += ["", "This document is generated for testing only."]
    return lines


def write_text_pdf(path: Path, tfn: str | None) -> None:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in _body(tfn):
        page.insert_text((72, y), line, fontsize=12)
        y += 20
    doc.save(path)
    doc.close()


def write_redacted_pdf(path: Path, tfn: str) -> None:
    """Text layer intact, but a black rectangle is drawn over the TFN line."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in _body(tfn):
        page.insert_text((72, y), line, fontsize=12)
        if line.startswith("Tax File Number"):
            # Cover just the number portion with an opaque black box.
            x0 = 72 + fitz.get_text_length("Tax File Number: ", fontsize=12)
            width = fitz.get_text_length(tfn, fontsize=12)
            rect = fitz.Rect(x0, y - 12, x0 + width + 4, y + 4)
            page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))
        y += 20
    doc.save(path)
    doc.close()


def write_scanned_pdf(path: Path, tfn: str | None) -> None:
    """Render the page to a raster image so there is no extractable text layer."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1754), "white")  # ~A4 @ 150dpi
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    y = 80
    for line in _body(tfn):
        draw.text((80, y), line, fill="black", font=font)
        y += 48

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(path)
    doc.close()


def generate(root: Path, folders: int, per_folder: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    root.mkdir(parents=True, exist_ok=True)
    counts = {"text": 0, "redacted": 0, "scanned": 0, "clean": 0}

    for fi in range(folders):
        # Mix flat and nested folders to exercise the recursive sampler.
        folder = root / f"dept_{fi}"
        if fi % 2 == 1:
            folder = folder / "subfolder"
        folder.mkdir(parents=True, exist_ok=True)

        for di in range(per_folder):
            kind = ["text", "redacted", "scanned", "clean"][di % 4]
            path = folder / f"doc_{di}_{kind}.pdf"
            if kind == "text":
                write_text_pdf(path, make_valid_tfn(rng))
            elif kind == "redacted":
                write_redacted_pdf(path, make_valid_tfn(rng))
            elif kind == "scanned":
                write_scanned_pdf(path, make_valid_tfn(rng))
            else:
                write_text_pdf(path, None)
            counts[kind] += 1
    return counts


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate sample PDFs for testing.")
    p.add_argument("output", help="Directory to create the repository in")
    p.add_argument("--folders", type=int, default=4)
    p.add_argument("--per-folder", type=int, default=8)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args(argv)

    counts = generate(Path(args.output), args.folders, args.per_folder, args.seed)
    total = sum(counts.values())
    print(f"Generated {total} PDFs in {args.output}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
