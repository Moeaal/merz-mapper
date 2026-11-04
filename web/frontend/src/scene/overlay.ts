import type { MapScene } from './MapScene';

// HTML markers pinned to map positions. They stay crisp at any zoom and remain real, focusable buttons.
export interface Pin { el: HTMLElement; x: number; y: number; h?: number; hideOffscreen?: boolean }

export class Overlay {
  private pins = new Set<Pin>();
  private off: () => void;

  constructor(private root: HTMLElement, private scene: MapScene) {
    this.off = scene.onFrame(() => this.place());
  }

  add(el: HTMLElement, x: number, y: number, h = 0): Pin {
    const pin = { el, x, y, h };
    el.classList.add('pin');
    this.root.appendChild(el);
    this.pins.add(pin);
    this.scene.invalidate();
    return pin;
  }

  move(pin: Pin, x: number, y: number) { pin.x = x; pin.y = y; this.scene.invalidate(); }

  remove(pin: Pin) { pin.el.remove(); this.pins.delete(pin); }

  clear() { for (const pin of this.pins) pin.el.remove(); this.pins.clear(); }

  place() {
    for (const pin of this.pins) {
      const p = this.scene.project(pin.x, pin.y, pin.h ?? 0);
      if (!p || !p.visible) { pin.el.style.visibility = 'hidden'; continue; }
      pin.el.style.visibility = '';
      pin.el.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`;
    }
  }

  destroy() { this.clear(); this.off(); }
}
