import type { PageContext } from '../main';
import type { Entrance, Route, RouteStep } from '../data';
import { h, icon, announce, fmt, reducedMotion } from '../ui/dom';
import { turnIcon } from '../ui/icons';
import { countUp, gsap, reveal } from '../ui/motion';
import { beacon, stepPin, youAreHere } from '../ui/pins';
import { Overlay, type Pin } from '../scene/overlay';
import { attachControls } from '../scene/controls';
import { attachSheet } from '../ui/sheet';
import { FlatMap } from '../scene/flatmap';

const WALK_SPEED = 1.25;          // m/s, a typical indoor walking pace for the time estimate
const FLY_SPEED = 2.4;            // m/s in the walk-through
const DWELL_S = 2.4;              // pause at each junction so the photo can be read

/** Search that forgives OCR-like slips (O/0, l/1, missing dots). */
export function normalise(text: string) {
  return text.toUpperCase().replace(/[\s.\-_]/g, '').replace(/O/g, '0').replace(/[IL]/g, '1');
}

export function score(query: string, room: string): number {
  const q = normalise(query);
  const r = normalise(room);
  if (!q) return 1;
  if (r === q) return 100;
  if (r.startsWith(q)) return 80 - (r.length - q.length);
  if (r.includes(q)) return 60 - r.indexOf(q);
  let i = 0;
  for (const ch of r) if (ch === q[i]) i++;
  if (i === q.length) return 30;
  // One typo away.
  if (Math.abs(r.length - q.length) <= 1) {
    let diff = 0;
    for (let k = 0; k < Math.max(r.length, q.length); k++) if (r[k] !== q[k]) diff++;
    if (diff <= 1) return 20;
  }
  return 0;
}

