"""O8 fused against single-sensor comparison, from one run's stored observations.

    python tools/eval/fusion_compare.py --truth landmarks_truth.csv --database merz.sqlite --plot fusion.png

For each landmark seen at least --min-observations times, this compares the error of a single observation (the first, as
if the robot had looked once) with the fused estimate (the mean of all observations). Because both use the same landmarks,
the comparison is paired. The primary O8 comparison has still to be agreed with the supervisor (see docs/EXPERIMENTS.md).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COLOUR_PRIMARY, COLOUR_SECONDARY, STATS_HEADERS, describe, format_table, new_figure,  # noqa: E402
                    query_database, read_csv, save_figure, stats_row)
from landmark_error import match_landmarks  # noqa: E402


@dataclass(frozen=True)
class PairedError:
    landmark_id: int
    single_m: float
    fused_m: float


def paired_errors(truth: list[dict], landmarks: list[dict], observations: list[dict], gate_m: float,
                  min_observations: int = 2) -> list[PairedError]:
    by_landmark: dict[int, list[dict]] = {}
    for row in sorted(observations, key=lambda o: (o['stamp'] is None, o['stamp'], o['id'])):
        by_landmark.setdefault(row['landmark_id'], []).append(row)
    matches, _ = match_landmarks(truth, landmarks, gate_m)
    pairs = []
    for match in matches:
        seen = by_landmark.get(match.landmark['id'], [])
        if len(seen) < min_observations:
            continue
        x, y = float(match.truth['x']), float(match.truth['y'])
        fused_x = float(np.mean([o['x'] for o in seen]))
        fused_y = float(np.mean([o['y'] for o in seen]))
        pairs.append(PairedError(match.landmark['id'], math.hypot(seen[0]['x'] - x, seen[0]['y'] - y),
                                 math.hypot(fused_x - x, fused_y - y)))
    return pairs


def plot(pairs: list[PairedError], path: Path) -> None:
    """One slope line per landmark: this shows each pair, which a pair of means would hide."""
    figure, axes = new_figure()
    for pair in pairs:
        axes.plot([0, 1], [pair.single_m, pair.fused_m], color='#9a9a9a', linewidth=0.6, zorder=1)
    # The x-axis names both groups, so no legend is needed. Marker shape also tells them apart in greyscale.
    axes.scatter([0] * len(pairs), [p.single_m for p in pairs], color=COLOUR_SECONDARY, marker='s', s=14, zorder=2)
    axes.scatter([1] * len(pairs), [p.fused_m for p in pairs], color=COLOUR_PRIMARY, marker='o', s=14, zorder=2)
    axes.set_xticks([0, 1], ['Single observation', 'Fused'])
    axes.set_xlim(-0.3, 1.3)
    axes.set_ylim(bottom=0)
    axes.set_ylabel('Landmark position error (m)')
    axes.grid(axis='x', visible=False)
    save_figure(figure, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--truth', required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--gate', type=float, default=2.0, help='Metres. Decide this before the run.')
    parser.add_argument('--min-observations', type=int, default=2)
    parser.add_argument('--plot', type=Path)
    args = parser.parse_args()
    pairs = paired_errors(read_csv(args.truth), query_database(args.database, 'SELECT * FROM landmarks'),
                          query_database(args.database, 'SELECT * FROM observations'), args.gate,
                          args.min_observations)
    if not pairs:
        sys.exit('No landmark had enough observations to compare.')
    improvement = [p.single_m - p.fused_m for p in pairs]
    print(format_table(STATS_HEADERS, [
        stats_row('single (m)', describe(p.single_m for p in pairs)),
        stats_row('fused (m)', describe(p.fused_m for p in pairs)),
    ]))
    stats = describe(improvement)
    print(f'\nPaired improvement (single - fused): mean {stats.mean:.3f} m, 95% CI +/-{stats.ci95:.3f} m, n={stats.count}')
    print(f'Fused was better for {sum(1 for v in improvement if v > 0)} of {len(pairs)} landmarks')
    if args.plot:
        plot(pairs, args.plot)


if __name__ == '__main__':
    main()
