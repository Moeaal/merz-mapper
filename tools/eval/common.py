"""Shared helpers for the evaluation scripts: statistics, tables, CSV reading, plot style. No ROS needed."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
import sys
from typing import Iterable, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
# The evaluation reads saved maps with the same code the robot uses, so that the two can never disagree.
sys.path.insert(0, str(REPO_ROOT / 'ros2_ws' / 'src' / 'merz_exploration'))

from merz_exploration.map_io import FREE, OCCUPIED, GridMap, load_map  # noqa: E402,F401

# Dark enough to print in greyscale at different weights. Checked with the dataviz validator.
COLOUR_PRIMARY = '#1f5f99'
COLOUR_SECONDARY = '#c8551b'
FIGURE_SIZE = (3.5, 2.6)   # inches: one IEEE column wide


@dataclass(frozen=True)
class Stats:
    count: int
    mean: float
    sd: float
    maximum: float
    rmse: float
    ci95: float      # half-width of the 95% confidence interval on the mean


# Two-sided 97.5% Student t values, by degrees of freedom. Beyond 30 the normal value is close enough.
_T_975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
          11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
          21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def describe(values: Iterable[float]) -> Stats:
    """Return summary statistics. RMSE treats each value as an error from zero."""
    data = np.asarray(list(values), dtype=float)
    if data.size == 0:
        raise ValueError('No values to describe')
    sd = float(data.std(ddof=1)) if data.size > 1 else 0.0
    t_value = _T_975.get(data.size - 1, 1.96)
    ci95 = t_value * sd / math.sqrt(data.size) if data.size > 1 else float('nan')
    return Stats(int(data.size), float(data.mean()), sd, float(data.max()), float(np.sqrt(np.mean(data ** 2))), ci95)


def format_table(headers: Sequence[str], rows: Iterable[Sequence]) -> str:
    """Return a plain text table, with columns wide enough to fit."""
    text_rows = [[f'{v:.3f}' if isinstance(v, float) else str(v) for v in row] for row in rows]
    widths = [max(len(str(h)), *(len(r[i]) for r in text_rows)) if text_rows else len(str(h))
              for i, h in enumerate(headers)]
    lines = ['  '.join(str(h).ljust(w) for h, w in zip(headers, widths)), '  '.join('-' * w for w in widths)]
    lines += ['  '.join(v.ljust(w) for v, w in zip(row, widths)) for row in text_rows]
    return '\n'.join(lines)


def stats_row(label: str, stats: Stats) -> list:
    return [label, stats.count, stats.mean, stats.sd, stats.maximum, stats.rmse, stats.ci95]


STATS_HEADERS = ['', 'n', 'mean', 'sd', 'max', 'rmse', 'ci95']


def pass_fail(passed: bool) -> str:
    return 'PASS' if passed else 'FAIL'


def read_csv(path: str | Path) -> list[dict]:
    with open(path, newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def query_database(path: str | Path, sql: str, parameters: Sequence = ()) -> list[dict]:
    """Read from the robot's database, opened read-only so that evaluating can never alter a result."""
    connection = sqlite3.connect(f'file:{Path(path).expanduser().as_posix()}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(sql, parameters)]
    finally:
        connection.close()


def new_figure():
    """Return (figure, axes) with a style that prints cleanly in a two-column paper."""
    import matplotlib
    matplotlib.use('Agg')   # no display is needed, and this works on a headless Jetson
    import matplotlib.pyplot as plt

    plt.rcParams.update({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'grid.color': '#d9d9d9', 'grid.linewidth': 0.5,
                         'axes.axisbelow': True, 'savefig.dpi': 300})
    return plt.subplots(figsize=FIGURE_SIZE, layout='constrained')


def save_figure(figure, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    import matplotlib.pyplot as plt
    plt.close(figure)
