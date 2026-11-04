"""Make one printable A4 QR poster per entrance (PNG each, plus one PDF with them all), in the website's design.
The QR code opens the website at that entrance.

    python web/qr_posters.py --database web/sample_data/merz_sample.sqlite \
        --base-url http://192.168.0.10:8000 --out posters/

The base URL must be one that visitors' phones can reach: check this before printing.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
from urllib.parse import urlencode


def entrance_url(base_url: str, entrance_id: str) -> str:
    return f"{base_url.rstrip('/')}/?{urlencode({'entrance': entrance_id})}"


# Colours and fonts match the website (web/static/app.css), so the poster and the page read as one thing.
INK = '#13233a'
INK_2 = '#44536a'
SIGNAL = '#ffc629'
ROUTE = '#c2410c'
ENTRANCE = '#047857'
PAPER = '#f4f2ec'
LINE = '#d6d1c4'
# Atkinson Hyperlegible (the website's font) if installed, else common system fonts, else Pillow's built-in font.
BOLD_FONTS = ['AtkinsonHyperlegible-Bold.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf']
REGULAR_FONTS = ['AtkinsonHyperlegible-Regular.ttf', 'arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']


def font(size: int, bold: bool = False):
    from PIL import ImageFont

    for name in BOLD_FONTS if bold else REGULAR_FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def draw_mark(draw, x: int, y: int, size: int) -> None:
    """The Merz Mapper mark: a yellow tile with a route turning a corner (as web/static/icon.svg)."""
    k = size / 32
    draw.rounded_rectangle([x, y, x + size, y + size], radius=6 * k, fill=SIGNAL)
    points = [(x + 8 * k, y + 24 * k), (x + 8 * k, y + 14 * k), (x + 16 * k, y + 14 * k), (x + 16 * k, y + 8 * k),
              (x + 24 * k, y + 8 * k)]
    draw.line(points, fill=INK, width=round(3.2 * k), joint='curve')
    draw.ellipse([x + 5 * k, y + 21 * k, x + 11 * k, y + 27 * k], fill=INK)


def draw_door(draw, x: int, y: int, size: int) -> None:
    """The entrance glyph: a green tile with an arrow going in through a door."""
    k = size / 24
    draw.rounded_rectangle([x, y, x + size, y + size], radius=4 * k, fill=ENTRANCE)
    w = round(2.4 * k)
    draw.line([(x + 13 * k, y + 5 * k), (x + 19 * k, y + 5 * k), (x + 19 * k, y + 19 * k), (x + 13 * k, y + 19 * k)],
              fill='white', width=w, joint='curve')
    draw.line([(x + 5 * k, y + 12 * k), (x + 14 * k, y + 12 * k)], fill='white', width=w)
    draw.line([(x + 10 * k, y + 8 * k), (x + 14 * k, y + 12 * k), (x + 10 * k, y + 16 * k)], fill='white', width=w,
              joint='curve')


def make_poster(url: str, entrance_name: str, path: Path) -> None:
    """Draw an A4 portrait poster at 150 dpi. High error correction, as posters get scratched and viewed at an angle."""
    import qrcode
    from PIL import Image, ImageDraw

    width, height = 1240, 1754
    margin = 90
    poster = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(poster)

    # Sign panel header with the yellow signal band, as on the website.
    draw.rectangle([0, 0, width, 250], fill=INK)
    draw.rectangle([0, 250, width, 266], fill=SIGNAL)
    draw_mark(draw, margin, 78, 96)
    draw.text((margin + 126, 104), 'Merz Mapper', fill='white', anchor='lm', font=font(66, bold=True))
    draw.text((margin + 128, 172), 'Photo directions inside Merz Court', fill='#d7dee8', anchor='lm', font=font(36))

    # "You are here" sign.
    draw.rounded_rectangle([margin, 320, width - margin, 500], radius=22, fill=PAPER, outline=LINE, width=3)
    draw_door(draw, margin + 36, 362, 96)
    draw.text((margin + 162, 380), 'YOU ARE HERE', fill=INK_2, anchor='lm', font=font(30, bold=True))
    draw.text((margin + 162, 446), entrance_name, fill=INK, anchor='lm', font=font(64, bold=True))

    draw.text((width / 2, 590), 'Find your room', fill=INK, anchor='mm', font=font(104, bold=True))

    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(fill_color='black', back_color='white').get_image().convert('RGB')
    size = 680
    image = image.resize((size, size), Image.NEAREST)   # keeps the module edges sharp
    top = 712
    left = (width - size) // 2
    draw.rounded_rectangle([left - 24, top - 24, left + size + 24, top + size + 24], radius=28, outline=INK, width=6)
    poster.paste(image, (left, top))
    # Route-coloured corner ticks, echoing the route line on the map.
    gap = 44
    for cx, cy, dx, dy in [(left - gap, top - gap, 1, 1), (left + size + gap, top - gap, -1, 1),
                           (left - gap, top + size + gap, 1, -1), (left + size + gap, top + size + gap, -1, -1)]:
        draw.line([(cx, cy + dy * 70), (cx, cy), (cx + dx * 70, cy)], fill=ROUTE, width=12, joint='curve')

    # Three numbered steps.
    steps = [('Scan', 'with your phone camera'), ('Choose', 'the room you need'), ('Follow', 'the junction photos')]
    column = (width - 2 * margin) / 3
    for index, (title, detail) in enumerate(steps):
        cx = margin + column * index + column / 2
        draw.ellipse([cx - 38, 1500 - 38, cx + 38, 1500 + 38], fill=ROUTE)
        draw.text((cx, 1500), str(index + 1), fill='white', anchor='mm', font=font(44, bold=True))
        draw.text((cx, 1576), title, fill=INK, anchor='mm', font=font(42, bold=True))
        draw.text((cx, 1620), detail, fill=INK_2, anchor='mm', font=font(28))

    draw.rectangle([0, height - 60, width, height], fill=INK)
    draw.text((margin, height - 30), url, fill='white', anchor='lm', font=font(24))
    draw.text((width - margin, height - 30), 'Student project demonstrator', fill='#d7dee8', anchor='rm', font=font(24))
    path.parent.mkdir(parents=True, exist_ok=True)
    poster.save(path)


def make_pdf(pngs: list[Path], path: Path) -> Path:
    """Put the posters in one A4 PDF, one entrance per page, ready to print at 100 % scale."""
    from PIL import Image

    pages = [Image.open(png).convert('RGB') for png in pngs]
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(path, 'PDF', resolution=150.0, save_all=True, append_images=pages[1:])
    return path


def make_all(database: str | Path, base_url: str, out: Path) -> list[Path]:
    connection = sqlite3.connect(f'file:{Path(database).as_posix()}?mode=ro', uri=True)
    try:
        rows = connection.execute('SELECT id, name FROM entrances ORDER BY id').fetchall()
    finally:
        connection.close()
    paths = []
    for entrance_id, name in rows:
        path = out / f'poster_{entrance_id}.png'
        make_poster(entrance_url(base_url, entrance_id), name, path)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--database', required=True)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--out', type=Path, default=Path('posters'))
    args = parser.parse_args()
    paths = make_all(args.database, args.base_url, args.out)
    for path in paths:
        print(f'Wrote {path}')
    if paths:
        print(f'Wrote {make_pdf(paths, args.out / "posters.pdf")} (print at 100 % scale on A4)')


if __name__ == '__main__':
    main()
