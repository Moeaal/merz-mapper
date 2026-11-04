import type { MapScene } from './MapScene';

// HTML markers pinned to map positions. They stay crisp at any zoom and remain real, focusable buttons.
export interface Pin { el: HTMLElement; wrap: HTMLElement; x: number; y: number; h?: number }

export class Overlay {
  private pins = new Set<Pin>();
  private off: () => void;

  constructor(private root: HTMLElement, private scene: MapScene) {
    this.off = scene.onFrame(() => this.place());
  }

  add(el: HTMLElement, x: number, y: number, h = 0): Pin {
    // The wrapper is positioned; the marker inside is free to animate its own transform.
    const wrapper = document.createElement('div');
    wrapper.className = 'pin';
    wrapper.style.visibility = 'hidden';
    wrapper.append(el);
    const pin = { el, x, y, h, wrap: wrapper };
    this.root.appendChild(wrapper);
    this.pins.add(pin);
    this.scene.invalidate();
    return pin;
  }

  move(pin: Pin, x: number, y: number) { pin.x = x; pin.y = y; this.scene.invalidate(); }

  remove(pin: Pin) { pin.wrap.remove(); this.pins.delete(pin); }

  clear() { for (const pin of this.pins) pin.wrap.remove(); this.pins.clear(); }

  place() {
    for (const pin of this.pins) {
      const p = this.scene.project(pin.x, pin.y, pin.h ?? 0);
      if (!p || !p.visible) { pin.wrap.style.visibility = 'hidden'; continue; }
      pin.wrap.style.visibility = '';
      pin.wrap.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`;
    }
  }

  destroy() { this.clear(); this.off(); }
}
