// Small hand-made SVG charts (dataviz method): one accent for the measured series, neutral ink for the target,
// status colours only for pass/fail and always with an icon and a word. Every mark has a hover/focus tooltip, and
// every chart has a table next to it.
import { h } from './dom';
import { drawLines, gsap } from './motion';

const NS = 'http://www.w3.org/2000/svg';
function s<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, text?: string) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text !== undefined) el.textContent = text;
  return el;
}

let tip: HTMLElement | null = null;
function tooltip() {
  if (!tip) { tip = h('div', { class: 'chart-tip', role: 'tooltip' }); document.body.append(tip); }
  return tip;
}
function bindTip(mark: SVGElement, text: string) {
  mark.setAttribute('tabindex', '0');
  mark.setAttribute('aria-label', text);
  mark.classList.add('mark');
  const show = (x: number, y: number) => {
    const t = tooltip();
    t.textContent = text;
    t.style.transform = `translate(${Math.round(x + 14)}px, ${Math.round(y - 12)}px)`;
    t.classList.add('on');
  };
  mark.addEventListener('pointermove', (e) => show(e.clientX, e.clientY));
  mark.addEventListener('pointerleave', () => tooltip().classList.remove('on'));
  mark.addEventListener('focus', () => { const r = mark.getBoundingClientRect(); show(r.right, r.top); });
  mark.addEventListener('blur', () => tooltip().classList.remove('on'));
}

function frame(width: number, height: number, label: string) {
  const svg = s('svg', { viewBox: `0 0 ${width} ${height}`, class: 'chart', role: 'group', 'aria-label': label });
  return svg;
}

/** A horizontal meter against a target, for percentages. */
export function meter(value: number, target: number, max: number, unit: string, passed: boolean | null, label: string) {
  const W = 520, H = 76, x0 = 0, x1 = W, y = 30;
  const svg = frame(W, H, label);
  const sx = (v: number) => x0 + ((x1 - x0) * Math.max(0, Math.min(max, v))) / max;
  svg.append(s('rect', { x: x0, y, width: x1 - x0, height: 10, rx: 5, class: 'track' }));
  const bar = s('rect', { x: x0, y, width: 0, height: 10, rx: 5, class: `bar ${passed === false ? 'is-fail' : ''}` });
  svg.append(bar);
  gsap.to(bar, { attr: { width: sx(value) - x0 }, duration: 1.6, ease: 'expo.out', delay: 0.2 });
  bindTip(bar, `Measured ${value.toFixed(1)}${unit}`);
  svg.append(s('line', { x1: sx(target), x2: sx(target), y1: y - 12, y2: y + 22, class: 'target' }),
    s('text', { x: sx(target), y: y - 16, class: 'tick-label', 'text-anchor': 'middle' }, `target ${target}${unit}`),
    s('text', { x: x0, y: y + 36, class: 'axis-label' }, `0${unit}`),
    s('text', { x: x1, y: y + 36, class: 'axis-label', 'text-anchor': 'end' }, `${max}${unit}`));
  return svg;
}

