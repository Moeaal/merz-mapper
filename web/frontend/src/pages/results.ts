import type { PageContext } from '../main';
import type { Landmark, MetricPart, Objective } from '../data';
import { h, icon, fmt } from '../ui/dom';
import { CLASS_NAMES, landmarkIcon } from '../ui/icons';
import { countUp, gsap, reveal, revealOnScroll, ScrollTrigger } from '../ui/motion';
import { dataTable, dotStrip, histogram, meter, slope, squares } from '../ui/charts';

const MEANING: Record<string, (o: Objective) => string> = {
  O2: () => 'How much of the chosen corridor the robot mapped by itself, and how close its walls are to the real ones.',
  O3: () => 'Out of every door sign in the test area, how many numbers the robot read correctly.',
  O4: () => 'How far, on average, each landmark on the robot’s map is from where it really is.',
  O5: () => 'Whether the rooms the robot thinks each entrance can reach match a survey done on foot.',
  O6: () => 'How long the website takes to work out a route. A visitor should never wait.',
  O7: () => 'Whether the routes match the ones walked by hand, junction for junction.',
  O8: () => 'Whether combining many sightings of a landmark places it better than a single sighting does.',
};
const TARGET_TEXT: Record<string, string> = {
  O2: '≥ 90% coverage, walls within 0.15 m', O3: '≥ 85% of signs read', O4: 'mean error ≤ 0.5 m',
  O5: 'every entrance–room pair matches', O6: 'every query under 1 s', O7: '≥ 9 of 10 routes correct',
  O8: 'improvement above zero, 95% CI excluding zero',
};

function status(o: Objective) {
  const map = {
    pass: ['check', 'Target met'], fail: ['cross', 'Target missed'], not_measured: ['dash', 'Not yet measured'],
    inconclusive: ['info', 'Inconclusive'],
  } as const;
  const [ic, word] = map[o.status];
  return h('span', { class: `status is-${o.status}` }, h('span', { class: 'status-icon', icon: ic }), word);
}

function figureValue(part: MetricPart) {
  const n = h('span', { class: 'figure-num mono', text: '—' });
  const digits = part.unit === '%' ? 1 : part.unit === 'm' ? 2 : part.unit === 'ms' ? 0 : 0;
  const value = part.unit === 'm' && Math.abs(part.value) < 1 ? part.value * 100 : part.value;
  const unit = part.unit === 'm' && Math.abs(part.value) < 1 ? 'cm' : part.unit;
  const el = h('div', { class: 'figure' }, n, h('span', { class: 'figure-unit', text: unit }));
  return { el, run: () => countUp(n, value, unit === 'cm' ? 1 : digits, '', 0.1) };
}

