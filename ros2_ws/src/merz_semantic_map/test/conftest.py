"""Make this package importable in tests on Windows, where it has not been installed by colcon."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
