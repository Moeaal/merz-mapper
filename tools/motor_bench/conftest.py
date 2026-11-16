"""Make motor_bench_test importable whichever folder pytest is started from."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