function chartFor(key: string, part: MetricPart, bundle: PageContext['bundle']) {
  const d = part.detail ?? {};
  switch (key) {
    case 'O2':
      if (part.histogram) return [histogram(part.histogram.bins, part.histogram.range_m, part.target, 'Wall error per occupied cell'),
        dataTable('Wall error histogram', ['From (cm)', 'To (cm)', 'Cells'], part.histogram.bins.map((c, i) => {
          const w = (part.histogram!.range_m[1] - part.histogram!.range_m[0]) / part.histogram!.bins.length;
          return [Math.round(i * w * 100), Math.round((i + 1) * w * 100), c];
        }))];
      return [meter(part.value, part.target, 100, '%', part.passed, 'Corridor coverage'),
        dataTable('Coverage', ['Corridor area (m²)', 'Mapped free area (m²)', 'Coverage'], [[fmt(d.polygon_m2, 1), fmt(d.free_m2, 1), fmt(part.value, 1) + '%']])];
    case 'O3':
      return [meter(part.value, part.target, 100, '%', part.passed, 'Signs read correctly'),
        h('div', { class: 'chips' },
          ...(d.missed as string[]).map((t) => h('span', { class: 'chip is-missed', title: 'Sign not read' }, icon('dash'), t)),
          ...(d.false_reads as string[]).map((t) => h('span', { class: 'chip is-false', title: 'Wrong reading' }, icon('cross'), t))),
        h('p', { class: 'small muted', text: `${(d.correct as string[]).length} of ${d.signs} read correctly. Dashed chips were missed; crossed chips are wrong readings, which could send a visitor astray, so each one is examined.` })];
    case 'O4': {
      const names = (d.matches as any[]).map((m) => `${CLASS_NAMES[m.class] ?? m.class}${m.text ? ' ' + m.text : ''}`);
      return [dotStrip(part.samples ?? [], part.target, ' m', 'Error of every matched landmark', { names, format: (v) => v.toFixed(2) }),
        dataTable('Landmark errors', ['Landmark', 'Sightings', 'Error (m)'], (d.matches as any[]).map((m, i) => [names[i], m.observations, m.error_m.toFixed(3)])),
        h('p', { class: 'small muted', text: `${d.unmatched} truth landmarks had no match within the gate; they are reported, not counted as zero.` })];
    }
    case 'O5': {
      const extra = d.only_in_map as [string, string][];
      const missing = d.only_in_survey as [string, string][];
      return [meter(part.value, 100, 100, '%', part.passed, 'Agreement with the survey'),
        h('div', { class: 'mismatch' },
          h('div', {}, h('p', { class: 'eyebrow', text: `Only in the map · ${extra.length}` }), h('p', { class: 'small muted', text: 'Would send a visitor to a locked door: the serious kind.' }),
            ...extra.map(([e, r]) => h('span', { class: 'chip is-false' }, `${e} → ${r}`))),
          h('div', {}, h('p', { class: 'eyebrow', text: `Only in the survey · ${missing.length}` }), h('p', { class: 'small muted', text: 'Reachable on foot but not offered; here caused by unread or misread signs.' }),
            ...missing.map(([e, r]) => h('span', { class: 'chip is-missed' }, `${e} → ${r}`))))];
    }
    case 'O6':
      return [dotStrip(part.samples ?? [], part.target, ' ms', 'Every route query time', { log: true, max: 2000, format: (v) => v.toFixed(1) }),
        h('p', { class: 'small muted', text: `${(part.samples ?? []).length} queries, log scale. Measured over ${d.measured_over ?? 'the network'}; phone networks and photo downloads add to this and are reported separately.` })];
    case 'O7': {
      const routes = d.routes as any[];
      return [squares(routes.map((r) => ({ label: `${r.entrance} → ${r.room}`, ok: r.correct })), 'Each judged route'),
        dataTable('Routes', ['Entrance', 'Room', 'Expected', 'Website', 'Correct'], routes.map((r) => [r.entrance, r.room, r.expected.join(' '), r.actual.join(' '), r.correct ? 'yes' : r.correct === false ? 'no' : '–']))];
    }
    case 'O8': {
      const pairs = d.pairs as { landmark_id: number; single_m: number; fused_m: number }[];
      return [slope(pairs.map((p) => ({ id: p.landmark_id, single_m: p.single_m, fused_m: p.fused_m })), 'Error with one sighting and with all sightings fused'),
        h('p', { class: 'small muted', text: `Fusing was better for ${d.fused_better} of ${pairs.length} landmarks. Mean improvement ${fmt((part.stats?.mean ?? 0) * 100, 1)} cm, 95% CI ±${fmt((part.stats?.ci95 ?? 0) * 100, 1)} cm.` }),
        fusionCompare(bundle)];
    }
  }
  return [];
}

