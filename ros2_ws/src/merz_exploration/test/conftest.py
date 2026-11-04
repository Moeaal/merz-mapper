"""Make this package, and merz_semantic_map which it uses, importable in tests on Windows."""
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE.parent / 'merz_semantic_map'))
