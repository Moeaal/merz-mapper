"""O5 access zones: the database compared with a manual walk-through survey.

    python tools/eval/access_zone_compare.py --survey survey.csv --database merz.sqlite

The survey CSV has columns entrance,room,reachable (yes/no), filled in on foot. Target: all pairs match.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import format_table, pass_fail, query_database, read_csv  # noqa: E402


@dataclass(frozen=True)
class Comparison:
    both_yes: int
    both_no: int
    extra: list[tuple[str, str]]     # the map says reachable, the survey says not: would send a visitor to a locked door
    missing: list[tuple[str, str]]   # the survey says reachable, the map does not

    @property
    def total(self) -> int:
        return self.both_yes + self.both_no + len(self.extra) + len(self.missing)

    @property
    def agreement_percent(self) -> float:
        return 100.0 * (self.both_yes + self.both_no) / self.total if self.total else 0.0


def compare(survey: list[dict], mapped: set[tuple[str, str]]) -> Comparison:
    both_yes = both_no = 0
    extra, missing = [], []
    for row in survey:
        pair = (row['entrance'].strip(), row['room'].strip())
        surveyed = row['reachable'].strip().lower() in {'yes', 'y', 'true', '1'}
        in_map = pair in mapped
        if surveyed and in_map:
            both_yes += 1
        elif not surveyed and not in_map:
            both_no += 1
        elif in_map:
            extra.append(pair)
        else:
            missing.append(pair)
    return Comparison(both_yes, both_no, extra, missing)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--survey', required=True)
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    rows = query_database(args.database, """SELECT z.entrance_id AS entrance, l.text AS room FROM access_zones z
                                            JOIN landmarks l ON l.id = z.landmark_id WHERE l.text <> ''""")
    result = compare(read_csv(args.survey), {(r['entrance'], r['room']) for r in rows})
    print(format_table(['pairs', 'both yes', 'both no', 'only in map', 'only in survey', 'agreement %', 'all match'],
                       [[result.total, result.both_yes, result.both_no, len(result.extra), len(result.missing),
                         result.agreement_percent, pass_fail(not result.extra and not result.missing)]]))
    for label, pairs in (('Only in map', result.extra), ('Only in survey', result.missing)):
        for entrance, room in pairs:
            print(f'{label}: {entrance} -> {room}')


if __name__ == '__main__':
    main()