export default async function find(ctx: PageContext) {
  const { bundle, root, params } = ctx;
  const entranceId = params.get('entrance');
  const entrance = bundle.graph.entrances.find((e) => e.id === entranceId);
  if (!entrance) return chooseEntrance(ctx, entranceId);

  const zone = bundle.routes[entrance.id];
  const reachable = Object.keys(zone?.routes ?? {}).sort();
  const allRooms = bundle.graph.rooms;
  let cleanup: (() => void)[] = [];
  let current: { room: string; route: Route } | null = null;
  let walk: ReturnType<typeof walkThrough> | null = null;

  // ---------------------------------------------------------------- layout
  const surface = h('div', { class: 'map-surface', tabindex: '0', role: 'application', 'aria-roledescription': 'map',
    'aria-label': `Map of the building from the robot's survey. ${entrance.name} is marked "You are here". Drag to move, pinch or use plus and minus to zoom. Keyboard: arrow keys move, Q and E rotate, W and S tilt.` });
  const panel = h('section', { class: 'find-panel glass', 'aria-label': 'Directions' });
  const handle = h('button', { class: 'sheet-handle', type: 'button', 'aria-label': 'Expand or collapse the directions panel' }, h('span'));
  const panelBody = h('div', { class: 'panel-body' });
  panel.append(handle, panelBody);
  const tools = h('div', { class: 'map-tools glass', role: 'toolbar', 'aria-label': 'Map view' });
  const btn3d = h('button', { class: 'icon-button', type: 'button', 'aria-pressed': 'false', 'aria-label': 'Show the map in 3D' }, icon('cube'));
  const btnIn = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Zoom in' }, icon('plus'));
  const btnOut = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Zoom out' }, icon('minus'));
  const compass = h('button', { class: 'icon-button compass', type: 'button', 'aria-label': 'Face north' }, icon('compass'));
  const btnFit = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Show the whole route' }, icon('locate'));
  tools.append(btn3d, btnIn, btnOut, compass, btnFit);
  root.append(surface, panel, tools);
  const sheet = attachSheet(panel, handle);
  cleanup.push(sheet.destroy);

  // ---------------------------------------------------------------- scene (3D, or the 2D fallback)
  const scene = await ctx.scene();
  const flat = scene ? null : new FlatMap(surface, bundle);
  const overlay = scene ? new Overlay(ctx.overlay, scene) : null;
  const pins: Pin[] = [];
  const addPin = (el: HTMLElement, x: number, y: number) => {
    if (overlay) pins.push(overlay.add(el, x, y));
    else flat!.addPin(el, x, y);
  };
  const clearRoutePins = () => {
    if (overlay) pins.splice(1).forEach((p) => overlay.remove(p));
    else flat!.clearPins(1);
  };
  addPin(youAreHere(entrance.name), entrance.x, entrance.y);

  const isNarrow = () => window.innerWidth < 900;
  const frameOpts = () => isNarrow()
    ? { padding: 28, pad: { t: 64, b: Math.round(window.innerHeight * 0.48) } }
    : { padding: 70, pad: { l: 480, t: 64, r: 60 } };
  let threeD = false;
  if (scene) {
    scene.setCloudState(0, 0);
    scene.setTrail(null);
    scene.setRobot(null);
    scene.setScan(null);
    scene.setGraph(null);
    scene.showEllipse(null);
    scene.setReveal(999);
    scene.setMapOpacity(1);
    scene.setRoute(null);
    scene.eyeBlend = 0;
    await scene.setWalls(false, 600);
    const zonePoints = (bundle.graph.zones[entrance.id]?.junctions ?? []).map((id) => bundle.graph.junctions.find((j) => j.id === id))
      .filter(Boolean).map((j) => [j!.x, j!.y] as [number, number]);
    scene.fit([[entrance.x, entrance.y], ...zonePoints], { tilt: 0, az: 0, duration: 1600, ...frameOpts() });
    cleanup.push(attachControls(surface, scene, { onUserMove: () => walk?.pause() }));
    const offCompass = scene.onFrame(() => {
      compass.style.setProperty('--rot', `${scene.rig.az}rad`);
    });
    cleanup.push(offCompass);
    const onTheme = () => scene.applyTheme();
    window.addEventListener('merz-theme', onTheme);
    cleanup.push(() => window.removeEventListener('merz-theme', onTheme));
    cleanup.push(() => { overlay!.destroy(); scene.setRoute(null); scene.eyeBlend = 0; });
  } else {
    btn3d.hidden = true;
    compass.hidden = true;
    cleanup.push(() => flat!.destroy());
  }

  const set3D = (on: boolean) => {
    if (!scene) return;
    threeD = on;
    btn3d.setAttribute('aria-pressed', String(on));
    btn3d.setAttribute('aria-label', on ? 'Show the map in 2D' : 'Show the map in 3D');
    btn3d.replaceChildren(icon(on ? 'flat' : 'cube'));
    scene.setWalls(on, 1100);
    scene.flyTo({ tilt: on ? 0.92 : 0, az: on ? (scene.rig.az || -0.45) : scene.rig.az, dist: scene.rig.dist * (on ? 0.8 : 1.25) }, 1200);
    announce(on ? '3D view' : '2D view');
  };
  btn3d.addEventListener('click', () => set3D(!threeD));
  btnIn.addEventListener('click', () => scene ? scene.flyTo({ dist: scene.rig.dist / 1.5 }, 400) : flat!.zoom(1.5));
  btnOut.addEventListener('click', () => scene ? scene.flyTo({ dist: scene.rig.dist * 1.5 }, 400) : flat!.zoom(1 / 1.5));
  compass.addEventListener('click', () => scene?.flyTo({ az: 0 }, 700));
  btnFit.addEventListener('click', () => frameRoute());

  function frameRoute() {
    const pts: [number, number][] = current && scene ? scene.route2points(current.route, entrance!) :
      current ? [[entrance!.x, entrance!.y], ...current.route.steps.map((s) => [s.x, s.y] as [number, number]),
        [current.route.destination.x, current.route.destination.y]] : [[entrance!.x, entrance!.y]];
    if (scene) scene.fit(pts, { tilt: threeD ? 0.9 : 0, duration: 1300, ...frameOpts() });
    else flat!.fit(pts);
  }

  // ---------------------------------------------------------------- panel: search
  function showSearch(initial = '') {
    current = null;
    clearRoutePins();
    scene?.setRoute(null);
    flat?.setRoute(null);
    const input = h('input', { id: 'room-search', class: 'search-input', type: 'search', inputmode: 'search', autocomplete: 'off',
      spellcheck: 'false', placeholder: 'Room number, e.g. S1.04', role: 'combobox', 'aria-expanded': 'true',
      'aria-controls': 'room-results', 'aria-autocomplete': 'list', 'aria-describedby': 'search-status' }) as HTMLInputElement;
    input.value = initial;
    const status = h('p', { id: 'search-status', class: 'search-status mono', 'aria-live': 'polite' });
    const results = h('ul', { id: 'room-results', class: 'room-results', role: 'listbox', 'aria-label': 'Reachable rooms' });
    const note = h('div', { class: 'search-note' });
    const draw = () => {
      const q = input.value.trim();
      const ranked = reachable.map((room) => ({ room, s: score(q, room) })).filter((r) => r.s > 0)
        .sort((a, b) => b.s - a.s || a.room.localeCompare(b.room, 'en', { numeric: true }));
      results.replaceChildren(...ranked.map(({ room }, i) => {
        const r = zone.routes[room];
        const option = h('li', { role: 'option', id: `opt-${i}`, 'aria-selected': i === 0 && q ? 'true' : 'false' },
          h('button', { class: 'room-option', type: 'button', tabindex: '-1', onclick: () => choose(room) },
            h('span', { class: 'room-num', text: room }),
            h('span', { class: 'room-meta mono', text: `${fmt(r.length_m)} m · ${Math.max(1, Math.round(r.length_m / WALK_SPEED / 60))} min` }),
            icon('arrow', 'icon room-go')));
        return option;
      }));
      status.textContent = q ? `${ranked.length} of ${reachable.length} rooms match` : `${reachable.length} rooms reachable from here`;
      note.replaceChildren();
      if (q && !ranked.length) {
        const elsewhere = allRooms.filter((r) => score(q, r.room) >= 60 && !reachable.includes(r.room));
        if (elsewhere.length) {
          const other = bundle.graph.entrances.find((e) => elsewhere[0].entrances.includes(e.id));
          note.append(h('div', { class: 'gentle' },
            h('span', { class: 'gentle-icon', icon: 'lock' }),
            h('div', {},
              h('p', { class: 'gentle-title' }, `Room ${elsewhere[0].room} is behind a locked door from here`),
              h('p', { class: 'muted small', text: `The robot mapped it, but could not reach it from the ${entrance!.name.toLowerCase()}, so it would not send you there.` }),
              other ? h('a', { class: 'button small-button', href: `find?entrance=${other.id}&room=${encodeURIComponent(elsewhere[0].room)}`, 'data-link': true },
                `Directions from the ${other.name}`, icon('arrow')) : null)));
        } else {
          note.append(h('div', { class: 'gentle' }, h('span', { class: 'gentle-icon', icon: 'info' }),
            h('div', {}, h('p', { class: 'gentle-title', text: `No room called “${q}” on the robot’s map` }),
              h('p', { class: 'muted small', text: 'Try the number on the door, such as S1.04. Rooms the robot could not read are not listed yet.' }))));
        }
      }
    };
    input.addEventListener('input', draw);
    input.addEventListener('keydown', (e) => {
      const options = [...results.querySelectorAll<HTMLButtonElement>('.room-option')];
      if (e.key === 'Enter' && options[0]) { e.preventDefault(); options[0].click(); }
      if (e.key === 'ArrowDown' && options[0]) { e.preventDefault(); options[0].focus(); }
    });
    results.addEventListener('keydown', (e) => {
      const options = [...results.querySelectorAll<HTMLButtonElement>('.room-option')];
      const i = options.indexOf(document.activeElement as HTMLButtonElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); options[Math.min(options.length - 1, i + 1)]?.focus(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); if (i <= 0) input.focus(); else options[i - 1].focus(); }
    });
    panelBody.replaceChildren(
      h('div', { class: 'here' },
        h('span', { class: 'here-dot', 'aria-hidden': 'true' }),
        h('div', {}, h('p', { class: 'eyebrow', text: 'You are here' }), h('p', { class: 'here-name', text: entrance!.name })),
        h('a', { class: 'link-button', href: 'find', 'data-link': true, text: 'Change' })),
      h('h1', { class: 'display-s panel-title', text: 'Where to?' }),
      h('label', { class: 'search-label', for: 'room-search' }, h('span', { class: 'sr-only', text: 'Search for a room' }),
        h('span', { class: 'search-icon', icon: 'search' }), input),
      status, note, results);
    draw();
    reveal(panelBody.children, 0.05, 0.06);
    sheet.snap('half');
    if (!isNarrow()) setTimeout(() => input.focus({ preventScroll: true }), 400);
  }

  // ---------------------------------------------------------------- panel: route
  function choose(room: string, replace = false) {
    const route = zone.routes[room];
    if (!route) {
      showSearch(room);
      return;
    }
    const url = new URL(location.href);
    if (url.searchParams.get('room') !== room) {
      url.searchParams.set('room', room);
      history[replace ? 'replaceState' : 'pushState'](null, '', url);
    }
    current = { room, route };
    clearRoutePins();
    const points: [number, number][] = [[entrance!.x, entrance!.y], ...route.steps.map((s) => [s.x, s.y] as [number, number]),
      [route.destination.x, route.destination.y]];
    if (scene) {
      scene.setRoute(points);
      scene.drawRoute(reducedMotion() ? 0 : 1900);
    } else flat!.setRoute(points);
    route.steps.forEach((s, i) => addPin(stepPin(i + 1, () => focusStep(i)), s.x, s.y));
    addPin(beacon(room), route.destination.x, route.destination.y);
    frameRoute();

    const minutes = Math.max(1, Math.round(route.length_m / WALK_SPEED / 60));
    const dist = h('span', { class: 'big-num mono' });
    const time = h('span', { class: 'big-num mono' });
    const turns = h('span', { class: 'big-num mono' });
    const list = h('ol', { class: 'route-steps', 'aria-label': 'Directions, step by step' },
      h('li', { class: 'route-step start' }, h('span', { class: 'step-glyph here-glyph', 'aria-hidden': 'true' }),
        h('div', {}, h('p', { class: 'step-text', text: `Start at the ${entrance!.name.toLowerCase()}` }))),
      ...route.steps.map((s, i) => h('li', { class: 'route-step' },
        h('button', { class: 'step-button', type: 'button', onclick: () => focusStep(i) },
          h('span', { class: 'step-glyph', icon: turnIcon(s.turn) }),
          h('div', {}, h('p', { class: 'step-text', text: s.instruction }),
            h('p', { class: 'step-meta mono', text: `Junction ${i + 1} · ${fmt(s.distance_m)} m` })),
          s.photo ? h('img', { class: 'step-thumb', src: bundle.url(s.photo.thumb), alt: '', loading: 'lazy', width: 72, height: 46 }) : null))));
    const walkButton = h('button', { class: 'button primary walk-button', type: 'button', icon: 'walk' }, 'Walk it with photos');
    walkButton.addEventListener('click', () => startWalk());
    panelBody.replaceChildren(
      h('button', { class: 'back-button', type: 'button', icon: 'back', onclick: () => { removeRoomParam(); showSearch(); } }, 'All rooms'),
      h('p', { class: 'eyebrow accent', text: `From the ${entrance!.name.toLowerCase()}` }),
      h('h1', { class: 'display route-title' }, h('span', { class: 'to', text: 'To ' }), room),
      h('dl', { class: 'route-stats' },
        h('div', {}, h('dt', { class: 'eyebrow', text: 'Distance' }), h('dd', {}, dist, h('small', { text: 'm' }))),
        h('div', {}, h('dt', { class: 'eyebrow', text: 'Walk' }), h('dd', {}, time, h('small', { text: 'min' }))),
        h('div', {}, h('dt', { class: 'eyebrow', text: 'Turns' }), h('dd', {}, turns))),
      walkButton, list);
    countUp(dist, route.length_m, 0, '', 0.2);
    countUp(time, minutes, 0, '', 0.3);
    countUp(turns, route.turns, 0, '', 0.4);
    reveal(panelBody.children, 0.05, 0.06);
    reveal(list.children, 0.5, 0.06);
    sheet.snap('half');
    announce(`Route to room ${room}: about ${Math.round(route.length_m)} metres, ${route.steps.length} junctions. ${route.steps.map((s) => s.instruction).join(' ')}`);
  }

  function focusStep(i: number) {
    if (!current) return;
    const s = current.route.steps[i];
    if (scene) scene.flyTo({ x: s.x, y: s.y, dist: 26, tilt: threeD ? 0.9 : scene.rig.tilt }, 1100);
    else flat!.fit([[s.x - 6, s.y - 6], [s.x + 6, s.y + 6]]);
    panelBody.querySelectorAll('.route-step').forEach((li, k) => li.classList.toggle('is-active', k === i + 1));
    announce(`Junction ${i + 1}: ${s.instruction}`);
  }

  function removeRoomParam() {
    const url = new URL(location.href);
    url.searchParams.delete('room');
    history.pushState(null, '', url);
  }

  // ---------------------------------------------------------------- walk-through
  function startWalk() {
    if (!current) return;
    walk = walkThrough(ctx, entrance!, current.room, current.route, scene, () => { walk = null; root.classList.remove('walking'); });
    root.classList.add('walking');
  }

  const onPop = () => {
    const room = new URL(location.href).searchParams.get('room');
    if (room && zone.routes[room]) choose(room, true); else showSearch();
  };
  window.addEventListener('popstate', onPop);
  cleanup.push(() => window.removeEventListener('popstate', onPop));

  const wanted = params.get('room');
  if (wanted && zone?.routes[wanted]) choose(wanted, true);
  else showSearch(wanted ?? '');

  return () => { walk?.close(); cleanup.forEach((fn) => fn()); cleanup = []; };
}

