import { icons, type IconName } from './icons';

// Tiny DOM helpers. Text from the data bundle is only ever set with textContent.
type Attrs = Record<string, string | number | boolean | null | undefined | EventListener>;
type Child = Node | string | null | undefined | false;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Attrs = {}, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') el.className = String(value);
    else if (key === 'text') el.textContent = String(value);
    else if (key === 'icon') el.insertAdjacentHTML('afterbegin', icons[value as IconName]);
    else if (key === 'style') el.setAttribute('style', String(value));
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value as EventListener);
    else el.setAttribute(key, value === true ? '' : String(value));
  }
  for (const child of children) if (child !== null && child !== undefined && child !== false) el.append(child);
  return el;
}

export function icon(name: IconName, cls = 'icon'): HTMLElement {
  const span = document.createElement('span');
  span.className = cls;
  span.insertAdjacentHTML('afterbegin', icons[name]);
  return span;
}

const announcer = () => document.getElementById('announcer')!;
let announceTimer = 0;
export function announce(text: string) {
  const el = announcer();
  clearTimeout(announceTimer);
  el.textContent = '';
  announceTimer = window.setTimeout(() => { el.textContent = text; }, 60);
}

export const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export function fmt(value: number | null | undefined, digits = 0, unit = ''): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits }) + unit;
}

export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}