export default async function results(ctx: PageContext) {
  const { bundle, root } = ctx;
  const objectives = bundle.metrics.objectives;
  const keys = Object.keys(objectives);
  const counts = { pass: 0, fail: 0, not_measured: 0, inconclusive: 0 };
  keys.forEach((k) => counts[objectives[k].status]++);

  const intro = h('section', { class: 'results-hero' },
    h('p', { class: 'eyebrow accent', text: 'Results · objectives O2–O8' }),
    h('h1', { class: 'display', text: 'The evidence.' }),
    h('p', { class: 'lede', text: 'Each objective from the project plan, measured with the evaluation scripts in tools/eval and read straight from their output. Nothing here is typed in by hand.' }),
    h('div', { class: 'tally' },
      ...(['pass', 'fail', 'inconclusive', 'not_measured'] as const).filter((k) => counts[k]).map((k) =>
        h('span', { class: `status is-${k}` }, h('span', { class: 'status-icon', icon: ({ pass: 'check', fail: 'cross', not_measured: 'dash', inconclusive: 'info' } as const)[k] }),
          `${counts[k]} ${({ pass: 'met', fail: 'missed', not_measured: 'not yet measured', inconclusive: 'inconclusive' })[k]}`))),
    bundle.manifest.sample ? h('div', { class: 'gentle sample-warning' }, h('span', { class: 'gentle-icon', icon: 'info' }),
      h('div', {}, h('p', { class: 'gentle-title', text: 'These are not results of the robot' }),
        h('p', { class: 'small muted', text: 'They come from the synthetic sample run, scored by the real evaluation scripts, to show how results will appear. Real numbers replace them when a rover run is imported.' }))) : null,
    h('nav', { class: 'objective-index', 'aria-label': 'Objectives' }, ...keys.map((k) =>
      h('a', { href: `#${k}`, class: `oi is-${objectives[k].status}` }, h('span', { class: 'mono', text: k }), objectives[k].title))));
  root.append(intro);
  reveal(intro.children, 0.05, 0.07);

  for (const key of keys) {
    const o = objectives[key];
    const section = h('section', { class: `objective is-${o.status}`, id: key, 'aria-labelledby': `${key}-title` });
    const head = h('header', { class: 'objective-head' },
      h('p', { class: 'objective-key mono', text: key }),
      h('h2', { id: `${key}-title`, class: 'display-s', text: o.title }),
      status(o));
    section.append(head);
    if (!o.parts.length) {
      section.append(h('div', { class: 'not-measured glass', 'data-reveal': true },
        h('div', { class: 'nm-visual', 'aria-hidden': 'true' }, h('span'), h('span'), h('span')),
        h('div', {}, h('p', { class: 'nm-title', text: 'Not yet measured' }),
          h('p', { class: 'muted', text: `Target: ${TARGET_TEXT[key]}. This appears when ${key} has been run on real data with tools/eval and the run is imported.` }))));
    }
    for (const part of o.parts) {
      const fig = figureValue(part);
      const block = h('div', { class: 'part glass', 'data-reveal': true },
        h('div', { class: 'part-figure' },
          h('p', { class: 'eyebrow', text: part.label }), fig.el,
          h('p', { class: 'target-line mono' }, `target ${part.comparator} ${part.unit === 'm' && part.target < 1 ? fmt(part.target * 100) + ' cm' : fmt(part.target) + ' ' + part.unit}`),
          part.plot ? h('a', { class: 'plot-link small', href: bundle.url(part.plot), target: '_blank', rel: 'noopener' }, 'Report figure (PNG)', icon('external')) : null),
        h('div', { class: 'part-chart' }, ...chartFor(key, part, bundle)));
      section.append(block);
      ScrollTrigger.create({ trigger: block, start: 'top 80%', once: true, onEnter: fig.run });
    }
    section.append(h('p', { class: 'meaning', 'data-reveal': true }, h('span', { class: 'eyebrow', text: 'In plain words' }), MEANING[key](o)),
      o.sources.length ? h('p', { class: 'source mono small muted', text: `Source: tools/eval/${o.sources.map((x) => x + '.py').join(', ')} · ${TARGET_TEXT[key]}` }) : '');
    root.append(section);
  }

  root.append(gallery(ctx));
  root.append(h('footer', { class: 'site-footer' }, h('p', { class: 'small muted', text: 'Procedures and pass rules: docs/EXPERIMENTS.md. An objective is only called TESTED once its result is logged in docs/logbook.' })));
  revealOnScroll(root);

  const scene = await ctx.scene();
  if (scene) {
    scene.setRoute(null); scene.setTrail(null); scene.setRobot(null); scene.setScan(null); scene.setGraph(null); scene.showEllipse(null);
    scene.setCloudState(0, 0); scene.eyeBlend = 0;
    scene.setWalls(true, 900);
    scene.overview(1.0, 1800, -0.9);
    const release = scene.hold();
    const spin = scene.onFrame(() => { scene.rig.az -= 0.0004; });
    return () => { release(); spin(); };
  }
}

