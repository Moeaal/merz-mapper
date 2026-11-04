import type { PageContext } from '../main';
import { h } from '../ui/dom';
import { reveal } from '../ui/motion';

// The 404 page: the robot at the edge of what it has mapped, scanning into the unknown.
export default function notFound(ctx: PageContext) {
  const north = ctx.bundle.graph.entrances[0];
  const visual = h('div', { class: 'lost-visual', 'aria-hidden': 'true' });
  visual.innerHTML = `<svg viewBox="0 0 400 260">
      <defs><radialGradient id="lostScan" cx="0" cy="0.5" r="1"><stop offset="0" stop-color="var(--accent)" stop-opacity=".45"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></radialGradient></defs>
      <g class="lost-dots">${Array.from({ length: 13 * 8 }, (_, i) => `<circle cx="${20 + (i % 13) * 30}" cy="${20 + Math.floor(i / 13) * 30}" r="1.6"/>`).join('')}</g>
      <path class="lost-wall" d="M20 200 H150 V120 H40"/>
      <g class="lost-sweep"><path d="M150 160 L380 70 A240 240 0 0 1 380 250 Z" fill="url(#lostScan)"/></g>
      <path class="lost-robot" d="M170 160 l-26 -14 6 14 -6 14z"/>
    </svg>`;
  ctx.root.append(h('section', { class: 'lost' }, visual,
    h('p', { class: 'eyebrow accent', text: 'Error 404 · unexplored space' }),
    h('h1', { class: 'display lost-title', text: 'Off the map.' }),
    h('p', { class: 'lede', text: 'This page is outside the area the robot has mapped. It has gone looking, but there is nothing here yet.' }),
    h('div', { class: 'lost-actions' },
      h('a', { class: 'button primary', href: './', 'data-link': true, text: 'Back to the start' }),
      h('a', { class: 'button', href: north ? `find?entrance=${north.id}` : 'find', 'data-link': true, text: 'Find a room' }))));
  reveal(ctx.root.querySelectorAll('.lost > *'), 0.05, 0.08);
  ctx.scene().then((scene) => {
    if (!scene) return;
    scene.setRoute(null); scene.setTrail(null); scene.setRobot(null); scene.setScan(null); scene.setGraph(null);
    scene.setWalls(false, 600);
    scene.overview(0.3, 1600, 0.2);
    scene.setMapOpacity(0.25);
  });
  return () => { ctx.scene().then((scene) => scene?.setMapOpacity(1)); };
}
