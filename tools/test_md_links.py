"""Every relative link in every Markdown file must point at a file or folder that exists.

Run as a test (`python -m pytest tools/test_md_links.py`) or as a script (`python tools/test_md_links.py`), which prints
each broken link. Web links, e-mail links and same-page anchors are not checked. Links inside code blocks are ignored.
"""
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', 'build', 'install', 'log', '__pycache__', '.pytest_cache', '_site'}
LINK = re.compile(r'!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
FENCE = re.compile(r'^\s*(```|~~~)')
INLINE_CODE = re.compile(r'`[^`]*`')


def markdown_files() -> list[Path]:
    return sorted(p for p in REPO.rglob('*.md') if not SKIP_DIRS & set(p.relative_to(REPO).parts))


def relative_links(path: Path):
    in_fence = False
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK.findall(INLINE_CODE.sub('', line)):
            if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith('#'):
                continue
            yield number, target


def broken_links() -> list[str]:
    broken = []
    for path in markdown_files():
        for number, target in relative_links(path):
            clean = target.split('#')[0].split('?')[0]
            resolved = (REPO / clean.lstrip('/')) if clean.startswith('/') else (path.parent / clean)
            if not resolved.exists():
                broken.append(f'{path.relative_to(REPO).as_posix()}:{number}: {target}')
    return broken


def test_markdown_files_were_found():
    assert (REPO / 'README.md') in markdown_files()
    assert len(markdown_files()) > 20


def test_every_relative_markdown_link_resolves():
    assert broken_links() == []


if __name__ == '__main__':
    problems = broken_links()
    print('\n'.join(problems) or f'All relative links resolve ({len(markdown_files())} Markdown files).')
    sys.exit(1 if problems else 0)
