"""Score sign reading against ground truth: the PROPOSED O3 measurement for the prototype.

    python score_ocr.py --truth truth.csv --results results.json [--json score.json]

truth.csv columns:
    image     file name as written in results.json ("image" field)
    text      the room number exactly as printed on the sign (written on foot, before running the pipeline)
    sign_id   optional; several photos of the same sign share one id. Defaults to the text itself.

Two numbers are reported:
    per-photo:  share of photos whose best room number equals the truth (after normalising).
    per-sign:   a sign is read correctly if the most common non-empty read over its photos (a plurality vote; a tie
                counts as wrong) is the right number. This is the O3 figure (target >= 85% of signs). A sign with no
                read in any photo counts as not correct.
Wrong numbers ("false reads") are listed separately: a wrong room in the database misdirects a visitor, which is
worse than a missed one. Photos missing from the results count as "no read".
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merz_signs.room_parser import normalise  # noqa: E402

TARGET_PERCENT = 85.0


def read_truth(path: Path) -> list[dict[str, str]]:
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = [r for r in csv.DictReader(f) if (r.get('text') or '').strip()]
    for row in rows:
        row['text'] = normalise(row['text'])
        row['sign_id'] = (row.get('sign_id') or '').strip() or row['text']
    return rows


def score(truth: list[dict[str, str]], reads: dict[str, str | None]) -> dict:
    photo_rows = []
    by_sign: dict[str, list[str | None]] = defaultdict(list)
    sign_text: dict[str, str] = {}
    for row in truth:
        read = reads.get(row['image'])
        read = normalise(read) if read else None
        photo_rows.append({'image': row['image'], 'truth': row['text'], 'read': read, 'correct': read == row['text']})
        by_sign[row['sign_id']].append(read)
        sign_text[row['sign_id']] = row['text']

    signs = []
    for sign_id, sign_reads in by_sign.items():
        votes = Counter(r for r in sign_reads if r)
        top = votes.most_common(2)
        majority = None
        if top and (len(top) == 1 or top[0][1] > top[1][1]):
            majority = top[0][0]
        signs.append({'sign_id': sign_id, 'truth': sign_text[sign_id], 'photos': len(sign_reads),
                      'majority_read': majority, 'correct': majority == sign_text[sign_id]})

    n_photos, n_signs = len(photo_rows), len(signs)
    photo_ok = sum(r['correct'] for r in photo_rows)
    sign_ok = sum(s['correct'] for s in signs)
    percent = 100.0 * sign_ok / n_signs if n_signs else 0.0
    return {
        'photos': n_photos, 'photos_correct': photo_ok,
        'photo_percent': 100.0 * photo_ok / n_photos if n_photos else 0.0,
        'photos_no_read': sum(r['read'] is None for r in photo_rows),
        'photos_false_read': sum(r['read'] is not None and not r['correct'] for r in photo_rows),
        'signs': n_signs, 'signs_correct': sign_ok, 'sign_percent': percent,
        'target_percent': TARGET_PERCENT, 'pass': percent >= TARGET_PERCENT and n_signs > 0,
        'per_photo': photo_rows, 'per_sign': signs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--truth', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True, help='JSON from run.py')
    parser.add_argument('--json', type=Path, help='also save the full score as JSON')
    args = parser.parse_args()

    records = json.loads(args.results.read_text(encoding='utf-8'))
    reads = {r['image']: r.get('room_number') for r in records}
    result = score(read_truth(args.truth), reads)

    print(f"Photos: {result['photos_correct']}/{result['photos']} correct ({result['photo_percent']:.1f}%), "
          f"{result['photos_no_read']} no read, {result['photos_false_read']} false reads")
    print(f"Signs (plurality vote over photos): {result['signs_correct']}/{result['signs']} correct "
          f"({result['sign_percent']:.1f}%)  target >= {TARGET_PERCENT:.0f}%: {'PASS' if result['pass'] else 'FAIL'}")
    wrong = [r for r in result['per_photo'] if not r['correct']]
    for r in wrong:
        print(f"  {r['image']}: truth {r['truth']}, read {r['read'] or '-'}")
    if args.json:
        args.json.write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