// ------------------------------------------------------------------ choosing an entrance
function chooseEntrance(ctx: PageContext, unknown: string | null) {
  const { bundle, root } = ctx;
  const cards = bundle.graph.entrances.map((e) => h('a', { class: 'entrance-card glass', href: `find?entrance=${encodeURIComponent(e.id)}`, 'data-link': true },
    h('span', { class: 'here-dot', 'aria-hidden': 'true' }),
    h('span', { class: 'entrance-name', text: e.name }),
    h('span', { class: 'entrance-meta mono', text: `${bundle.graph.zones[e.id]?.rooms.length ?? 0} rooms reachable` }),
    icon('arrow', 'icon entrance-go')));
  root.append(h('div', { class: 'choose' },
    unknown ? h('div', { class: 'gentle glass', role: 'alert' }, h('span', { class: 'gentle-icon', icon: 'info' }),
      h('div', {}, h('p', { class: 'gentle-title', text: 'This QR code points to an entrance we do not know' }),
        h('p', { class: 'muted small' }, 'It asked for “', unknown, '”, which is not on the robot’s map. Choose the entrance you are standing at.'))) : null,
    h('p', { class: 'eyebrow accent', text: 'Find a room' }),
    h('h1', { class: 'display choose-title', text: 'Which entrance are you at?' }),
    h('p', { class: 'lede', text: 'Each entrance has a poster with a QR code; scanning it skips this step.' }),
    h('div', { class: 'entrance-grid' }, ...cards)));
  reveal(root.querySelectorAll('.choose > *'), 0.05, 0.08);
  ctx.scene().then((scene) => {
    if (!scene) return;
    scene.setRoute(null); scene.setCloudState(0, 0); scene.setTrail(null); scene.setRobot(null); scene.setScan(null); scene.setGraph(null);
    scene.setWalls(true, 900);
    scene.overview(0.9, 1600, -0.6);
  });
}

