import type { PageContext } from '../main';
import { loadMission, poseAt, type Landmark } from '../data';
import { h, icon, announce, clock, fmt, reducedMotion } from '../ui/dom';
import { CLASS_NAMES } from '../ui/icons';
import { gsap, reveal } from '../ui/motion';
import { landmarkPin } from '../ui/pins';
import { Overlay, type Pin } from '../scene/overlay';
import { attachControls } from '../scene/controls';

const SPEEDS = [1, 2, 4, 8, 16];

export default async function mission(ctx: PageContext) {
  const { bundle, root } = ctx;
  const skeleton = h('div', { class: 'replay-skeleton' }, h('div', { class: 'skeleton', style: 'height:44px;width:260px' }),
    h('div', { class: 'skeleton', style: 'height:64px' }));
  root.append(skeleton);
  const [scene, data] = await Promise.all([ctx.scene(), loadMission(bundle)]);
  skeleton.remove();
  if (!data) {
    root.append(h('div', { class: 'empty glass' }, h('span', { class: 'empty-icon', icon: 'mission' }),
      h('h1', { class: 'display-s', text: 'No mission recording yet' }),
      h('p', { class: 'muted', text: 'This run was imported without a rosbag, so there is nothing to replay. Record one with record_bag.launch.py and import it again.' })));
    return;
  }
  const { mission: m, scans } = data;
  const duration = m.duration_s;
  const signs = bundle.landmarks.filter((l) => l.first_seen_s !== null).sort((a, b) => a.first_seen_s! - b.first_seen_s!);
  let t = 0;
  let speed = 8;
  let playing = !reducedMotion();
  let follow = true;
  let selected: Landmark | null = null;
  const cleanup: (() => void)[] = [];

  // ---------------------------------------------------------------- UI
  const surface = h('div', { class: 'map-surface', tabindex: '0', role: 'application', 'aria-roledescription': 'map',
    'aria-label': 'Mission replay map. Drag to move, pinch or plus and minus to zoom. The mission log below lists every event.' });
  const v = (label: string) => {
    const dd = h('dd', { text: '—' });
    return { node: h('div', { class: 'tele' }, h('dt', { text: label }), dd), dd };
  };
  const hud = { time: v('Mission time'), pos: v('Position'), heading: v('Heading'), speed: v('Speed'), dist: v('Travelled'),
    signs: v('Signs read'), segment: v('Run') };
  const hudPanel = h('aside', { class: 'hud glass', 'aria-label': 'Telemetry' }, ...Object.values(hud).map((x) => x.node));
  const title = h('div', { class: 'replay-title' },
    h('p', { class: 'eyebrow accent', text: 'Mission replay' }),
    h('h1', { class: 'display-s', text: 'How the robot built this map' }),
    h('p', { class: 'muted small', text: `${m.segments.length} entrance runs · ${fmt(m.distance_m)} m · ${clock(duration)} of driving${bundle.manifest.sample ? ' · synthetic sample' : ''}` }));
  const playBtn = h('button', { class: 'icon-button play big', type: 'button', 'aria-label': 'Pause replay' }, icon('pause'));
  const scrub = h('input', { class: 'scrub', type: 'range', min: '0', max: String(duration), step: '0.1', value: '0',
    'aria-label': 'Mission time' }) as HTMLInputElement;
  const readout = h('span', { class: 'mono readout', text: `00:00 / ${clock(duration)}` });
  const speedGroup = h('div', { class: 'segmented', role: 'radiogroup', 'aria-label': 'Replay speed' },
    ...SPEEDS.map((s) => h('button', { type: 'button', role: 'radio', 'aria-checked': String(s === speed), 'data-speed': s, text: `${s}×` })));
  const bands = h('div', { class: 'scrub-bands', 'aria-hidden': 'true' },
    ...m.segments.map((s) => h('span', { style: `left:${(s.start_s / duration) * 100}%;width:${((s.end_s - s.start_s) / duration) * 100}%` })),
    ...signs.map((lm) => h('i', { class: lm.class === 'room_sign' ? 'sign' : '', style: `left:${(lm.first_seen_s! / duration) * 100}%` })));
  const followBtn = h('button', { class: 'button follow', type: 'button', icon: 'locate', hidden: true }, 'Follow the robot');
  const bar = h('div', { class: 'timeline glass' }, playBtn,
    h('div', { class: 'scrub-wrap' }, bands, scrub), readout, speedGroup);
  const card = h('aside', { class: 'lm-card glass', hidden: true, 'aria-live': 'polite' });
  const log = h('details', { class: 'mission-log glass' },
    h('summary', {}, 'Mission log ', h('span', { class: 'muted', text: `(${signs.length} landmarks)` })),
    h('ol', {}, ...m.segments.map((s) => h('li', { class: 'mono small' }, `${clock(s.start_s)}  Run started: ${s.name}`)),
      ...signs.map((lm) => h('li', {}, h('button', { type: 'button', class: 'log-item', onclick: () => select(lm, true) },
        h('span', { class: 'mono', text: clock(lm.first_seen_s!) }), ` ${CLASS_NAMES[lm.class] ?? lm.class}${lm.text ? ' ' + lm.text : ''}`)))));
  root.append(surface, title, hudPanel, followBtn, card, log, bar);
  reveal([title, hudPanel, bar, log], 0.1, 0.08);

  if (!scene) {
    root.append(h('p', { class: 'gentle glass no-webgl-note', text: 'The replay needs 3D graphics (WebGL), which this browser does not offer. The mission log above lists every event.' }));
    return;
  }

  // ---------------------------------------------------------------- scene
  const overlay = new Overlay(ctx.overlay, scene);
  const release = scene.hold();
  scene.setRoute(null);
  scene.setGraph(null);
  scene.setCloudState(0, 0);
  scene.setMapOpacity(1);
  scene.eyeBlend = 0;
  await scene.setWalls(false, 500);
  scene.setTrail(m.trajectory, 90, 0.18);
  cleanup.push(attachControls(surface, scene, { onUserMove: () => { follow = false; followBtn.hidden = false; } }));
  const pins = new Map<number, Pin>();
  for (const lm of signs) {
    const el = landmarkPin(lm, (l) => select(l, false));
    el.classList.add('hidden-pin');
    pins.set(lm.id, overlay.add(el, lm.x, lm.y, 1.2));
  }
  const obsPins: Pin[] = [];

  function select(lm: Landmark | null, fly: boolean) {
    selected = lm;
    obsPins.splice(0).forEach((p) => overlay.remove(p));
    pins.forEach((p, id) => p.el.classList.toggle('is-selected', id === lm?.id));
    scene!.showEllipse(lm);
    if (!lm) { card.hidden = true; return; }
    for (const o of lm.observations) obsPins.push(overlay.add(h('span', { class: 'obs-dot', 'aria-hidden': 'true' }), o[1], o[2], 0.2));
    if (fly) { follow = false; followBtn.hidden = false; scene!.flyTo({ x: lm.x, y: lm.y, dist: 18, tilt: 0.6 }, 1100); if (t < (lm.first_seen_s ?? 0)) seek(lm.first_seen_s! + 0.5); }
    const conf = Math.round(lm.confidence * 100);
    card.replaceChildren(
      h('button', { class: 'icon-button card-close', type: 'button', 'aria-label': 'Close details', onclick: () => select(null, false) }, icon('close')),
      lm.photo ? h('img', { class: 'lm-photo', src: bundle.url(lm.photo.src), alt: `The sign camera's photo of ${lm.text || 'this sign'}`, width: lm.photo.w, height: lm.photo.h })
        : h('div', { class: 'lm-photo placeholder', icon: 'camera' }),
      h('p', { class: 'eyebrow', text: CLASS_NAMES[lm.class] ?? lm.class }),
      h('p', { class: 'lm-text display-s', text: lm.text || (lm.class === 'room_sign' ? 'Not read' : CLASS_NAMES[lm.class] ?? lm.class) }),
      lm.class === 'room_sign' ? h('p', { class: 'muted small', text: lm.text ? 'What the OCR read from the sign.' : 'The sign was seen, but its number could not be read.' }) : '',
      h('div', { class: 'meter', role: 'meter', 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-valuenow': String(conf), 'aria-label': 'Detector confidence' },
        h('div', { class: 'meter-row' }, h('span', { class: 'eyebrow', text: 'Confidence' }), h('span', { class: 'mono', text: `${conf}%` })),
        h('div', { class: 'meter-track' }, h('span', { style: `width:${conf}%` }))),
      h('dl', { class: 'lm-facts' },
        h('div', { class: 'tele' }, h('dt', { text: 'Sightings' }), h('dd', { text: String(lm.count) })),
        h('div', { class: 'tele' }, h('dt', { text: 'First seen' }), h('dd', { text: lm.first_seen_s === null ? '—' : clock(lm.first_seen_s) })),
        h('div', { class: 'tele' }, h('dt', { text: 'Position' }), h('dd', {}, `${fmt(lm.x, 2)}, ${fmt(lm.y, 2)}`, h('small', { text: 'm' }))),
        h('div', { class: 'tele' }, h('dt', { text: '95% region' }), h('dd', {}, `±${fmt(lm.sd[0] * 2.45, 2)} × ${fmt(lm.sd[1] * 2.45, 2)}`, h('small', { text: 'm' })))),
      h('p', { class: 'muted small', text: 'The ring on the map is the 95% uncertainty region; the dots are the individual sightings that were averaged.' }));
    card.hidden = false;
    if (!reducedMotion()) gsap.fromTo(card, { opacity: 0, y: 16, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.6 });
  }

  // ---------------------------------------------------------------- the replay clock
  let lastAnnounce = 0;
  const shown = new Set<number>();
  function apply() {
    const pose = poseAt(m.trajectory, t);
    const k = m.snapshot_times.filter((s) => s <= t).length;
    scene!.setReveal(t >= duration - 0.05 ? 999 : Math.max(0, k));
    scene!.setTrailTime(t);
    scene!.setRobot({ x: pose[1], y: pose[2], yaw: pose[3] });
    let si = -1;
    for (let lo = 0, hi = m.scans.meta.length - 1; lo <= hi;) {
      const mid = (lo + hi) >> 1;
      if (m.scans.meta[mid][0] <= t) { si = mid; lo = mid + 1; } else hi = mid - 1;
    }
    if (si >= 0 && t - m.scans.meta[si][0] < 2) {
      const s = m.scans.meta[si];
      scene!.setScan({ x: s[1], y: s[2], yaw: s[3] }, scans.subarray(si * m.scans.rays, (si + 1) * m.scans.rays), s[4], s[5]);
    } else scene!.setScan(null);
    if (follow) {
      scene!.rig.x += (pose[1] - scene!.rig.x) * 0.08;
      scene!.rig.y += (pose[2] - scene!.rig.y) * 0.08;
    }
    let found = 0;
    for (const lm of signs) {
      const visible = lm.first_seen_s! <= t;
      const pin = pins.get(lm.id)!;
      if (visible && !shown.has(lm.id)) {
        shown.add(lm.id);
        pin.el.classList.remove('hidden-pin');
        pin.el.classList.add('pop');
        if (playing && performance.now() - lastAnnounce > 4000 && lm.class === 'room_sign') {
          announce(`Sign ${lm.text || 'unread'} found at ${clock(t)}.`);
          lastAnnounce = performance.now();
        }
      } else if (!visible && shown.has(lm.id)) {
        shown.delete(lm.id);
        pin.el.classList.add('hidden-pin');
        pin.el.classList.remove('pop');
      }
      if (visible && lm.class === 'room_sign' && lm.text) found++;
    }
    const prev = poseAt(m.trajectory, Math.max(0, t - 1));
    const speedMs = Math.hypot(pose[1] - prev[1], pose[2] - prev[2]) / Math.min(1, Math.max(0.1, t));
    const segment = m.segments.find((s) => t >= s.start_s - 0.1 && t <= s.end_s + 2) ?? m.segments[m.segments.length - 1];
    hud.time.dd.textContent = clock(t);
    hud.pos.dd.replaceChildren(`${fmt(pose[1], 1)}, ${fmt(pose[2], 1)}`, h('small', { text: 'm' }));
    hud.heading.dd.replaceChildren(fmt(((90 - (pose[3] * 180) / Math.PI) % 360 + 360) % 360, 0), h('small', { text: '°' }));
    hud.speed.dd.replaceChildren(fmt(speedMs, 2), h('small', { text: 'm/s' }));
    hud.dist.dd.replaceChildren(fmt(pose[4], 0), h('small', { text: 'm' }));
    hud.signs.dd.textContent = String(found);
    hud.segment.dd.textContent = segment?.name.replace(/^\d+_\d+_/, '') ?? '—';
    scrub.value = String(t);
    scrub.setAttribute('aria-valuetext', `${clock(t)} of ${clock(duration)}`);
    readout.textContent = `${clock(t)} / ${clock(duration)}`;
  }

  function seek(to: number) { t = Math.max(0, Math.min(duration, to)); apply(); }
  function setPlaying(on: boolean) {
    playing = on;
    playBtn.replaceChildren(icon(on ? 'pause' : 'play'));
    playBtn.setAttribute('aria-label', on ? 'Pause replay' : 'Play replay');
  }
  let last = performance.now();
  let raf = 0;
  const tick = (now: number) => {
    raf = requestAnimationFrame(tick);
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    if (playing) {
      t += dt * speed;
      if (t >= duration) { t = duration; setPlaying(false); }
      apply();
    } else if (follow) apply();
  };

  playBtn.addEventListener('click', () => { if (t >= duration) t = 0; setPlaying(!playing); });
  scrub.addEventListener('input', () => { seek(Number(scrub.value)); });
  speedGroup.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest('button');
    if (!b) return;
    speed = Number(b.dataset.speed);
    speedGroup.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    announce(`Speed ${speed} times`);
  });
  speedGroup.addEventListener('keydown', (e) => {
    const i = SPEEDS.indexOf(speed);
    const j = e.key === 'ArrowRight' ? Math.min(SPEEDS.length - 1, i + 1) : e.key === 'ArrowLeft' ? Math.max(0, i - 1) : i;
    if (j !== i) { e.preventDefault(); (speedGroup.children[j] as HTMLButtonElement).click(); (speedGroup.children[j] as HTMLButtonElement).focus(); }
  });
  followBtn.addEventListener('click', () => {
    follow = true;
    followBtn.hidden = true;
    const pose = poseAt(m.trajectory, t);
    scene.flyTo({ x: pose[1], y: pose[2], dist: 46, tilt: 0.72 }, 900);
  });
  const onKey = (e: KeyboardEvent) => {
    if ((e.target as HTMLElement).closest('input, button, summary')) return;
    if (e.key === ' ') { e.preventDefault(); setPlaying(!playing); }
    if (e.key === 'Escape') select(null, false);
  };
  document.addEventListener('keydown', onKey);
  const onTheme = () => scene.applyTheme();
  window.addEventListener('merz-theme', onTheme);

  const first = m.trajectory[0];
  scene.flyTo({ x: first[1], y: first[2], dist: 46, tilt: 0.72, az: -0.3 }, 1600);
  apply();
  // Opened from the landmark gallery: show the finished map with that landmark selected.
  const wanted = Number(ctx.params.get('landmark'));
  const target = signs.find((l) => l.id === wanted);
  if (target) { playing = false; seek(duration); select(target, true); }
  setPlaying(playing);
  raf = requestAnimationFrame(tick);

  return () => {
    cancelAnimationFrame(raf);
    document.removeEventListener('keydown', onKey);
    window.removeEventListener('merz-theme', onTheme);
    cleanup.forEach((fn) => fn());
    overlay.destroy();
    release();
    scene.setTrail(null);
    scene.setRobot(null);
    scene.setScan(null);
    scene.showEllipse(null);
    scene.setReveal(999);
    void selected;
  };
}
