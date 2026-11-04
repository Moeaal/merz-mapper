/* Merz Mapper demonstrator page. No framework and no build step, so it runs from the repository as it is.
   Everything that comes from the API is inserted with textContent, so text from the database can never run as code.
   Markup strings are inserted only for the fixed icons below. */
'use strict';

const ICONS = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 5-7 7 7 7"/></svg>',
  door: '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13 4h6v16h-6M4 12h10m-4-4 4 4-4 4"/></svg>',
  warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4m0 3v.5"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
  plug: '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 10v12m12-12v12M16 22h24v8a12 12 0 0 1-24 0v-8Zm12 20v8a6 6 0 0 0 6 6h6"/><path d="m44 12 10 10m0-10L44 22"/></svg>',
  retry: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  minus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M5 12h14"/></svg>',
  fit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>',
  straight: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 27V6m-8 8 8-8 8 8"/></svg>',
  left: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 27V15a4 4 0 0 0-4-4H6m6-6-6 6 6 6"/></svg>',
  right: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 27V15a4 4 0 0 1 4-4h11m-6-6 6 6-6 6"/></svg>',
  back_turn: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 27V13a6 6 0 0 0-12 0v8m-5-5 5 5 5-5"/></svg>',
  arrive: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 28V5m0 1h15l-4 5 4 5H9"/></svg>',
  pin: '<svg viewBox="0 0 34 42" aria-hidden="true"><path d="M17 41S2 25.5 2 16a15 15 0 0 1 30 0c0 9.5-15 25-15 25Z" fill="var(--dest)" stroke="var(--map-floor)" stroke-width="2.5"/><circle cx="17" cy="16" r="6" fill="#fff"/></svg>',
};

const view = document.getElementById('view');
const announcer = document.getElementById('announcer');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const state = { entrances: null, sample: false, mapInfo: undefined, cleanup: null };

/* ------------------------------------------------------------------ small helpers */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'icon') node.insertAdjacentHTML('afterbegin', ICONS[value]);
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children) if (child !== null && child !== undefined && child !== false) node.append(child);
  return node;
}

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function announce(text) {
  announcer.textContent = '';
  window.setTimeout(() => { announcer.textContent = text; }, 30);
}

function show(...nodes) {
  if (state.cleanup) { state.cleanup(); state.cleanup = null; }
  view.classList.remove('wide');
  view.replaceChildren(...nodes);
  const heading = view.querySelector('h1');
  if (heading) {
    heading.tabIndex = -1;
    // Only move focus after a visitor's own action, so a screen reader starts at the new heading.
    if (show.userInitiated) heading.focus({ preventScroll: true });
  }
  window.scrollTo({ top: 0 });
}
show.userInitiated = false;

function metres(value) {
  return value < 1 ? 'less than 1 m' : `about ${Math.round(value)} m`;
}

/* ------------------------------------------------------------------ API */
class ServerUnreachable extends Error {}

async function getJson(url) {
  let response;
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } });
  } catch (_error) {
    throw new ServerUnreachable('The server could not be reached.');
  }
  let body = null;
  try { body = await response.json(); } catch (_error) { /* not JSON: a proxy or crashed server */ }
  if (response.status >= 500 || body === null) throw new ServerUnreachable(`The server answered ${response.status}.`);
  if (!response.ok) {
    const error = new Error(body.detail || 'Something went wrong. Please try again.');
    error.status = response.status;
    throw error;
  }
  return body;
}

/* ------------------------------------------------------------------ navigation */
function params() {
  const search = new URLSearchParams(location.search);
  return { entrance: search.get('entrance'), room: search.get('room') };
}

function navigate(next) {
  const search = new URLSearchParams();
  if (next.entrance) search.set('entrance', next.entrance);
  if (next.room) search.set('room', next.room);
  const url = search.toString() ? `/?${search}` : '/';
  history.pushState(null, '', url);
  show.userInitiated = true;
  render();
}

window.addEventListener('popstate', () => { show.userInitiated = true; render(); });

async function render() {
  try {
    if (!state.entrances) {
      const data = await getJson('/entrances');
      state.entrances = data.entrances;
      state.sample = data.sample_data;
      document.getElementById('sample').hidden = !state.sample;
    }
    const { entrance, room } = params();
    if (!entrance) return showEntrances();
    const found = state.entrances.find((e) => e.id === entrance);
    if (!found) return showEntrances(entrance);
    if (!room) return await showRooms(found);
    return await showRoute(found, room);
  } catch (error) {
    if (error instanceof ServerUnreachable) return showServerDown();
    return show(message('error', 'Something went wrong', [error.message]), el('a', { class: 'button', href: '/', text: 'Start again' }));
  }
}