// ------------------------------------------------------------------ landmark gallery
function gallery(ctx: PageContext) {
  const { bundle } = ctx;
  const all = [...bundle.landmarks].sort((a, b) => (a.class === 'room_sign' ? 0 : 1) - (b.class === 'room_sign' ? 0 : 1) || a.text.localeCompare(b.text, 'en', { numeric: true }));
  const filters = [['all', 'All'], ['room_sign', 'Room signs'], ['unread', 'Unread'], ['door', 'Doors'], ['lift', 'Lifts'], ['stairs', 'Stairs'], ['exit_sign', 'Exits']];
  let active = 'room_sign';
  const grid = h('div', { class: 'masonry' });
  const count = h('p', { class: 'mono small muted', 'aria-live': 'polite' });
  const bar = h('div', { class: 'filters', role: 'toolbar', 'aria-label': 'Filter landmarks' }, ...filters.map(([k, label]) =>
    h('button', { type: 'button', class: 'filter', 'aria-pressed': String(k === active), 'data-k': k, text: label })));
  const card = (lm: Landmark) => {
    const conf = Math.round(lm.confidence * 100);
    const el = h('a', { class: `lm glass cls-${lm.class}`, href: `mission?landmark=${lm.id}`, 'data-link': true,
      'aria-label': `${CLASS_NAMES[lm.class] ?? lm.class} ${lm.text || ''}, confidence ${conf}%, ${lm.count} sightings. Show it on the map.` },
      lm.photo ? h('img', { src: bundle.url(lm.photo.thumb), alt: '', loading: 'lazy', width: lm.photo.w, height: lm.photo.h })
        : h('div', { class: 'lm-glyph', icon: landmarkIcon(lm.class) }),
      h('div', { class: 'lm-body' },
        h('p', { class: 'lm-ocr mono', text: lm.text || (lm.class === 'room_sign' ? 'unread' : CLASS_NAMES[lm.class] ?? lm.class) }),
        lm.class !== 'room_sign' ? h('p', { class: 'lm-pos mono', text: `at ${lm.x.toFixed(1)}, ${lm.y.toFixed(1)} m` }) : null,
        h('p', { class: 'lm-class eyebrow', text: `${CLASS_NAMES[lm.class] ?? lm.class} · ${lm.count} sightings` }),
        h('div', { class: 'meter-track thin', 'aria-hidden': 'true' }, h('span', { style: `width:${conf}%` })),
        h('span', { class: 'lm-fly' }, 'Show on map', icon('arrow'))));
    return el;
  };
  const draw = () => {
    const list = all.filter((lm) => active === 'all' || (active === 'unread' ? lm.class === 'room_sign' && !lm.text : lm.class === active));
    grid.replaceChildren(...list.map(card));
    count.textContent = `${list.length} landmarks`;
    gsap.fromTo(grid.children, { opacity: 0, y: 14 }, { opacity: 1, y: 0, stagger: 0.02, duration: 0.5 });
  };
  bar.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest('button');
    if (!b) return;
    active = b.dataset.k!;
    bar.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    draw();
  });
  draw();
  return h('section', { class: 'gallery', id: 'landmarks', 'aria-labelledby': 'gallery-title' },
    h('p', { class: 'eyebrow accent', text: 'Everything the robot noticed' }),
    h('h2', { id: 'gallery-title', class: 'display-s', text: 'Landmark gallery' }),
    h('p', { class: 'lede', text: 'Every sign, door, lift and staircase in the database, with what the camera read and how sure it was. Choose one to fly to it on the replay map.' }),
    bar, count, grid);
}

