"""O4 landmark accuracy: the horizontal distance between each landmark and its laser-measured position.

    python tools/eval/landmark_error.py --truth landmarks_truth.csv --database merz.sqlite --plot errors.png

The truth CSV has columns class,text,x,y (metres, map frame). Signs are matched by text. Anything without text is matched
to the nearest same-class landmark within --gate. Unmatched truth rows are listed, not silently dropped, as ignoring
missing landmarks would flatter the mean. Target: mean <=0.5 m.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COLOUR_PRIMARY, STATS_HEADERS, describe, format_table, new_figure, pass_fail, query_database,  # noqa: E402
                    read_csv, save_figure, stats_row)

TARGET_M = 0.5


@dataclass(frozen=True)
class Match:
    truth: dict
    landmark: dict
    error_m: float


def match_landmarks(truth: list[dict], landmarks: list[dict], gate_m: float) -> tuple[list[Match], list[dict]]:
    """Each landmark is matched at most once. Text matches go first, as they are unambiguous."""
    matches: list[Match] = []
    unmatched: list[dict] = []
    available = list(landmarks)

    def take(row: dict, candidates: list[dict]) -> bool:
        if not candidates:
            return False
        x, y = float(row['x']), float(row['y'])
        best = min(candidates, key=lambda lm: math.hypot(lm['x'] - x, lm['y'] - y))
        error = math.hypot(best['x'] - x, best['y'] - y)
        if error > gate_m:
            return False
        matches.append(Match(row, best, error))
        available.remove(best)
        return True

    with_text = [row for row in truth if row.get('text', '').strip()]
    without_text = [row for row in truth if not row.get('text', '').strip()]
    for row in with_text:
        if not take(row, [lm for lm in available if lm['text'] == row['text'].strip()]):
            unmatched.append(row)
    for row in without_text:
        if not take(row, [lm for lm in available if lm['class'] == row['class']]):
            unmatched.append(row)
    return matches, unmatched


def plot(errors: list[float], path: Path) -> None:
    figure, axes = new_figure()
    axes.hist(errors, bins=min(15, max(5, len(errors))), color=COLOUR_PRIMARY, edgecolor='white', linewidth=0.5)
    axes.axvline(TARGET_M, color='black', linestyle='--', linewidth=1, label=f'Target {TARGET_M} m')
    axes.set_xlabel('Landmark position error (m)')
    axes.set_ylabel('Landmarks')
    axes.legend(frameon=False)
    save_figure(figure, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--truth', required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--gate', type=float, default=2.0, help='Metres. Decide this before the run.')
    parser.add_argument('--plot', type=Path)
    args = parser.parse_args()
    matches, unmatched = match_landmarks(read_csv(args.truth), query_database(args.database, 'SELECT * FROM landmarks'),
                                         args.gate)
    if not matches:
        sys.exit('No landmarks matched the truth list.')
    errors = [m.error_m for m in matches]
    stats = describe(errors)
    print(format_table(['class', 'text', 'db id', 'seen', 'error m'],
                       [[m.truth['class'], m.truth.get('text', ''), m.landmark['id'],
                         m.landmark['observation_count'], m.error_m] for m in matches]))
    print()
    print(format_table(STATS_HEADERS, [stats_row('error (m)', stats)]))
    print(f'Unmatched truth rows: {len(unmatched)} of {len(matches) + len(unmatched)}')
    print(f'Mean <= {TARGET_M} m: {pass_fail(stats.mean <= TARGET_M)}')
    if args.plot:
        plot(errors, args.plot)


if __name__ == '__main__':
    main()