/* ------------------------------------------------------------------ shared pieces */
function message(kind, title, lines, icon = 'warn') {
  return el('div', { class: `message ${kind}`, role: kind === 'error' ? 'alert' : 'status', icon },
    el('div', {}, el('h2', { text: title }), ...lines.map((line) => el('p', { text: line }))));
}

function hereSign(entrance, withChange = true) {
  return el('div', { class: 'here-sign' },
    el('span', { class: 'glyph', icon: 'door' }),
    el('div', {}, el('p', { class: 'label', text: 'You are here' }), el('p', { class: 'name', text: entrance.name })),
    withChange ? el('button', { class: 'change', type: 'button', text: 'Change', 'aria-label': 'Change entrance',
                                onclick: () => navigate({}) }) : null);
}

function entranceList() {
  return el('ul', { class: 'entrance-list' }, ...state.entrances.map((entrance) => el('li', {},
    el('button', { class: 'entrance-button', type: 'button', onclick: () => navigate({ entrance: entrance.id }) },
      el('span', { class: 'square', icon: 'door' }), el('span', { text: entrance.name })))));
}

/* ------------------------------------------------------------------ screens */
function showServerDown() {
  show(el('section', { class: 'server-down', 'aria-labelledby': 'down-title' },
    el('div', { class: 'icon', icon: 'plug' }),
    el('h1', { id: 'down-title', text: 'Cannot reach the Merz Mapper server' }),
    el('p', { text: 'The directions come from a small server run for the demonstration, and it is not answering right now.' }),
    el('p', { text: 'Check that your phone is on the building Wi-Fi, then try again. If it still fails, the server may be switched off.' }),
    el('div', { class: 'button-row', style: 'justify-content:center' },
      el('button', { class: 'button', type: 'button', icon: 'retry', onclick: () => { show.userInitiated = true; render(); } },
        'Try again'))));
}

function showEntrances(unknownId) {
  const parts = [];
  if (unknownId) {
    parts.push(message('error', 'We do not recognise this QR code',
      [`It points to an entrance called "${unknownId}", which is not on the robot's map.`,
        'Please choose the entrance you are standing at.']));
  }
  parts.push(el('p', { class: 'eyebrow', text: 'Step 1 of 2' }), el('h1', { class: 'page-title', text: 'Which entrance are you at?' }),
    el('p', { class: 'lede', text: 'Each entrance has a poster with a QR code. Scanning it skips this step.' }), entranceList());
  show(...parts);
}

async function showRooms(entrance) {
  const { rooms } = await getJson(`/rooms?entrance=${encodeURIComponent(entrance.id)}`);
  const input = el('input', { id: 'room-search', type: 'search', inputmode: 'search', autocomplete: 'off',
                              spellcheck: 'false', placeholder: 'For example S1.04', 'aria-describedby': 'room-count' });
  const count = el('p', { id: 'room-count', class: 'count', 'aria-live': 'polite' });
  const results = el('div');

  const tile = (room, term) => {
    const num = el('span', { class: 'num' });
    const at = term ? room.toUpperCase().indexOf(term) : -1;
    if (at >= 0) num.append(room.slice(0, at), el('mark', { text: room.slice(at, at + term.length) }), room.slice(at + term.length));
    else num.textContent = room;
    return el('li', {}, el('button', { class: 'room-tile', type: 'button', 'aria-label': `Room ${room}`,
                                       onclick: () => navigate({ entrance: entrance.id, room }) },
      num, el('span', { class: 'go', icon: 'chevron' })));
  };

  const draw = () => {
    const term = input.value.trim().toUpperCase();
    const matching = rooms.filter((room) => room.toUpperCase().includes(term));
    if (!rooms.length) {
      count.textContent = '';
      results.replaceChildren(el('p', { class: 'empty', text: 'The robot has not recorded any rooms that can be reached from this entrance yet.' }));
      return;
    }
    count.textContent = term
      ? `${matching.length} of ${rooms.length} rooms match`
      : `${rooms.length} rooms can be reached from here`;
    results.replaceChildren(matching.length
      ? el('ul', { class: 'room-grid' }, ...matching.map((room) => tile(room, term)))
      : el('div', { class: 'empty' },
        el('p', {}, 'No room matching ', el('strong', { text: `"${input.value.trim()}"` }), ' can be reached from this entrance.'),
        el('p', { text: 'Rooms behind locked doors are not listed. Try another entrance, or check the number on your booking.' })));
  };
  input.addEventListener('input', draw);
  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    const first = results.querySelector('.room-tile');
    if (first) first.click();
  });
  draw();
  show(hereSign(entrance),
    el('p', { class: 'eyebrow', text: 'Step 2 of 2' }),
    el('h1', { class: 'page-title', text: 'Where would you like to go?' }),
    el('label', { class: 'field-label', for: 'room-search', text: 'Room number' }),
    el('div', { class: 'search', icon: 'search' }, input), count, results);
}

