import type { Bundle } from '../data';

// The 2D map used when WebGL is unavailable (old devices, some locked-down browsers). Same data, simpler drawing:
// the occupancy grid on a canvas, the route as a line, and HTML pins. Drag to pan, wheel or buttons to zoom.
export class FlatMap {
  private canvas = document.createElement('canvas');
  private ctx = this.canvas.getContext('2d')!;
  private image: HTMLCanvasElement | null = null;
  private pinsLayer = document.createElement('div');
  private pins: { el: HTMLElement; x: number; y: number }[] = [];   // el is the positioned wrapper
  private route: [number, number][] | null = null;
  private view = { x: 0, y: 0, s: 8 };          // centre (m) and pixels per metre
  private observer: ResizeObserver;

  constructor(private host: HTMLElement, private bundle: Bundle) {
    this.canvas.className = 'flat-canvas';
    this.canvas.setAttribute('aria-hidden', 'true');
    this.pinsLayer.className = 'flat-pins';
    host.append(this.canvas, this.pinsLayer);
    const m = bundle.manifest.map;
    this.view.x = m.origin[0] + (m.width * m.resolution) / 2;
    this.view.y = m.origin[1] + (m.height * m.resolution) / 2;
    this.observer = new ResizeObserver(() => this.draw());
    this.observer.observe(host);
    this.loadImage();
    this.bindPointer();
  }

  private loadImage() {
    const m = this.bundle.manifest.map;
    const level = m.levels.find((l) => l.factor === 2) ?? m.levels[0];
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = img.width;
      c.height = img.height;
      const g = c.getContext('2d')!;
      g.drawImage(img, 0, 0);
      const data = g.getImageData(0, 0, c.width, c.height);
      const style = getComputedStyle(document.documentElement);
      const rgb = (name: string) => {
        const probe = document.createElement('span');
        probe.style.color = style.getPropertyValue(name);
        document.body.append(probe);
        const parts = getComputedStyle(probe).color.match(/\d+/g)!.map(Number);
        probe.remove();
        return parts;
      };
      const floor = rgb('--floor');
      const wall = rgb('--wall');
      for (let i = 0; i < data.data.length; i += 4) {
        const v = data.data[i];
        const colour = v > 190 ? wall : v > 60 ? floor : null;
        if (colour) { data.data[i] = colour[0]; data.data[i + 1] = colour[1]; data.data[i + 2] = colour[2]; data.data[i + 3] = 255; }
        else data.data[i + 3] = 0;
      }
      g.putImageData(data, 0, 0);
      this.image = c;
      this.draw();
    };
    img.src = this.bundle.url(level.file);
  }

  private bindPointer() {
    let last: { x: number; y: number } | null = null;
    this.host.addEventListener('pointerdown', (e) => {
      if ((e.target as HTMLElement).closest('button')) return;
      last = { x: e.clientX, y: e.clientY };
      this.host.setPointerCapture(e.pointerId);
    });
    this.host.addEventListener('pointermove', (e) => {
      if (!last) return;
      this.view.x -= (e.clientX - last.x) / this.view.s;
      this.view.y += (e.clientY - last.y) / this.view.s;
      last = { x: e.clientX, y: e.clientY };
      this.draw();
    });
    this.host.addEventListener('pointerup', () => { last = null; });
    this.host.addEventListener('wheel', (e) => { e.preventDefault(); this.zoom(Math.exp(-e.deltaY * 0.0015)); }, { passive: false });
  }

  zoom(f: number) { this.view.s = Math.max(1, Math.min(80, this.view.s * f)); this.draw(); }

  fit(points: [number, number][]) {
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const w = this.host.clientWidth;
    const hgt = this.host.clientHeight;
    this.view.x = (Math.min(...xs) + Math.max(...xs)) / 2;
    this.view.y = (Math.min(...ys) + Math.max(...ys)) / 2;
    this.view.s = Math.min(w / (Math.max(...xs) - Math.min(...xs) + 10), hgt / (Math.max(...ys) - Math.min(...ys) + 10));
    this.draw();
  }

  setRoute(points: [number, number][] | null) { this.route = points; this.draw(); }

  addPin(marker: HTMLElement, x: number, y: number) {
    const el = document.createElement('div');
    el.className = 'pin';
    el.append(marker);
    this.pinsLayer.append(el);
    this.pins.push({ el, x, y });
    this.draw();
  }

  clearPins(keep = 0) { this.pins.splice(keep).forEach((p) => p.el.remove()); }

  private toScreen(x: number, y: number) {
    return [(x - this.view.x) * this.view.s + this.host.clientWidth / 2, (this.view.y - y) * this.view.s + this.host.clientHeight / 2];
  }

  draw() {
    const w = this.host.clientWidth;
    const hgt = this.host.clientHeight;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = w * ratio;
    this.canvas.height = hgt * ratio;
    const g = this.ctx;
    g.setTransform(ratio, 0, 0, ratio, 0, 0);
    g.clearRect(0, 0, w, hgt);
    const m = this.bundle.manifest.map;
    if (this.image) {
      const [x0, y0] = this.toScreen(m.origin[0], m.origin[1] + m.height * m.resolution);
      g.imageSmoothingEnabled = this.view.s < 20;
      g.drawImage(this.image, x0, y0, m.width * m.resolution * this.view.s, m.height * m.resolution * this.view.s);
    }
    if (this.route) {
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
      g.strokeStyle = accent;
      g.lineWidth = 5;
      g.lineJoin = g.lineCap = 'round';
      g.shadowColor = accent;
      g.shadowBlur = 14;
      g.beginPath();
      this.route.forEach(([x, y], i) => { const [sx, sy] = this.toScreen(x, y); if (i) g.lineTo(sx, sy); else g.moveTo(sx, sy); });
      g.stroke();
      g.shadowBlur = 0;
    }
    for (const p of this.pins) {
      const [sx, sy] = this.toScreen(p.x, p.y);
      p.el.style.transform = `translate3d(${sx}px, ${sy}px, 0)`;
    }
  }

  destroy() { this.observer.disconnect(); this.canvas.remove(); this.pinsLayer.remove(); }
}
