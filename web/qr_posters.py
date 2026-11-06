"""Make one printable A4 QR poster per entrance (PNG each, plus one PDF with them all), in the website's design
(docs/website/design-brief.md). The QR code opens the website at that entrance. The robot's own map is printed faintly
behind, with the entrance marked.

    python web/qr_posters.py --database web/data/sample/api/merz.sqlite --base-url https://<user>.github.io/merz-mapper --out posters
    python web/qr_posters.py ... --theme light      # "blueprint on paper", uses far less ink

The base URL must be one that visitors' phones can reach: scan a printed poster before relying on it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Optional
from urllib.parse import urlencode

WEB = Path(__file__).resolve().parent
THEMES = {
    'dark': {'bg': '#05080f', 'panel': '#0a101c', 'ink': '#eef1f6', 'ink2': '#9aa6b8', 'line': '#1c2840',
             'accent': '#ffb547', 'map_floor': '#101a2e', 'map_wall': '#3a4d70'},
    'light': {'bg': '#f3f0e6', 'panel': '#fbfaf5', 'ink': '#13233a', 'ink2': '#4a5a72', 'line': '#d7d2c2',
              'accent': '#b4610a', 'map_floor': '#ebe6d8', 'map_wall': '#9fb0cf'},
}


def entrance_url(base_url: str, entrance_id: str) -> str:
    return f"{base_url.rstrip('/')}/?{urlencode({'entrance': entrance_id})}"


def _site_font(pattern: str) -> Optional[Path]:
    """The website's own (self-hosted, OFL) fonts, as built into web/dist. Needs a Pillow with WOFF2 support."""
    found = sorted((WEB / 'dist' / 'assets').glob(pattern))
    return found[0] if found else None


FALLBACK_BOLD = ['arialbd.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf']
FALLBACK_REGULAR = ['arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']
FALLBACK_MONO = ['consola.ttf', 'DejaVuSansMono.ttf', 'LiberationMono-Regular.ttf']


def font(size: int, kind: str = 'ui', weight: int = 500, width: int = 100):
    """kind: 'display' (Archivo, expanded), 'ui' (Geist) or 'mono' (Geist Mono), falling back to system fonts."""
    from PIL import ImageFont

    pattern = {'display': 'archivo-latin-standard-normal-*.woff2', 'ui': 'geist-latin-wght-normal-*.woff2',
               'mono': 'geist-mono-latin-wght-normal-*.woff2'}[kind]
    path = _site_font(pattern)
    if path:
        try:
            f = ImageFont.truetype(str(path), size)
            axes = f.get_variation_axes()
            f.set_variation_by_axes([weight, width][:len(axes)])
            return f
        except (OSError, ValueError):
            pass
    names = FALLBACK_MONO if kind == 'mono' else FALLBACK_BOLD if weight >= 600 else FALLBACK_REGULAR
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def draw_mark(draw, x: int, y: int, size: int, c: dict) -> None:
    """The Merz Mapper mark (web/frontend/src/ui/icons.ts): a ring, a scan arc and the robot's chevron."""
    k = size / 32
    draw.ellipse([x + 1.5 * k, y + 1.5 * k, x + 30.5 * k, y + 30.5 * k], outline=c['line'], width=max(2, round(1.4 * k)))
    draw.arc([x + 1.5 * k, y + 1.5 * k, x + 30.5 * k, y + 30.5 * k], 270, 360, fill=c['accent'], width=max(3, round(2 * k)))
    draw.polygon([(x + 11 * k, y + 21.5 * k), (x + 16 * k, y + 9.5 * k), (x + 21 * k, y + 21.5 * k), (x + 16 * k, y + 18.3 * k)],
                 fill=c['accent'])


def map_backdrop(width: int, height: int, entrance_id: str, c: dict):
    """The robot's map from the current data bundle, recoloured, with the entrance's position. None if no bundle."""
    from PIL import Image

    try:
        index = json.loads((WEB / 'data' / 'index.json').read_text())
        bundle = WEB / 'data' / index['default']
        manifest = json.loads((bundle / 'manifest.json').read_text())
        graph = json.loads((bundle / 'graph.json').read_text())
    except (OSError, ValueError, KeyError):
        return None
    m = manifest['map']
    level = next((lv for lv in m['levels'] if lv['factor'] == 2), m['levels'][0])
    state = Image.open(bundle / level['file']).convert('L')
    lut_r, lut_g, lut_b, lut_a = [], [], [], []
    for v in range(256):
        colour = c['map_wall'] if v > 190 else c['map_floor'] if v > 60 else None
        rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5)) if colour else (0, 0, 0)
        lut_r.append(rgb[0]); lut_g.append(rgb[1]); lut_b.append(rgb[2]); lut_a.append(255 if colour else 0)
    art = Image.merge('RGBA', [state.point(lut) for lut in (lut_r, lut_g, lut_b, lut_a)])
    scale = min(width / art.width, height / art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.NEAREST)
    entrance = next((e for e in graph['entrances'] if e['id'] == entrance_id), None)
    pos = None
    if entrance:
        res = m['resolution'] * level['factor'] / scale
        pos = ((entrance['x'] - m['origin'][0]) / res, art.height - (entrance['y'] - m['origin'][1]) / res)
    return art, pos