// ------------------------------------------------------------------ the walk-through
function walkThrough(ctx: PageContext, entrance: Entrance, room: string, route: Route, scene: Awaited<ReturnType<PageContext['scene']>>,
  onClose: () => void) {
  const { bundle } = ctx;
  const points: [number, number][] = [[entrance.x, entrance.y], ...route.steps.map((s) => [s.x, s.y] as [number, number]),
    [route.destination.x, route.destination.y]];
  const cumulative = [0];
  for (let i = 1; i < points.length; i++) cumulative.push(cumulative[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
  const total = cumulative[cumulative.length - 1];
  const junctionAt = route.steps.map((_, i) => cumulative[i + 1]);
  const at = (d: number): [number, number] => {
    d = Math.max(0, Math.min(total, d));
    let i = 1;
    while (i < cumulative.length - 1 && cumulative[i] < d) i++;
    const k = (d - cumulative[i - 1]) / Math.max(1e-6, cumulative[i] - cumulative[i - 1]);
    return [points[i - 1][0] + (points[i][0] - points[i - 1][0]) * k, points[i - 1][1] + (points[i][1] - points[i - 1][1]) * k];
  };

  const photoA = h('img', { class: 'walk-photo', alt: '' }) as HTMLImageElement;
  const photoB = h('img', { class: 'walk-photo', alt: '' }) as HTMLImageElement;
  const caption = h('div', { class: 'walk-caption' });
  const scrub = h('input', { class: 'scrub', type: 'range', min: '0', max: String(total), step: '0.1', value: '0',
    'aria-label': 'Position along the route' }) as HTMLInputElement;
  const play = h('button', { class: 'icon-button play', type: 'button', 'aria-label': 'Pause' }, icon('pause'));
  const prev = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Previous junction' }, icon('prev'));
  const next = h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Next junction' }, icon('next'));
  const close = h('button', { class: 'icon-button walk-close', type: 'button', 'aria-label': 'Leave the walk-through' }, icon('close'));
  const ticks = h('div', { class: 'scrub-ticks', 'aria-hidden': 'true' }, ...junctionAt.map((d, i) =>
    h('span', { style: `left:${(d / total) * 100}%`, text: String(i + 1) })));
  const card = h('div', { class: 'walk-card glass' },
    h('div', { class: 'walk-media' }, photoA, photoB, h('span', { class: 'walk-badge mono' })), caption);
  const ui = h('div', { class: 'walk', role: 'dialog', 'aria-modal': 'true', 'aria-label': `Walk-through to room ${room}` },
    h('div', { class: 'walk-top' }, h('p', { class: 'eyebrow accent', text: `Walk-through · to ${room}` }), close),
    card,
    h('div', { class: 'walk-controls glass' }, prev, play, next, h('div', { class: 'scrub-wrap' }, scrub, ticks)));
  document.getElementById('app')!.append(ui);

  let d = 0;
  let playing = !reducedMotion();
  let dwell = 0;
  let shown = -2;
  let front = photoA;
  let last = performance.now();
  let raf = 0;
  const release = scene?.hold();
  scene?.setWalls(true, 900);

  function show(i: number) {
    if (i === shown) return;
    shown = i;
    const step: RouteStep | undefined = route.steps[i];
    const back = front === photoA ? photoB : photoA;
    const badge = card.querySelector('.walk-badge')!;
    if (step?.photo) {
      back.src = bundle.url(step.photo.src);
      back.alt = `Photo the robot took at junction ${i + 1}`;
      back.onload = () => {
        if (reducedMotion()) { back.style.opacity = '1'; front.style.opacity = '0'; }
        else { gsap.to(back, { opacity: 1, duration: 0.6 }); gsap.to(front, { opacity: 0, duration: 0.6 }); }
        front = back;
      };
      card.classList.remove('no-photo');
    } else {
      gsap.to([photoA, photoB], { opacity: 0, duration: 0.3 });
      card.classList.add('no-photo');
    }
    badge.textContent = i < 0 ? 'Start' : `Junction ${i + 1} of ${route.steps.length}`;
    caption.replaceChildren(
      h('span', { class: 'walk-turn', icon: i < 0 ? 'door' : turnIcon(step!.turn) }),
      h('p', { class: 'walk-instruction', text: i < 0 ? `Leave the ${entrance.name.toLowerCase()} and follow the glowing line.` : step!.instruction }));
    if (!reducedMotion()) gsap.fromTo(caption.children, { opacity: 0, y: 10 }, { opacity: 1, y: 0, stagger: 0.06, duration: 0.6 });
    announce(i < 0 ? 'Start of the walk-through.' : `Junction ${i + 1} of ${route.steps.length}. ${step!.instruction}`);
    scrub.setAttribute('aria-valuetext', i < 0 ? 'Start' : `Junction ${i + 1} of ${route.steps.length}: ${step!.instruction}`);
  }

  function place() {
    const [x, y] = at(d);
    const [tx, ty] = at(d + 4.5);
    const dir = Math.hypot(tx - x, ty - y) < 0.5 ? [route.destination.x, route.destination.y] : [tx, ty];
    if (scene) {
      scene.eye = { px: x, py: y, ph: 1.55, tx: dir[0], ty: dir[1], th: 1.2 };
      scene.invalidate();
    }
    scrub.value = String(d);
    let index = -1;
    junctionAt.forEach((jd, i) => { if (d >= jd - 2.5) index = i; });
    show(index);
  }

  function tick(now: number) {
    raf = requestAnimationFrame(tick);
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!playing) return;
    if (dwell > 0) { dwell -= dt; return; }
    const before = d;
    d = Math.min(total, d + FLY_SPEED * dt);
    if (junctionAt.some((jd) => before < jd && d >= jd)) dwell = DWELL_S;
    if (d >= total) { setPlaying(false); }
    place();
  }

  function setPlaying(on: boolean) {
    playing = on;
    play.replaceChildren(icon(on ? 'pause' : 'play'));
    play.setAttribute('aria-label', on ? 'Pause' : 'Play');
  }

  function jump(dir: 1 | -1) {
    const stops = [0, ...junctionAt, total];
    const target = dir > 0 ? stops.find((s) => s > d + 0.5) ?? total : [...stops].reverse().find((s) => s < d - 0.5) ?? 0;
    setPlaying(false);
    if (reducedMotion() || !scene) { d = target; place(); return; }
    const from = d;
    gsap.to({ k: 0 }, { k: 1, duration: 0.9, ease: 'power2.inOut', onUpdate() { d = from + (target - from) * this.targets()[0].k; place(); } });
  }

  play.addEventListener('click', () => { if (d >= total) d = 0; setPlaying(!playing); });
  prev.addEventListener('click', () => jump(-1));
  next.addEventListener('click', () => jump(1));
  scrub.addEventListener('input', () => { setPlaying(false); d = Number(scrub.value); place(); });
  close.addEventListener('click', () => api.close());
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') api.close();
    else if (e.key === 'ArrowRight') { e.preventDefault(); jump(1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); jump(-1); }
    else if (e.key === ' ' && document.activeElement !== play) { e.preventDefault(); setPlaying(!playing); }
  };
  document.addEventListener('keydown', onKey);
  // Swipe the photo to move between junctions.
  let swipeX: number | null = null;
  card.addEventListener('pointerdown', (e) => { swipeX = e.clientX; });
  card.addEventListener('pointerup', (e) => {
    if (swipeX !== null && Math.abs(e.clientX - swipeX) > 40) jump(e.clientX < swipeX ? 1 : -1);
    swipeX = null;
  });

  if (scene) {
    place();
    scene.eyeBlend = 0;
    scene.tween(reducedMotion() ? 0 : 1600, (k) => { scene.eyeBlend = k; });
  } else place();
  if (!reducedMotion()) gsap.fromTo(ui.children, { opacity: 0, y: 20 }, { opacity: 1, y: 0, stagger: 0.08, duration: 0.8 });
  setPlaying(playing);
  raf = requestAnimationFrame(tick);
  close.focus();

  const api = {
    pause: () => setPlaying(false),
    close: () => {
      cancelAnimationFrame(raf);
      document.removeEventListener('keydown', onKey);
      if (scene) {
        const from = scene.eyeBlend;
        scene.tween(reducedMotion() ? 0 : 1000, (k) => { scene.eyeBlend = from * (1 - k); }, () => { scene.eye = null; });
      }
      release?.();
      gsap.to(ui, { opacity: 0, duration: 0.3, onComplete: () => ui.remove() });
      onClose();
    },
  };
  return api;
}
