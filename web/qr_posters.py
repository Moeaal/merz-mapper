"""Make one printable A4 QR poster per entrance. The QR code opens the website at that entrance.

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


def make_poster(url: str, entrance_name: str, path: Path) -> None:
    """Draw an A4 portrait poster at 150 dpi. High error correction, as posters get scratched and viewed at an angle."""
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1240, 1754
    poster = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(poster)
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(fill_color='black', back_color='white').get_image().convert('RGB')
    size = 900
    image = image.resize((size, size), Image.NEAREST)   # keeps the module edges sharp
    poster.paste(image, ((width - size) // 2, 400))

    draw.text((width / 2, 170), 'Find your room', fill='black', anchor='mm', font=ImageFont.load_default(size=90))
    draw.text((width / 2, 290), f'You are at: {entrance_name}', fill='#333333', anchor='mm',
              font=ImageFont.load_default(size=50))
    draw.text((width / 2, 1400), 'Scan with your phone camera', fill='black', anchor='mm',
              font=ImageFont.load_default(size=56))
    draw.text((width / 2, 1490), 'for photo directions to your room.', fill='#333333', anchor='mm',
              font=ImageFont.load_default(size=44))
    draw.text((width / 2, 1680), url, fill='#555555', anchor='mm', font=ImageFont.load_default(size=26))
    path.parent.mkdir(parents=True, exist_ok=True)
    poster.save(path)


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
    for path in make_all(args.database, args.base_url, args.out):
        print(f'Wrote {path}')


if __name__ == '__main__':
    main()