/** Histogram of errors with the target line. */
export function histogram(bins: number[], range: [number, number], target: number, label: string) {
  const W = 520, H = 200, L = 34, B = 30, T = 18;
  const svg = frame(W, H, label);
  const maxCount = Math.max(...bins, 1);
  const bw = (W - L) / bins.length;
  const total = bins.reduce((a, b) => a + b, 0);
  svg.append(s('line', { x1: L, x2: W, y1: H - B, y2: H - B, class: 'axis' }));
  bins.forEach((count, i) => {
    const hgt = ((H - B - T) * count) / maxCount;
    const a = range[0] + ((range[1] - range[0]) * i) / bins.length;
    const b = a + (range[1] - range[0]) / bins.length;
    const rect = s('rect', { x: L + i * bw + 1, y: H - B, width: Math.max(1, bw - 2), height: 0, rx: 2,
      class: `bar ${a >= target ? 'is-muted' : ''}` });
    svg.append(rect);
    gsap.to(rect, { attr: { y: H - B - hgt, height: hgt }, duration: 1.1, delay: 0.1 + i * 0.025, ease: 'expo.out' });
    bindTip(rect, `${(a * 100).toFixed(0)}–${(b * 100).toFixed(0)} cm: ${count} cells (${((100 * count) / Math.max(1, total)).toFixed(1)}%)`);
  });
  const tx = L + ((W - L) * (target - range[0])) / (range[1] - range[0]);
  svg.append(s('line', { x1: tx, x2: tx, y1: T - 6, y2: H - B + 4, class: 'target' }),
    s('text', { x: tx + 6, y: T, class: 'tick-label' }, `target ${target * 100} cm`));
  for (const v of [range[0], (range[0] + range[1]) / 2, range[1]]) {
    const x = L + ((W - L) * (v - range[0])) / (range[1] - range[0]);
    svg.append(s('text', { x, y: H - 8, class: 'axis-label', 'text-anchor': 'middle' }, `${Math.round(v * 100)} cm`));
  }
  svg.append(s('text', { x: 0, y: T, class: 'axis-label' }, 'cells'));
  return svg;
}

/** Every sample as a dot on one axis, with the mean and the target. Optional log scale. */
export function dotStrip(samples: number[], target: number, unit: string, label: string,
  opts: { log?: boolean; max?: number; format?: (v: number) => string; names?: string[] } = {}) {
  const W = 520, H = 150, L = 8, R = 12, mid = 66;
  const svg = frame(W, H, label);
  const fmtv = opts.format ?? ((v: number) => v.toFixed(2));
  const max = opts.max ?? Math.max(target * 1.4, ...samples) * 1.05;
  const min = opts.log ? Math.max(0.1, Math.min(...samples) / 2) : 0;
  const sx = (v: number) => opts.log
    ? L + ((W - L - R) * (Math.log10(Math.max(v, min)) - Math.log10(min))) / (Math.log10(max) - Math.log10(min))
    : L + ((W - L - R) * v) / max;
  svg.append(s('line', { x1: L, x2: W - R, y1: mid + 30, y2: mid + 30, class: 'axis' }));
  const ticks = opts.log ? [1, 10, 100, 1000].filter((t) => t >= min && t <= max) : [0, max / 2, max].map((v) => +v.toPrecision(2));
  for (const t of ticks) svg.append(s('text', { x: sx(t), y: mid + 48, class: 'axis-label', 'text-anchor': 'middle' }, `${t}${unit}`));
  // Simple beeswarm: stack dots that would overlap.
  const placed: { x: number; y: number }[] = [];
  const order = samples.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v);
  for (const { v, i } of order) {
    const x = sx(v);
    let y = mid;
    for (let k = 0; k < 40; k++) {
      const off = (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 7;
      if (!placed.some((p) => Math.hypot(p.x - x, p.y - (mid + off)) < 7)) { y = mid + off; break; }
    }
    placed.push({ x, y });
    const dot = s('circle', { cx: x, cy: y, r: 0, class: `dot ${v > target ? 'is-over' : ''}` });
    svg.append(dot);
    gsap.to(dot, { attr: { r: 4 }, duration: 0.6, delay: 0.2 + placed.length * 0.012, ease: 'back.out(2)' });
    bindTip(dot, `${opts.names?.[i] ? opts.names[i] + ': ' : ''}${fmtv(v)}${unit}`);
  }
  const mean = samples.reduce((a, b) => a + b, 0) / Math.max(1, samples.length);
  svg.append(s('line', { x1: sx(mean), x2: sx(mean), y1: mid - 34, y2: mid + 30, class: 'mean' }),
    s('text', { x: sx(mean) + 5, y: mid - 38, class: 'tick-label accent' }, `mean ${fmtv(mean)}${unit}`));
  if (target <= max) {
    svg.append(s('line', { x1: sx(target), x2: sx(target), y1: 8, y2: mid + 30, class: 'target' }),
      s('text', { x: sx(target) - 5, y: 14, class: 'tick-label', 'text-anchor': 'end' }, `target ${fmtv(target)}${unit}`));
  }
  return svg;
}

