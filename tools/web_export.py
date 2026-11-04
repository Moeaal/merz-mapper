"""Export the website as plain static files (no server needed), e.g. for GitHub Pages.

    python tools/web_export.py --out _site --base /merz-mapper/

The site reads everything from the data bundle (web/data, made by tools/web_import.py), so it works the same with or
without the FastAPI server. Routes are pre-computed by the importer with the API's own routing code. The API copy of
the database (data/<run>/api) is left out of the export, as nothing in the browser needs it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
DIST = REPO / 'web' / 'dist'
DATA = REPO / 'web' / 'data'
PAGES = ['find', 'mission', 'results', 'about']


def export(out: Path, base: str = '/', runs: list[str] | None = None) -> Path:
    if not (DIST / 'index.html').is_file():
        raise SystemExit('web/dist is missing: build the site first (see web/README.md).')
    base = '/' + base.strip('/') + '/' if base.strip('/') else '/'
    index = json.loads((DATA / 'index.json').read_text())
    chosen = [r for r in index['runs'] if runs is None or r['id'] in runs]
    if not chosen:
        raise SystemExit('No runs to export.')
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    for run in chosen:
        shutil.copytree(DATA / run['id'], out / 'data' / run['id'], ignore=shutil.ignore_patterns('api'))
    default = index['default'] if any(r['id'] == index['default'] for r in chosen) else chosen[0]['id']
    (out / 'data' / 'index.json').write_text(json.dumps({'default': default, 'runs': chosen}, separators=(',', ':')))
    html = (out / 'index.html').read_text(encoding='utf-8')
    if '<base href="/">' not in html:
        raise SystemExit('index.html has no <base href="/"> to rewrite.')
    html = html.replace('<base href="/">', f'<base href="{base}">')
    (out / 'index.html').write_text(html, encoding='utf-8')
    # GitHub Pages has no rewrites: give each page its own copy, and use the same page for 404s.
    for page in PAGES:
        (out / page).mkdir(exist_ok=True)
        (out / page / 'index.html').write_text(html, encoding='utf-8')
    (out / '404.html').write_text(html, encoding='utf-8')
    (out / '.nojekyll').write_text('')
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=REPO / '_site')
    parser.add_argument('--base', default='/', help='URL path the site is served from, e.g. /merz-mapper/')
    parser.add_argument('--runs', help='Comma-separated run ids (default: all in web/data/index.json)')
    args = parser.parse_args()
    out = export(args.out, args.base, args.runs.split(',') if args.runs else None)
    size = sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) / 1e6
    print(f'Exported {out} ({size:.1f} MB) for {args.base}')


if __name__ == '__main__':
    main()
