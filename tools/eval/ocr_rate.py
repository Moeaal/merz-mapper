"""O3 sign reading: the share of real signs read correctly, compared with a manual list.

    python tools/eval/ocr_rate.py --truth signs.csv --database merz.sqlite
    python tools/eval/ocr_rate.py --truth signs.csv --results offline_results.csv

The truth CSV has a column "text": each sign's number exactly as written. Results come from the robot's database or from
merz_perception.offline_batch. Texts are compared exactly, after normalising. Target: >=85%.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import format_table, pass_fail, query_database, read_csv  # noqa: E402
from common import stats_dict, write_json  # noqa: E402,F401

TARGET_PERCENT = 85.0


def normalise(text: str) -> str:
    return text.upper().replace(' ', '')


@dataclass(frozen=True)
class ReadRate:
    total_signs: int
    correct: set[str]
    missed: set[str]
    false_reads: set[str]

    @property
    def percent(self) -> float:
        return 100.0 * len(self.correct) / self.total_signs if self.total_signs else 0.0


def score(truth: list[str], read: list[str]) -> ReadRate:
    """False reads are reported separately, as a wrong number in the database can send a visitor the wrong way."""
    truth_set = {normalise(t) for t in truth if t.strip()}
    read_set = {normalise(r) for r in read if r.strip()}
    return ReadRate(len(truth_set), truth_set & read_set, truth_set - read_set, read_set - truth_set)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--truth', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--database')
    source.add_argument('--results')
    parser.add_argument('--json', type=Path, help='Also save the numbers as JSON, for tools/web_import.py.')
    args = parser.parse_args()
    truth = [row['text'] for row in read_csv(args.truth)]
    if args.database:
        read = [row['text'] for row in query_database(args.database, "SELECT text FROM landmarks WHERE text <> ''")]
    else:
        read = [row['room_number'] for row in read_csv(args.results)]
    result = score(truth, read)
    print(format_table(['signs', 'correct', 'missed', 'false reads', 'read rate %', f'>={TARGET_PERCENT:.0f}%'],
                       [[result.total_signs, len(result.correct), len(result.missed), len(result.false_reads),
                         result.percent, pass_fail(result.percent >= TARGET_PERCENT)]]))
    print('Missed:', ', '.join(sorted(result.missed)) or 'none')
    print('False reads:', ', '.join(sorted(result.false_reads)) or 'none')
    if args.json:
        write_json(args.json, 'O3', 'ocr_rate', result.percent >= TARGET_PERCENT,
                   {'signs': result.total_signs, 'correct': sorted(result.correct), 'missed': sorted(result.missed),
                    'false_reads': sorted(result.false_reads), 'percent': result.percent,
                    'target_percent': TARGET_PERCENT}, {'truth': args.truth, 'database': args.database,
                                                        'results': args.results})


if __name__ == '__main__':
    main()