def make_poster(url: str, entrance_name: str, path: Path, entrance_id: str = '', theme: str = 'dark') -> None:
    """A4 portrait at 150 dpi. High error correction: posters get scratched and are scanned at an angle."""
    import qrcode
    from PIL import Image, ImageDraw

    c = THEMES[theme]
    W, H, M = 1240, 1754, 96
    poster = Image.new('RGB', (W, H), c['bg'])
    # The robot's map in its own band, with the entrance ringed: "this is where you are".
    band = (640, 1060)
    backdrop = map_backdrop(W - 2 * M, band[1] - band[0], entrance_id, c)
    if backdrop:
        art, pos = backdrop
        ox, oy = (W - art.width) // 2, band[0] + (band[1] - band[0] - art.height) // 2
        poster.paste(art, (ox, oy), art)
        if pos:
            px, py = ox + pos[0], oy + pos[1]
            d = ImageDraw.Draw(poster)
            for r, a in ((54, 2), (34, 3)):
                d.ellipse([px - r, py - r, px + r, py + r], outline=c['accent'], width=a)
            d.ellipse([px - 13, py - 13, px + 13, py + 13], fill=c['accent'])
    draw = ImageDraw.Draw(poster)
    # Header: mark and name.
    draw_mark(draw, M, 92, 64, c)
    draw.text((M + 86, 124), 'Merz Mapper', fill=c['ink'], anchor='lm', font=font(40, 'display', 750, 120))
    draw.text((W - M, 124), 'EEE3094 · student project', fill=c['ink2'], anchor='rm', font=font(22, 'mono', 500))
    # You are here.
    draw.text((M, 252), f'YOU ARE HERE · {entrance_name.upper()}', fill=c['accent'], anchor='lm', font=font(26, 'mono', 500))
    big = font(150, 'display', 800, 125)
    draw.text((M - 6, 300), 'Find your', fill=c['ink'], anchor='la', font=big)
    draw.text((M - 6, 450), 'room.', fill=c['accent'], anchor='la', font=big)
    # QR code on a light card, always dark on light so every phone can read it.
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    code.add_data(url)
    code.make(fit=True)
    qr = code.make_image(fill_color='black', back_color='white').get_image().convert('RGB')
    size = 430
    qr = qr.resize((size, size), Image.NEAREST)
    qx, qy = W - M - size - 30, 1110
    draw.rounded_rectangle([qx - 30, qy - 30, qx + size + 30, qy + size + 30], radius=30, fill='#ffffff')
    poster.paste(qr, (qx, qy))
    for cx, cy, dx, dy in [(qx - 48, qy - 48, 1, 1), (qx + size + 48, qy - 48, -1, 1), (qx - 48, qy + size + 48, 1, -1),
                           (qx + size + 48, qy + size + 48, -1, -1)]:
        draw.line([(cx, cy + dy * 44), (cx, cy), (cx + dx * 44, cy)], fill=c['accent'], width=7, joint='curve')
    # Three steps, as telemetry.
    steps = [('01', 'Scan', 'with your phone camera'), ('02', 'Choose', 'your room'), ('03', 'Follow', 'the robot’s photos')]
    for i, (n, title, text) in enumerate(steps):
        y = 1110 + i * 150
        draw.text((M, y), n, fill=c['accent'], anchor='la', font=font(26, 'mono', 500))
        draw.text((M, y + 36), title, fill=c['ink'], anchor='la', font=font(52, 'display', 750, 115))
        draw.text((M, y + 100), text, fill=c['ink2'], anchor='la', font=font(28, 'ui', 450))
    # Footer.
    draw.line([(M, H - 150), (W - M, H - 150)], fill=c['line'], width=2)
    draw.text((M, H - 104), url, fill=c['ink'], anchor='la', font=font(24, 'mono', 500))
    draw.text((M, H - 66), 'Directions from a map built by an autonomous rover. Every room offered can be reached from here.',
              fill=c['ink2'], anchor='la', font=font(22, 'ui', 400))
    path.parent.mkdir(parents=True, exist_ok=True)
    poster.save(path)


def make_pdf(pngs: list[Path], path: Path) -> Path:
    """Put the posters in one A4 PDF, one entrance per page, ready to print at 100 % scale."""
    from PIL import Image

    pages = [Image.open(png).convert('RGB') for png in pngs]
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(path, 'PDF', resolution=150.0, save_all=True, append_images=pages[1:])
    return path


def make_all(database: str | Path, base_url: str, out: Path, theme: str = 'dark') -> list[Path]:
    connection = sqlite3.connect(f'file:{Path(database).as_posix()}?mode=ro', uri=True)
    try:
        rows = connection.execute('SELECT id, name FROM entrances ORDER BY id').fetchall()
    finally:
        connection.close()
    paths = []
    for entrance_id, name in rows:
        path = out / f'poster_{entrance_id}.png'
        make_poster(entrance_url(base_url, entrance_id), name, path, entrance_id, theme)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--database', required=True)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--out', type=Path, default=Path('posters'))
    parser.add_argument('--theme', choices=sorted(THEMES), default='dark')
    args = parser.parse_args()
    paths = make_all(args.database, args.base_url, args.out, args.theme)
    for path in paths:
        print(f'Wrote {path}')
    if paths:
        print(f'Wrote {make_pdf(paths, args.out / "posters.pdf")} (print at 100 % scale on A4)')


if __name__ == '__main__':
    main()
