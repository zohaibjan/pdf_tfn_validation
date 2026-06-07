#!/usr/bin/env bash
# Rebuild the offline wheel bundle for a given target platform / Python version.
# Run this on a machine WITH internet, then copy the whole offline/ folder to
# the air-gapped client.
#
# Usage:
#   ./build_bundle.sh                       # defaults: win_amd64, py 3.11
#   PLATFORM=manylinux2014_x86_64 PYVER=312 ./build_bundle.sh
#   PLATFORM=macosx_11_0_arm64    PYVER=311 ./build_bundle.sh
set -euo pipefail

PLATFORM="${PLATFORM:-win_amd64}"
PYVER="${PYVER:-311}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WHEELS="$HERE/wheels"

echo "Building bundle for platform=$PLATFORM python=$PYVER -> $WHEELS"
rm -rf "$WHEELS"
mkdir -p "$WHEELS"

# Third-party deps + pip tooling.
python3 -m pip download \
  --only-binary=:all: \
  --platform "$PLATFORM" --python-version "$PYVER" --implementation cp --abi "cp$PYVER" \
  -d "$WHEELS" \
  PyMuPDF PyYAML pytesseract Pillow pip setuptools wheel

# file_flag itself (pure-python, universal wheel).
python3 -m pip wheel "$ROOT" --no-deps -w "$WHEELS"

echo "Done. Contents:"
ls -1 "$WHEELS"