// ------------------------------------------------------------------ O8 on the map: one sighting against fused
function fusionCompare(bundle: PageContext['bundle']) {
  const matches = ((bundle.metrics.objectives.O4.parts[0]?.detail?.matches ?? []) as any[])
    .map((m) => ({ m, lm: bundle.landmarks.find((l) => l.id === m.landmark_id) }))
    .filter((x) => x.lm && x.lm.observations.length >= 2);
  if (!matches.length) return h('span');
  let index = matches.reduce((best, x, i) => {
    const e = Math.hypot(x.lm!.observations[0][1] - x.m.truth_x, x.lm!.observations[0][2] - x.m.truth_y);
    return e > best.e ? { e, i } : best;
  }, { e: -1, i: 0 }).i;
  let split = 0.5;
  const canvas = h('canvas', { class: 'fusion-canvas', 'aria-hidden': 'true' }) as HTMLCanvasElement;
  const handle = h('div', { class: 'fusion-handle', role: 'slider', tabindex: '0', 'aria-label': 'Compare one sighting (left) with fused (right)',
    'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-valuenow': '50' }, h('span'));
  const caption = h('p', { class: 'fusion-caption mono small' });
  const prev = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Previous landmark' }, icon('prev'));
  const next = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Next landmark' }, icon('next'));
  const wrap = h('div', { class: 'fusion-view' }, canvas, handle,
    h('span', { class: 'fusion-tag left mono', text: 'One sighting' }), h('span', { class: 'fusion-tag right mono', text: 'Fused' }));
  // The state image recoloured to the current theme (floor and walls), as on the main map.
  let img: HTMLCanvasElement | null = null;
  const source = new Image();
  const level = bundle.manifest.map.levels.find((l) => l.factor === 1)!;
  const recolour = () => {
    const c = document.createElement('canvas');
    c.width = source.width; c.height = source.height;
    const g = c.getContext('2d')!;
    g.drawImage(source, 0, 0);
    const data = g.getImageData(0, 0, c.width, c.height);
    const probe = (name: string) => {
      const el = document.createElement('span');
      el.style.color = getComputedStyle(document.documentElement).getPropertyValue(name);
      document.body.append(el);
      const rgb = getComputedStyle(el).color.match(/\d+/g)!.map(Number);
      el.remove();
      return rgb;
    };
    const floor = probe('--floor');
    const wall = probe('--wall');
    for (let i = 0; i < data.data.length; i += 4) {
      const v = data.data[i];
      const col = v > 190 ? wall : v > 60 ? floor : null;
      if (col) { data.data[i] = col[0]; data.data[i + 1] = col[1]; data.data[i + 2] = col[2]; data.data[i + 3] = 255; }
      else data.data[i + 3] = 0;
    }
    g.putImageData(data, 0, 0);
    img = c;
    draw();
  };
  source.onload = recolour;
  source.src = bundle.url(level.file);
  const draw = () => {
    const { m, lm } = matches[index];
    const w = wrap.clientWidth || 520;
    const hgt = Math.round(w * 0.56);
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = w * ratio; canvas.height = hgt * ratio;
    canvas.style.height = `${hgt}px`;
    const g = canvas.getContext('2d')!;
    g.setTransform(ratio, 0, 0, ratio, 0, 0);
    const css = getComputedStyle(document.documentElement);
    const col = (n: string) => css.getPropertyValue(n).trim();
    const scale = 70;                       // pixels per metre: errors of a few centimetres stay visible
    const cx = m.truth_x, cy = m.truth_y;
    const toS = (x: number, y: number) => [w / 2 + (x - cx) * scale, hgt / 2 - (y - cy) * scale];
    const mapInfo = bundle.manifest.map;
    const drawSide = (fused: boolean) => {
      g.fillStyle = col('--surface');
      g.fillRect(0, 0, w, hgt);
      if (img) {
        const [x0, y0] = toS(mapInfo.origin[0], mapInfo.origin[1] + mapInfo.height * mapInfo.resolution);
        g.globalAlpha = 0.85;
        g.imageSmoothingEnabled = false;
        g.drawImage(img, x0, y0, mapInfo.width * mapInfo.resolution * scale, mapInfo.height * mapInfo.resolution * scale);
        g.globalAlpha = 1;
      }
      const [tx, ty] = toS(cx, cy);
      const est = fused ? [lm!.x, lm!.y] : [lm!.observations[0][1], lm!.observations[0][2]];
      const [ex, ey] = toS(est[0], est[1]);
      if (fused) {
        g.fillStyle = col('--ink-3');
        for (const o of lm!.observations) { const [ox, oy] = toS(o[1], o[2]); g.beginPath(); g.arc(ox, oy, 2.5, 0, 7); g.fill(); }
      }
      g.strokeStyle = col('--ink');
      g.lineWidth = 2;
      g.beginPath(); g.arc(tx, ty, 9, 0, 7); g.stroke();
      g.setLineDash([4, 4]);
      g.strokeStyle = col('--accent');
      g.beginPath(); g.moveTo(tx, ty); g.lineTo(ex, ey); g.stroke();
      g.setLineDash([]);
      g.fillStyle = col('--accent');
      g.beginPath(); g.arc(ex, ey, 6, 0, 7); g.fill();
      const err = Math.hypot(est[0] - cx, est[1] - cy);
      g.fillStyle = col('--ink');
      g.font = '600 13px "Geist Mono Variable", monospace';
      g.fillText(`${(err * 100).toFixed(0)} cm`, ex + 10, ey - 10);
    };
    g.save(); g.beginPath(); g.rect(0, 0, w * split, hgt); g.clip(); drawSide(false); g.restore();
    g.save(); g.beginPath(); g.rect(w * split, 0, w, hgt); g.clip(); drawSide(true); g.restore();
    g.strokeStyle = col('--accent'); g.lineWidth = 2; g.beginPath(); g.moveTo(w * split, 0); g.lineTo(w * split, hgt); g.stroke();
    handle.style.left = `${split * 100}%`;
    handle.setAttribute('aria-valuenow', String(Math.round(split * 100)));
    const single = Math.hypot(lm!.observations[0][1] - cx, lm!.observations[0][2] - cy);
    const fused = Math.hypot(lm!.x - cx, lm!.y - cy);
    caption.textContent = `${CLASS_NAMES[m.class] ?? m.class} ${m.text || ''} · ring = measured truth · one sighting ${(single * 100).toFixed(0)} cm · fused over ${lm!.observations.length} ${(fused * 100).toFixed(0)} cm`;
  };
  const setSplit = (v: number) => { split = Math.max(0.05, Math.min(0.95, v)); draw(); };
  let dragging = false;
  wrap.addEventListener('pointerdown', (e) => { dragging = true; wrap.setPointerCapture(e.pointerId); setSplit((e.clientX - wrap.getBoundingClientRect().left) / wrap.clientWidth); });
  wrap.addEventListener('pointermove', (e) => { if (dragging) setSplit((e.clientX - wrap.getBoundingClientRect().left) / wrap.clientWidth); });
  wrap.addEventListener('pointerup', () => { dragging = false; });
  handle.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); setSplit(split - 0.05); }
    if (e.key === 'ArrowRight') { e.preventDefault(); setSplit(split + 0.05); }
  });
  prev.addEventListener('click', () => { index = (index - 1 + matches.length) % matches.length; draw(); });
  next.addEventListener('click', () => { index = (index + 1) % matches.length; draw(); });
  new ResizeObserver(draw).observe(wrap);
  window.addEventListener('merz-theme', () => { if (source.complete) recolour(); });
  return h('div', { class: 'fusion' },
    h('div', { class: 'fusion-head' }, h('p', { class: 'eyebrow', text: 'On the map · drag to compare' }),
      h('div', { class: 'fusion-nav' }, prev, next)),
    wrap, caption);
}
