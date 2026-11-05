"""Make this package (and merz_base, whose BaseController the simulated base uses) importable without colcon."""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SRC / 'merz_sim'))
sys.path.insert(0, str(SRC / 'merz_base'))
