import sys
from pathlib import Path

# Make the src/ layout importable without installation.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (SRC, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