/** Pass/fail squares, one per item (O7 routes). */
export function squares(items: { label: string; ok: boolean | null }[], label: string) {
  const size = 40, gap = 8;
  const W = items.length * (size + gap);
  const svg = frame(Math.max(W, 10), size + 26, label);
  items.forEach((it, i) => {
    const g = s('g', { class: `square ${it.ok ? 'is-pass' : it.ok === false ? 'is-fail' : 'is-na'}` });
    const r = s('rect', { x: i * (size + gap), y: 0, width: size, height: size, rx: 8 });
    const t = s('text', { x: i * (size + gap) + size / 2, y: size / 2 + 5, 'text-anchor': 'middle' }, it.ok ? '✓' : it.ok === false ? '✕' : '–');
    g.append(r, t);
    svg.append(g);
    gsap.from(g, { opacity: 0, y: 8, duration: 0.5, delay: 0.1 + i * 0.05 });
    bindTip(r, `${it.label}: ${it.ok ? 'correct' : it.ok === false ? 'wrong' : 'not judged'}`);
  });
  return svg;
}

/** Paired slope chart: single sighting on the left, fused on the right, one line per landmark. */
export function slope(pairs: { id: number; single_m: number; fused_m: number }[], label: string) {
  const W = 520, H = 230, L = 120, R = 400, T = 24, B = 26;
  const svg = frame(W, H, label);
  const max = Math.max(...pairs.flatMap((p) => [p.single_m, p.fused_m]), 0.1) * 1.08;
  const sy = (v: number) => T + (H - T - B) * (1 - v / max);
  svg.append(s('line', { x1: L, x2: L, y1: T, y2: H - B, class: 'axis' }), s('line', { x1: R, x2: R, y1: T, y2: H - B, class: 'axis' }),
    s('text', { x: L, y: H - 6, 'text-anchor': 'middle', class: 'axis-label' }, 'one sighting'),
    s('text', { x: R, y: H - 6, 'text-anchor': 'middle', class: 'axis-label' }, 'fused'),
    s('text', { x: L - 10, y: sy(max * 0.95), 'text-anchor': 'end', class: 'axis-label' }, `${(max * 0.95 * 100).toFixed(0)} cm`),
    s('text', { x: L - 10, y: sy(0), 'text-anchor': 'end', class: 'axis-label' }, '0 cm'));
  const lines: SVGGeometryElement[] = [];
  for (const p of pairs) {
    const better = p.fused_m < p.single_m;
    const line = s('line', { x1: L, y1: sy(p.single_m), x2: R, y2: sy(p.fused_m), class: `slope ${better ? '' : 'is-worse'}` });
    svg.append(line);
    lines.push(line);
    bindTip(line, `Landmark ${p.id}: ${(p.single_m * 100).toFixed(0)} cm → ${(p.fused_m * 100).toFixed(0)} cm`);
  }
  const ms = pairs.reduce((a, p) => a + p.single_m, 0) / pairs.length;
  const mf = pairs.reduce((a, p) => a + p.fused_m, 0) / pairs.length;
  const meanLine = s('line', { x1: L, y1: sy(ms), x2: R, y2: sy(mf), class: 'slope-mean' });
  svg.append(meanLine, s('text', { x: R + 10, y: sy(mf) + 4, class: 'tick-label accent' }, `mean ${(mf * 100).toFixed(0)} cm`),
    s('text', { x: L - 10, y: sy(ms) + 4, class: 'tick-label accent', 'text-anchor': 'end' }, `mean ${(ms * 100).toFixed(0)} cm`));
  drawLines([...lines, meanLine], 1.4, 0.2);
  return svg;
}

export function dataTable(caption: string, headers: string[], rows: (string | number)[][]) {
  return h('details', { class: 'data-table' }, h('summary', {}, 'Show the data'),
    h('table', {}, h('caption', { class: 'sr-only', text: caption }),
      h('thead', {}, h('tr', {}, ...headers.map((x) => h('th', { scope: 'col', text: x })))),
      h('tbody', {}, ...rows.map((r) => h('tr', {}, ...r.map((c) => h('td', { text: String(c) })))))));
}