async function showRoute(entrance, room) {
  let route;
  try {
    route = await getJson(`/route?entrance=${encodeURIComponent(entrance.id)}&room=${encodeURIComponent(room)}`);
  } catch (error) {
    if (error instanceof ServerUnreachable || error.status !== 404) throw error;
    return show(hereSign(entrance),
      message('error', `Room ${room} cannot be reached from here`, [
        'It may be behind a locked door, or the robot may not have seen its sign. Only rooms that can be reached from this entrance are listed.',
      ]),
      el('div', { class: 'button-row' },
        el('button', { class: 'button', type: 'button', onclick: () => navigate({ entrance: entrance.id }) }, 'Choose a room from the list'),
        el('button', { class: 'button secondary', type: 'button', onclick: () => navigate({}) }, 'Choose another entrance')));
  }
  if (state.mapInfo === undefined) {
    try { state.mapInfo = await getJson('/map'); } catch (_error) { state.mapInfo = { available: false }; }
  }
  const steps = route.steps;
  const total = steps.length;

  /* ---- header */
  const head = el('div', { class: 'route-head' },
    el('div', {},
      el('p', { class: 'eyebrow', text: `From ${route.start.name}` }),
      el('h1', {}, el('span', { class: 'to', text: 'To ' }), `room ${route.room}`),
      el('ul', { class: 'route-facts', 'aria-label': 'Route summary' },
        el('li', { text: `${metres(route.length_m)} walk` }),
        el('li', { text: `${total} ${total === 1 ? 'junction' : 'junctions'}` }),
        el('li', { text: `About ${Math.max(1, Math.round(route.length_m / 70))} min` }))),
    el('button', { class: 'back-link', type: 'button', icon: 'back', onclick: () => navigate({ entrance: entrance.id }) }, 'Choose another room'));

  /* ---- step cards */
  const position = el('span', { class: 'of' });
  const prev = el('button', { type: 'button', icon: 'back', 'aria-label': 'Previous step' });
  const next = el('button', { type: 'button', icon: 'chevron', 'aria-label': 'Next step' });
  const track = el('ol', { class: 'track', tabindex: '0', 'aria-label': 'Photo directions. Use the left and right arrow keys to move between steps.' });
  const stepper = el('ol', { class: 'stepper', 'aria-label': 'Jump to a step' });

  steps.forEach((step, index) => {
    const last = index === total - 1;
    const kind = turnKind(step.instruction, last);
    const photo = el('div', { class: 'photo' });
    if (step.photo_url) {
      const img = el('img', { src: step.photo_url, alt: `Step ${index + 1}: the view the rover photographed at this junction`,
                              loading: index < 2 ? 'eager' : 'lazy', decoding: 'async', draggable: 'false' });
      img.addEventListener('error', () => img.replaceWith(el('p', { class: 'missing', text: 'The photo for this junction is missing.' })));
      photo.append(img);
    } else {
      photo.append(el('p', { class: 'missing', text: 'No photo was taken at this junction.' }));
    }
    photo.append(el('span', { class: 'badge', 'aria-hidden': 'true', text: String(index + 1) }));
    const from = index === 0 ? `from ${route.start.name.toLowerCase()}` : 'from the last junction';
    track.append(el('li', { class: 'slide', 'aria-roledescription': 'slide', 'aria-label': `Step ${index + 1} of ${total}` },
      el('article', { class: `card${last ? ' arrive' : ''}` }, photo,
        el('div', { class: 'body' },
          el('span', { class: 'turn', icon: kind }),
          el('div', {},
            el('p', { class: 'instruction', text: step.instruction }),
            el('p', { class: 'meta', text: `${metres(step.distance_m)[0].toUpperCase()}${metres(step.distance_m).slice(1)} ${from}.` }))))));
    stepper.append(el('li', {}, el('button', { type: 'button', 'aria-label': `Step ${index + 1}: ${step.instruction}`,
                                               onclick: () => go(index, 'stepper') },
      el('span', { class: 'n', 'aria-hidden': 'true', text: String(index + 1) }),
      el('span', { class: 't', 'aria-hidden': 'true' }, step.instruction, el('small', { text: `${metres(step.distance_m)} ${from}` })))));
  });

  const stepsPanel = el('section', { class: 'steps-panel', 'aria-roledescription': 'carousel', 'aria-labelledby': 'steps-title' },
    el('div', { class: 'steps-bar' },
      el('h2', { id: 'steps-title' }, 'Step ', position),
      el('div', { class: 'step-nav' }, prev, next)),
    track,
    el('p', { class: 'swipe-hint', text: 'Swipe the photo, or tap a number, to move between steps.' }),
    stepper);

  /* ---- map */
  const mapPanel = el('section', { class: 'map-panel', 'aria-label': 'Map' });
  const map = createRouteMap(mapPanel, route, state.mapInfo, (index) => go(index, 'map'));

  /* ---- wiring */
  let current = -1;
  function go(index, source) {
    index = Math.max(0, Math.min(total - 1, index));
    if (index === current && source !== 'stepper') return;
    current = index;
    position.textContent = `${index + 1} `;
    position.append(el('span', { class: 'of', text: `of ${total}` }));
    prev.disabled = index === 0;
    next.disabled = index === total - 1;
    stepper.querySelectorAll('button').forEach((button, i) => {
      if (i === index) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
    });
    if (source !== 'track') {
      track.scrollTo({ left: index * track.clientWidth, behavior: reducedMotion.matches || source === 'init' ? 'auto' : 'smooth' });
    }
    // On arrival the whole route is shown; after that the map follows the chosen step.
    map.setStep(index, source !== 'init', source !== 'init');
    if (source !== 'init') announce(`Step ${index + 1} of ${total}. ${steps[index].instruction}`);
  }
  prev.addEventListener('click', () => go(current - 1, 'button'));
  next.addEventListener('click', () => go(current + 1, 'button'));
  track.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight') { event.preventDefault(); go(current + 1, 'button'); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); go(current - 1, 'button'); }
  });
  let scrollTimer = 0;
  const settle = () => {
    const index = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
    if (index !== current) go(index, 'track');
  };
  track.addEventListener('scroll', () => { window.clearTimeout(scrollTimer); scrollTimer = window.setTimeout(settle, 90); }, { passive: true });

  const footer = el('div', { class: 'route-footer' },
    el('button', { class: 'button secondary', type: 'button', icon: 'back', onclick: () => navigate({ entrance: entrance.id }) }, 'Choose another room'),
    el('a', { class: 'button secondary', href: '/about' }, 'How the robot made this map'));

  show(head, el('div', { class: 'route-layout' }, mapPanel, el('div', {}, stepsPanel, footer)));
  view.classList.add('wide');
  state.cleanup = map.destroy;
  map.start();
  go(0, 'init');
}

