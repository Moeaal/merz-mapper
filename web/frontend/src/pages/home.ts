import type { PageContext } from '../main';
import { loadMission } from '../data';
import { h, fmt, reducedMotion } from '../ui/dom';
import { countUp, gsap, reveal, revealOnScroll, ScrollTrigger } from '../ui/motion';
import { landmarkPin, beacon, youAreHere } from '../ui/pins';
import { Overlay } from '../scene/overlay';

// The landing page: the building materialises from the robot's laser points, then the story of the mission.
export default async function home(ctx: PageContext) {
  const { bundle, root } = ctx;
  const stats = bundle.manifest.stats;
  const north = bundle.graph.entrances[0];
  const zoneRooms = bundle.graph.entrances.map((e) => ({ e, n: bundle.graph.zones[e.id]?.rooms.length ?? 0 }));

  const statTile = (label: string, unit: string, value: number | null, digits = 0, note?: string) => {
    const number = h('span', { class: 'stat-value mono', text: '—' });
    const tile = h('div', { class: 'stat' },
      h('dt', { class: 'eyebrow', text: label }),
      h('dd', {}, number, h('span', { class: 'stat-unit', text: unit }), note ? h('span', { class: 'stat-note', text: note }) : null));
    return { tile, number, value, digits };
  };
  const tiles = [
    statTile('Explored', 'm', stats.metres_explored),
    statTile('Signs read', '', stats.signs_read),
    statTile('Rooms mapped', '', stats.rooms_mapped),
    statTile('Landmark error', 'm', stats.landmark_error_m, 2, stats.landmark_error_m === null ? 'not yet measured' : 'mean, O4'),
  ];
  const skip = h('button', { class: 'skip-intro', type: 'button' }, 'Skip intro');
  const entry = (href: string, iconName: 'find' | 'mission' | 'results', title: string, text: string, params = '') =>
    h('a', { class: 'entry glass', href: href + params, 'data-link': true },
      h('span', { class: 'entry-icon', icon: iconName }),
      h('span', { class: 'entry-title', text: title }),
      h('span', { class: 'entry-text', text }),
      h('span', { class: 'entry-arrow', icon: 'arrow' }));

  const hero = h('section', { class: 'hero', 'aria-labelledby': 'hero-title' },
    h('div', { class: 'hero-copy' },
      h('p', { class: 'eyebrow accent', 'data-hero': true }, 'EEE3094 · Autonomous indoor mapping rover'),
      h('h1', { id: 'hero-title', class: 'display hero-title' },
        h('span', { class: 'line', 'data-hero': true, text: 'The building,' }),
        h('span', { class: 'line', 'data-hero': true }, 'as the ', h('em', { text: 'robot' }), ' saw it.')),
      h('p', { class: 'lede', 'data-hero': true, text: 'A small rover drives Merz Court on its own, maps every corridor with laser light, reads the door signs and photographs each junction. Then it shows you the way.' }),
      h('dl', { class: 'stats', 'aria-label': 'This run in numbers' }, ...tiles.map((t) => t.tile))),
    h('nav', { class: 'entries', 'aria-label': 'Start here' },
      entry('find', 'find', 'Find a room', 'Directions from the entrance you are at', north ? `?entrance=${encodeURIComponent(north.id)}` : ''),
      entry('mission', 'mission', 'Watch the mission', 'Replay how the robot built this map'),
      entry('results', 'results', 'See the results', 'Every objective, measured against its target')),
    skip,
    h('div', { class: 'scroll-cue', 'aria-hidden': 'true' }, h('span', {}), 'Scroll'));

  const beats = [
    { key: 'drive', n: '01', title: 'It drives itself.', text: `Starting at an entrance, the rover heads for whatever it has not seen yet. On this run it covered ${fmt(stats.metres_explored)} m in ${fmt((stats.duration_s ?? 0) / 60)} minutes, with no one steering.` },
    { key: 'scan', n: '02', title: 'It sees in laser light.', text: 'A spinning lidar measures the distance to every wall around it, many times a second. Joined together, the scans become a floor plan.' },
    { key: 'signs', n: '03', title: 'It reads the signs.', text: `A camera spots door plates and reads the room numbers. ${stats.signs_read} signs were read, each placed on the map where the robot saw it.` },
    { key: 'zones', n: '04', title: 'It learns which doors are locked.', text: `From each entrance it works out what can actually be reached. ${zoneRooms.map((z) => `${z.e.name}: ${z.n} rooms`).join(' · ')}. No visitor is ever sent to a locked door.` },
    { key: 'route', n: '05', title: 'Then it shows you the way.', text: 'Scan the QR poster at the entrance, pick your room, and follow the robot’s own photos of each junction.' },
  ];
  const story = h('section', { class: 'story', 'aria-label': 'How it works' },
    ...beats.map((b) => h('article', { class: 'beat', 'data-beat': b.key },
      h('div', { class: 'beat-card glass', 'data-reveal': true },
        h('p', { class: 'beat-n mono', text: b.n }),
        h('h2', { class: 'display-s', text: b.title }),
        h('p', { class: 'beat-text', text: b.text }),
        b.key === 'signs' ? signStrip(ctx) : null,
        b.key === 'route' ? h('a', { class: 'button primary', href: north ? `find?entrance=${north.id}` : 'find', 'data-link': true, icon: 'find' }, 'Find a room') : null))));
  const footer = h('footer', { class: 'site-footer' },
    h('p', {}, h('strong', { text: 'Merz Mapper' }), ' · final-year individual project, EEE3094. The robot is the project; this site shows what it recorded.'),
    h('p', { class: 'mono small muted', text: `Data: ${bundle.manifest.name}${bundle.manifest.sample ? ' (synthetic sample)' : ''}` }));
  root.append(hero, story, footer);
  reveal(root.querySelectorAll('[data-hero]'), 0.15, 0.12);
  reveal(root.querySelectorAll('.entry'), 0.9, 0.08);
  tiles.forEach((t, i) => countUp(t.number, t.value, t.digits, '', 1.0 + i * 0.12));
  revealOnScroll(story);

  // ---------------------------------------------------------------- the scene
  const scene = await ctx.scene();
  if (!scene) { document.body.classList.add('no-webgl'); return () => document.body.classList.remove('no-webgl'); }
  const data = await loadMission(bundle);
  const overlay = new Overlay(ctx.overlay, scene);
  const release = scene.hold();
  const timeline = gsap.timeline();
  let orbiting = true;
  const m = bundle.manifest.map;
  const box: [number, number][] = [[m.origin[0], m.origin[1]], [m.origin[0] + m.width * m.resolution, m.origin[1] + m.height * m.resolution]];
  scene.setRoute(null);
  scene.setGraph(null);
  scene.showEllipse(null);
  scene.setScan(null);
  scene.setRobot(null);
  scene.eyeBlend = 0;
  const duration = data?.mission.duration_s ?? 1;
  if (data) {
    scene.setCloud(data.cloud);
    scene.setTrail(data.mission.trajectory, 1e6, 0.85);
  }

  const finalState = () => {
    scene.setCloudState(duration, 0.22);
    scene.setTrailTime(duration);
    scene.setMapOpacity(1);
    scene.setReveal(999);
    scene.setWalls(true, 0);
  };
  const isNarrow = window.innerWidth < 760;
  // Frame the building on the right on wide screens, so the headline has the left.
  const frame = (tilt: number, az: number, ms: number) => scene.fit(box, { tilt, az, duration: ms, padding: isNarrow ? 10 : 60,
    offsetX: isNarrow ? 0 : -0.16, offsetY: isNarrow ? 0.1 : 0 });

  if (reducedMotion() || !data) {
    finalState();
    frame(0.95, -0.5, 0);
    skip.hidden = true;
  } else {
    scene.setMapOpacity(0);
    scene.setReveal(999);
    scene.setCloudState(0, 1);
    scene.setTrailTime(0);
    scene.setWalls(false, 0);
    frame(0.25, -0.15, 0);
    const p = { t: 0, map: 0, cloud: 1 };
    timeline
      .to(p, { t: duration, duration: 3.8, ease: 'power1.inOut', onUpdate: () => { scene.setCloudState(p.t, p.cloud); scene.setTrailTime(p.t); } }, 0.2)
      .to(p, { map: 1, duration: 1.6, ease: 'power2.out', onUpdate: () => scene.setMapOpacity(p.map) }, 2.9)
      .to(p, { cloud: 0.22, duration: 1.6, onUpdate: () => scene.setCloudState(p.t, p.cloud) }, 3.4)
      .call(() => { scene.setWalls(true, 1600); frame(0.95, -0.5, 2600); }, [], 3.9)
      .call(() => { skip.hidden = true; }, [], 6.4);
    skip.addEventListener('click', () => { timeline.progress(1); scene.stopTweens(); finalState(); frame(0.95, -0.5, 600); skip.hidden = true; });
  }
  // A slow orbit while the visitor reads the hero.
  const spin = scene.onFrame(() => {
    if (orbiting && !reducedMotion() && timeline.progress() >= 1 && window.scrollY < 40) scene.rig.az -= 0.0006;
  });

  // ---------------------------------------------------------------- scroll story drives the camera
  const pins: ReturnType<Overlay['add']>[] = [];
  const clearPins = () => { pins.splice(0).forEach((p) => overlay.remove(p)); };
  const traj = data?.mission.trajectory ?? [];
  const mid = traj[Math.floor(traj.length * 0.18)];
  const beatState: Record<string, () => void> = {
    drive: () => {
      clearPins(); scene.setGraph(null); scene.setRoute(null); scene.setScan(null);
      scene.setCloudState(duration, 0.12); scene.setTrail(data?.mission.trajectory ?? null, 1e6, 0.9); scene.setTrailTime(duration);
      if (mid) { scene.setRobot({ x: mid[1], y: mid[2], yaw: mid[3] }); }
      scene.fit(box, { tilt: 0.5, az: -0.2, duration: 1600, padding: isNarrow ? 10 : 80, offsetX: isNarrow ? 0 : 0.18 });
    },
    scan: () => {
      clearPins(); scene.setGraph(null); scene.setRoute(null);
      if (data && mid) {
        const i = Math.max(0, data.mission.scans.meta.findIndex((s) => s[0] >= mid[0]));
        const meta = data.mission.scans.meta[i];
        const rays = data.mission.scans.rays;
        scene.setRobot({ x: meta[1], y: meta[2], yaw: meta[3] });
        scene.setScan({ x: meta[1], y: meta[2], yaw: meta[3] }, data.scans.subarray(i * rays, (i + 1) * rays), meta[4], meta[5]);
        scene.setCloudState(duration, 0.5);
        scene.flyTo({ x: meta[1] - (isNarrow ? 0 : 6), y: meta[2] + (isNarrow ? -4 : 0), dist: 38, tilt: 0.7, az: -0.6 }, 1600);
      }
    },
    signs: () => {
      clearPins(); scene.setScan(null); scene.setRobot(null); scene.setCloudState(duration, 0.1);
      const signs = bundle.landmarks.filter((l) => l.class === 'room_sign' && l.text);
      signs.forEach((lm, i) => {
        const pin = overlay.add(landmarkPin(lm), lm.x, lm.y, 1.4);
        pin.el.style.setProperty('--delay', `${i * 40}ms`);
        pin.el.classList.add('pop');
        pins.push(pin);
      });
      scene.fit(signs.map((s) => [s.x, s.y] as [number, number]), { tilt: 0.55, az: -0.35, duration: 1600, padding: isNarrow ? 30 : 100, offsetX: isNarrow ? 0 : 0.18 });
    },
    zones: () => {
      clearPins(); scene.setRoute(null);
      const zone = bundle.graph.zones[north?.id ?? ''];
      const byId = new Map(bundle.graph.junctions.map((j) => [j.id, j]));
      const edges = bundle.graph.edges.filter(([a, b]) => zone?.junctions.includes(a) && zone.junctions.includes(b))
        .map(([a, b]) => [[byId.get(a)!.x, byId.get(a)!.y], [byId.get(b)!.x, byId.get(b)!.y]] as [number, number][]);
      scene.setGraph(edges);
      if (north) pins.push(overlay.add(youAreHere(north.name), north.x, north.y));
      scene.fit(box, { tilt: 0.15, az: 0, duration: 1600, padding: isNarrow ? 10 : 80, offsetX: isNarrow ? 0 : 0.18 });
    },
    route: () => {
      clearPins(); scene.setGraph(null);
      const routes = bundle.routes[north?.id ?? '']?.routes ?? {};
      const [room, route] = Object.entries(routes).sort((a, b) => b[1].length_m - a[1].length_m)[0] ?? [];
      if (!route || !north) return;
      const pts = scene.route2points(route, north);
      scene.setRoute(pts);
      scene.drawRoute(2200);
      pins.push(overlay.add(youAreHere(north.name), north.x, north.y), overlay.add(beacon(room), route.destination.x, route.destination.y));
      scene.fit(pts, { tilt: 0.8, az: -0.4, duration: 1600, padding: isNarrow ? 40 : 120, offsetX: isNarrow ? 0 : 0.18 });
    },
  };
  story.querySelectorAll<HTMLElement>('.beat').forEach((beat) => {
    ScrollTrigger.create({
      trigger: beat, start: 'top 55%', end: 'bottom 45%',
      onToggle: (self) => { if (self.isActive) { orbiting = false; timeline.progress(1); skip.hidden = true; finalState(); beatState[beat.dataset.beat!]?.(); } },
    });
  });
  ScrollTrigger.create({
    trigger: hero, start: 'top top', end: 'bottom 40%',
    onEnterBack: () => {
      orbiting = true; clearPins(); scene.setGraph(null); scene.setRoute(null); scene.setScan(null); scene.setRobot(null);
      if (data) { scene.setTrail(data.mission.trajectory, 1e6, 0.85); scene.setTrailTime(duration); }
      finalState(); frame(0.95, -0.5, 1400);
    },
  });

  const onTheme = () => scene.applyTheme();
  window.addEventListener('merz-theme', onTheme);
  return () => {
    timeline.kill();
    release();
    spin();
    overlay.destroy();
    window.removeEventListener('merz-theme', onTheme);
    scene.setCloudState(0, 0);
    scene.setTrail(null);
    scene.setRobot(null);
    scene.setScan(null);
    scene.setGraph(null);
    scene.setRoute(null);
  };
}

function signStrip(ctx: PageContext) {
  const signs = ctx.bundle.landmarks.filter((l) => l.photo).slice(0, 6);
  return h('div', { class: 'sign-strip', 'aria-hidden': 'true' }, ...signs.map((lm) =>
    h('figure', {}, h('img', { src: ctx.bundle.url(lm.photo!.thumb), alt: '', loading: 'lazy', width: 120, height: 76 }),
      h('figcaption', { class: 'mono', text: lm.text || '?' }))));
}


