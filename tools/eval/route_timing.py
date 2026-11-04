"""O6 query time and O7 route correctness, measured through the website's real API.

    python tools/eval/route_timing.py --url http://localhost:8000 --routes routes.csv --repeats 20 --plot times.png

The routes CSV has columns entrance,room,expected (junction ids separated by spaces, from walking the route by hand; leave
it empty to only time the query). Targets: every query under 1 s; at least 9 of 10 routes correct.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Callable
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COLOUR_PRIMARY, STATS_HEADERS, describe, format_table, new_figure, pass_fail, read_csv,  # noqa: E402
                    save_figure, stats_row)
from common import stats_dict, write_json  # noqa: E402,F401

TARGET_S = 1.0
TARGET_CORRECT = 0.9

Query = Callable[[str, str], dict]


@dataclass(frozen=True)
class RouteResult:
    entrance: str
    room: str
    expected: list[int]
    actual: list[int]
    times_s: list[float]

    @property
    def correct(self) -> bool | None:
        return self.actual == self.expected if self.expected else None


def http_query(base_url: str) -> Query:
    def query(entrance: str, room: str) -> dict:
        arguments = urllib.parse.urlencode({'entrance': entrance, 'room': room})
        with urllib.request.urlopen(f'{base_url}/route?{arguments}', timeout=10) as response:
            return json.load(response)
    return query


def measure(routes: list[dict], query: Query, repeats: int) -> list[RouteResult]:
    results = []
    for row in routes:
        times = []
        actual: list[int] = []
        for _ in range(repeats):
            start = time.perf_counter()
            reply = query(row['entrance'], row['room'])
            times.append(time.perf_counter() - start)
            actual = [step['junction_id'] for step in reply['steps']]
        expected = [int(v) for v in row.get('expected', '').split()]
        results.append(RouteResult(row['entrance'], row['room'], expected, actual, times))
    return results


def plot(times_ms: list[float], path: Path) -> None:
    figure, axes = new_figure()
    axes.hist(times_ms, bins=30, color=COLOUR_PRIMARY, edgecolor='white', linewidth=0.5)
    axes.set_xlabel('Route query time (ms)')
    axes.set_ylabel('Queries')
    save_figure(figure, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', default='http://localhost:8000')
    parser.add_argument('--routes', required=True)
    parser.add_argument('--repeats', type=int, default=20)
    parser.add_argument('--plot', type=Path)
    parser.add_argument('--json', type=Path, help='Also save the numbers as JSON, for tools/web_import.py.')
    args = parser.parse_args()
    results = measure(read_csv(args.routes), http_query(args.url.rstrip('/')), args.repeats)
    print(format_table(['entrance', 'room', 'route', 'expected', 'correct'],
                       [[r.entrance, r.room, ' '.join(map(str, r.actual)), ' '.join(map(str, r.expected)),
                         {True: 'yes', False: 'NO', None: '-'}[r.correct]] for r in results]))
    times = [t for r in results for t in r.times_s]
    stats = describe(times)
    print()
    print(format_table(STATS_HEADERS, [stats_row('query time (s)', stats)]))
    print(f'All queries < {TARGET_S} s: {pass_fail(stats.maximum < TARGET_S)}')
    judged = [r for r in results if r.correct is not None]
    if judged:
        correct = sum(1 for r in judged if r.correct)
        print(f'Routes correct: {correct} of {len(judged)}: {pass_fail(correct / len(judged) >= TARGET_CORRECT)}')
    if args.plot:
        plot([t * 1000.0 for t in times], args.plot)
    if args.json:
        correct = sum(1 for r in judged if r.correct)
        write_json(args.json, 'O6-O7', 'route_timing', None,
                   {'time_stats_s': stats_dict(stats), 'target_s': TARGET_S, 'o6_passed': stats.maximum < TARGET_S,
                    'routes_judged': len(judged), 'routes_correct': correct, 'target_correct': TARGET_CORRECT,
                    'o7_passed': (correct / len(judged) >= TARGET_CORRECT) if judged else None,
                    'times_ms': [round(t * 1000.0, 3) for t in times],
                    'routes': [{'entrance': r.entrance, 'room': r.room, 'expected': r.expected, 'actual': r.actual,
                                'correct': r.correct, 'max_ms': round(max(r.times_s) * 1000.0, 3)} for r in results]},
                   {'url': args.url, 'routes': args.routes, 'repeats': args.repeats})


if __name__ == '__main__':
    main()