function turnKind(instruction, last) {
  if (last) return 'arrive';
  const text = instruction.toLowerCase();
  if (text.includes('left')) return 'left';
  if (text.includes('right')) return 'right';
  if (text.includes('around')) return 'back_turn';
  return 'straight';
}

/* ------------------------------------------------------------------ the map
   World coordinates are metres in the robot's map frame (x right, y up). The SVG uses (x, -y) so that north is up,
   and pan/zoom changes its viewBox. Markers are HTML on top, so they stay the same size and remain real buttons. */
function createRouteMap(panel, route, mapInfo, onPick) {
  const hasMap = Boolean(mapInfo && mapInfo.available);
  const points = [[route.start.x, route.start.y], ...route.steps.map((s) => [s.x, s.y]), [route.destination.x, route.destination.y]];
  const box = el('div', { class: 'map', tabindex: '0', role: 'group', 'aria-roledescription': 'map',
                          'aria-label': `Map of the route from ${route.start.name} to room ${route.room}. Drag or use the arrow keys to move, plus and minus to zoom.` });
  const svg = svgEl('svg', { class: 'world', 'aria-hidden': 'true', focusable: 'false' });
  const defs = svgEl('defs');
  // Recolour the robot's map image to the current theme (walls and floor), keeping unknown space transparent.
  const filter = svgEl('filter', { id: 'map-tone', 'color-interpolation-filters': 'sRGB', x: '0', y: '0', width: '1', height: '1' });
  const transfer = svgEl('feComponentTransfer');
  const funcs = ['R', 'G', 'B'].map((channel) => { const f = svgEl(`feFunc${channel}`, { type: 'discrete' }); transfer.append(f); return f; });
  filter.append(transfer);
  defs.append(filter);
  svg.append(defs);
  if (hasMap) {
    const widthM = mapInfo.width * mapInfo.resolution;
    const heightM = mapInfo.height * mapInfo.resolution;
    svg.append(svgEl('image', { class: 'grid-image', href: mapInfo.image_url, x: mapInfo.origin[0],
                                y: -(mapInfo.origin[1] + heightM), width: widthM, height: heightM,
                                preserveAspectRatio: 'none', filter: 'url(#map-tone)' }));
  }
  const pointsAttr = points.map(([x, y]) => `${x},${-y}`).join(' ');
  const casing = svgEl('polyline', { class: 'route-casing', points: pointsAttr, 'vector-effect': 'non-scaling-stroke' });
  const line = svgEl('polyline', { class: 'route-line', points: pointsAttr, 'vector-effect': 'non-scaling-stroke' });
  const legCasing = svgEl('polyline', { class: 'route-leg-casing', 'vector-effect': 'non-scaling-stroke' });
  const leg = svgEl('polyline', { class: 'route-leg', 'vector-effect': 'non-scaling-stroke' });
  svg.append(casing, legCasing, line, leg);

  const overlay = el('div', { class: 'overlay' });
  const markers = [];
  const place = (node, x, y, label = null) => { markers.push({ node, x, y, label }); overlay.append(node); return node; };
  place(el('div', { class: 'marker entrance-marker', icon: 'door' }), route.start.x, route.start.y);
  place(el('div', { class: 'marker map-label', text: route.start.name }), route.start.x, route.start.y, { dx: -20, dy: 18 });
  place(el('div', { class: 'marker dest-marker', icon: 'pin' }), route.destination.x, route.destination.y);
  place(el('div', { class: 'marker map-label', text: route.room }), route.destination.x, route.destination.y, { dx: 20, dy: -36 });
  const stepButtons = route.steps.map((step, index) => place(
    el('button', { class: 'marker step-marker', type: 'button', tabindex: '-1', 'aria-hidden': 'true', text: String(index + 1),
                   onclick: () => onPick(index) }), step.x, step.y));

  const zoomIn = el('button', { type: 'button', icon: 'plus', 'aria-label': 'Zoom in' });
  const zoomOut = el('button', { type: 'button', icon: 'minus', 'aria-label': 'Zoom out' });
  const fitAll = el('button', { type: 'button', icon: 'fit', 'aria-label': 'Show the whole route' });
  const scaleBar = el('div', { class: 'map-scale', 'aria-hidden': 'true' });
  box.append(svg, overlay, el('div', { class: 'map-controls' }, zoomIn, zoomOut, fitAll), scaleBar);
  if (!hasMap) box.append(el('p', { class: 'map-note', text: 'The building map is not available, so only the route is drawn.' }));

  const legend = el('ul', { class: 'legend', 'aria-label': 'Map key' },
    el('li', {}, el('span', { class: 'sw sw-route' }), 'Your route'),
    el('li', {}, el('span', { class: 'sw sw-entrance' }), 'Entrance'),
    el('li', {}, el('span', { class: 'sw sw-dest' }), `Room ${route.room}`),
    el('li', {}, el('span', { class: 'sw sw-step' }), 'Junction photo'),
    el('li', {}, el('span', { class: 'sw sw-current' }), 'Current step'),
    hasMap ? el('li', {}, el('span', { class: 'sw sw-wall' }), 'Walls and floor') : null,
    hasMap ? el('li', {}, el('span', { class: 'sw sw-unknown' }), 'Not surveyed') : null);
  panel.append(box, legend);

  /* ---- view state: centre (metres) and scale (pixels per metre) */
  const view = { cx: 0, cy: 0, s: 10 };
  let size = { w: 1, h: 1 };
  let limits = { min: 1, max: 40 };
  let animation = 0;

  function applyTheme() {
    const style = getComputedStyle(document.documentElement);
    const rgb = (name) => {
      const probe = document.createElement('span');
      probe.style.color = style.getPropertyValue(name);
      document.body.append(probe);
      const parts = getComputedStyle(probe).color.match(/[\d.]+/g).map(Number);
      probe.remove();
      return parts;
    };
    const wall = rgb('--map-wall');
    const floor = rgb('--map-floor');
    funcs.forEach((f, i) => f.setAttribute('tableValues', `${(wall[i] / 255).toFixed(3)} ${(floor[i] / 255).toFixed(3)}`));
  }

  function draw() {
    const { w, h } = size;
    svg.setAttribute('viewBox', `${view.cx - w / 2 / view.s} ${-view.cy - h / 2 / view.s} ${w / view.s} ${h / view.s}`);
    for (const m of markers) {
      let left = (m.x - view.cx) * view.s + w / 2;
      let top = (view.cy - m.y) * view.s + h / 2;
      if (m.label) {
        // Labels sit beside their marker, but slide back inside the map edge rather than being cut off.
        // A label whose marker is off the map is hidden, so it never points at the wrong place.
        m.node.hidden = left < -10 || left > w + 10 || top < -10 || top > h + 10;
        const width = m.node.offsetWidth;
        left = Math.min(Math.max(left + m.label.dx, 6), w - width - 6);
        top += m.label.dy;
      }
      m.node.style.transform = `translate(${left.toFixed(1)}px, ${top.toFixed(1)}px)`;
    }
    // Scale bar: the largest round length that fits in about 90 px.
    const target = 90 / view.s;
    const nice = [1, 2, 5, 10, 20, 50, 100].reduce((best, n) => (n <= target ? n : best), 1);
    scaleBar.textContent = `${nice} m`;
    scaleBar.append(el('span', { class: 'bar', style: `width:${nice * view.s}px` }));
  }

  function bounds(list, padMetres) {
    const xs = list.map((p) => p[0]);
    const ys = list.map((p) => p[1]);
    return { x0: Math.min(...xs) - padMetres, x1: Math.max(...xs) + padMetres, y0: Math.min(...ys) - padMetres, y1: Math.max(...ys) + padMetres };
  }

  function target(b) {
    const s = Math.min(size.w / Math.max(1, b.x1 - b.x0), size.h / Math.max(1, b.y1 - b.y0));
    return { cx: (b.x0 + b.x1) / 2, cy: (b.y0 + b.y1) / 2, s: clamp(s) };
  }

  function clamp(s) { return Math.max(limits.min, Math.min(limits.max, s)); }

  function flyTo(goal, animate) {
    window.cancelAnimationFrame(animation);
    if (!animate || reducedMotion.matches) { Object.assign(view, goal); draw(); return; }
    const from = { ...view };
    const started = performance.now();
    const duration = 420;
    const tick = (now) => {
      const t = Math.min(1, (now - started) / duration);
      const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
      // Interpolate the zoom in log space, so zooming feels even.
      view.s = Math.exp(Math.log(from.s) + (Math.log(goal.s) - Math.log(from.s)) * e);
      view.cx = from.cx + (goal.cx - from.cx) * e;
      view.cy = from.cy + (goal.cy - from.cy) * e;
      draw();
      if (t < 1) animation = window.requestAnimationFrame(tick);
    };
    animation = window.requestAnimationFrame(tick);
  }

  function zoomAt(px, py, factor) {
    window.cancelAnimationFrame(animation);
    const wx = view.cx + (px - size.w / 2) / view.s;
    const wy = view.cy - (py - size.h / 2) / view.s;
    view.s = clamp(view.s * factor);
    view.cx = wx - (px - size.w / 2) / view.s;
    view.cy = wy + (py - size.h / 2) / view.s;
    draw();
  }

  function pan(dx, dy) {
    window.cancelAnimationFrame(animation);
    view.cx -= dx / view.s;
    view.cy += dy / view.s;
    draw();
  }

  function setStep(index, animate, frame) {
    stepButtons.forEach((button, i) => button.classList.toggle('current', i === index));
    // Highlight the leg walked to reach this junction, and frame it with the next one for context.
    const legPoints = [points[index], points[index + 1]];
    leg.setAttribute('points', legPoints.map(([x, y]) => `${x},${-y}`).join(' '));
    legCasing.setAttribute('points', leg.getAttribute('points'));
    if (frame) flyTo(target(bounds([points[index], points[index + 1], points[index + 2]], 6)), animate);
  }

  function fitRoute(animate) { flyTo(target(bounds(points, 3)), animate); }

  function resize() {
    const rect = box.getBoundingClientRect();
    size = { w: Math.max(1, rect.width), h: Math.max(1, rect.height) };
    const whole = hasMap ? { x0: mapInfo.origin[0], y0: mapInfo.origin[1], x1: mapInfo.origin[0] + mapInfo.width * mapInfo.resolution,
                             y1: mapInfo.origin[1] + mapInfo.height * mapInfo.resolution } : bounds(points, 10);
    limits = { min: 1, max: 40 };
    limits.min = Math.min(target(whole).s * 0.8, 6);
    draw();
  }

  /* ---- pointer: one finger pans, two fingers pinch; wheel zooms at the cursor */
  const pointers = new Map();
  let pinch = null;
  box.addEventListener('pointerdown', (event) => {
    if (event.target.closest('button')) return;
    box.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    box.classList.add('dragging');
    pinch = null;
  });
  box.addEventListener('pointermove', (event) => {
    const last = pointers.get(event.pointerId);
    if (!last) return;
    const nowPoint = { x: event.clientX, y: event.clientY };
    if (pointers.size === 1) {
      pan(nowPoint.x - last.x, nowPoint.y - last.y);
    } else if (pointers.size === 2) {
      pointers.set(event.pointerId, nowPoint);
      const [a, b] = [...pointers.values()];
      const rect = box.getBoundingClientRect();
      const mid = { x: (a.x + b.x) / 2 - rect.left, y: (a.y + b.y) / 2 - rect.top };
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch) {
        pan(mid.x - pinch.mid.x, mid.y - pinch.mid.y);
        zoomAt(mid.x, mid.y, distance / pinch.distance);
      }
      pinch = { mid, distance };
      return;
    }
    pointers.set(event.pointerId, nowPoint);
  });
  const release = (event) => {
    pointers.delete(event.pointerId);
    pinch = null;
    if (!pointers.size) box.classList.remove('dragging');
  };
  box.addEventListener('pointerup', release);
  box.addEventListener('pointercancel', release);
  box.addEventListener('wheel', (event) => {
    event.preventDefault();
    const rect = box.getBoundingClientRect();
    zoomAt(event.clientX - rect.left, event.clientY - rect.top, Math.exp(-event.deltaY * (event.deltaMode ? 0.05 : 0.0015)));
  }, { passive: false });
  box.addEventListener('dblclick', (event) => {
    if (event.target.closest('button')) return;
    const rect = box.getBoundingClientRect();
    zoomAt(event.clientX - rect.left, event.clientY - rect.top, 1.6);
  });
  box.addEventListener('keydown', (event) => {
    const step = 60;
    const keys = {
      ArrowLeft: () => pan(step, 0), ArrowRight: () => pan(-step, 0), ArrowUp: () => pan(0, step), ArrowDown: () => pan(0, -step),
      '+': () => zoomAt(size.w / 2, size.h / 2, 1.4), '=': () => zoomAt(size.w / 2, size.h / 2, 1.4),
      '-': () => zoomAt(size.w / 2, size.h / 2, 1 / 1.4), 0: () => fitRoute(true),
    };
    if (event.target !== box || !keys[event.key]) return;
    event.preventDefault();
    keys[event.key]();
  });
  zoomIn.addEventListener('click', () => zoomAt(size.w / 2, size.h / 2, 1.5));
  zoomOut.addEventListener('click', () => zoomAt(size.w / 2, size.h / 2, 1 / 1.5));
  fitAll.addEventListener('click', () => fitRoute(true));

  const observer = new ResizeObserver(() => { resize(); });
  const themeQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const onTheme = () => applyTheme();

  return {
    start() {
      observer.observe(box);
      themeQuery.addEventListener('change', onTheme);
      applyTheme();
      resize();
      fitRoute(false);
    },
    setStep(index, animate, frame = true) {
      if (size.w <= 1) resize();
      setStep(index, animate, frame);
    },
    destroy() {
      observer.disconnect();
      themeQuery.removeEventListener('change', onTheme);
      window.cancelAnimationFrame(animation);
    },
  };
}

render();
