import '@fontsource-variable/archivo/standard.css';
import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import './styles/tokens.css';
import './styles/base.css';
import './styles/pages.css';
import { loadBundle, Unreachable, type Bundle } from './data';
import { getScene } from './scene/stage';
import type { MapScene } from './scene/MapScene';
import { h, icon, announce } from './ui/dom';
import { gsap, killScroll } from './ui/motion';

export interface PageContext {
  bundle: Bundle;
  root: HTMLElement;
  overlay: HTMLElement;
  params: URLSearchParams;
  scene: () => Promise<MapScene | null>;
  navigate: (path: string, params?: Record<string, string>, replace?: boolean) => void;
}
export type Cleanup = () => void;
type PageModule = { default: (ctx: PageContext) => Promise<Cleanup | void> | Cleanup | void };

const PAGES: Record<string, { load: () => Promise<PageModule>; title: string; nav?: string }> = {
  home: { load: () => import('./pages/home'), title: 'The building, as the robot saw it', nav: '' },
  find: { load: () => import('./pages/find'), title: 'Find a room', nav: 'find' },
  mission: { load: () => import('./pages/mission'), title: 'Mission replay', nav: 'mission' },
  results: { load: () => import('./pages/results'), title: 'Results', nav: 'results' },
  about: { load: () => import('./pages/about'), title: 'About the rover', nav: 'about' },
  notfound: { load: () => import('./pages/notfound'), title: 'Off the map' },
};

const app = document.getElementById('app')!;
const overlay = document.getElementById('overlay')!;
const basePath = new URL(document.baseURI).pathname;
let cleanup: Cleanup | void;
let renderToken = 0;

function route(): { page: keyof typeof PAGES; params: URLSearchParams } {
  const url = new URL(location.href);
  const path = url.pathname.startsWith(basePath) ? url.pathname.slice(basePath.length) : url.pathname.replace(/^\//, '');
  const clean = path.replace(/\/$/, '').replace(/index\.html$/, '');
  const params = url.searchParams;
  if (clean === '') return { page: params.has('entrance') ? 'find' : 'home', params };
  if (clean in PAGES && clean !== 'notfound' && clean !== 'home') return { page: clean as keyof typeof PAGES, params };
  return { page: 'notfound', params };
}

export function navigate(path: string, params: Record<string, string> = {}, replace = false) {
  const url = new URL(path.replace(/^\//, ''), document.baseURI);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  if (url.href === location.href) return;
  history[replace ? 'replaceState' : 'pushState'](null, '', url);
  render(true);
}

document.addEventListener('click', (e) => {
  const link = (e.target as HTMLElement).closest('a[data-link]') as HTMLAnchorElement | null;
  if (!link || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
  e.preventDefault();
  const url = new URL(link.href);
  navigate(url.pathname.slice(basePath.length) + url.search);
});
window.addEventListener('popstate', () => render(true));

// ------------------------------------------------------------------ shell
function themeToggle() {
  const button = h('button', { class: 'icon-button theme-toggle', type: 'button' });
  const paint = () => {
    const dark = document.documentElement.dataset.theme !== 'light';
    button.replaceChildren(icon(dark ? 'sun' : 'moon'));
    button.setAttribute('aria-label', dark ? 'Switch to the light blueprint theme' : 'Switch to the dark theme');
  };
  button.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    document.documentElement.classList.add('theme-fade');
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('merz-theme', next); } catch { /* storage blocked */ }
    document.querySelector('meta[name=theme-color]')?.setAttribute('content', next === 'light' ? '#f3f0e6' : '#05080f');
    window.dispatchEvent(new Event('merz-theme'));
    setTimeout(() => document.documentElement.classList.remove('theme-fade'), 500);
    paint();
  });
  paint();
  return button;
}

let header: HTMLElement | null = null;
function shell(bundle: Bundle | null) {
  if (header) return header;
  const links = [['find', 'Find a room'], ['mission', 'Mission'], ['results', 'Results'], ['about', 'About']];
  const nav = h('nav', { class: 'site-nav', 'aria-label': 'Main' },
    ...links.map(([href, label]) => h('a', { href, 'data-link': true, 'data-nav': href, text: label })));
  const menu = h('button', { class: 'icon-button menu-button', type: 'button', 'aria-label': 'Open menu',
    'aria-expanded': 'false', 'aria-controls': 'site-nav' }, icon('menu'));
  nav.id = 'site-nav';
  menu.addEventListener('click', () => {
    const open = !header!.classList.contains('menu-open');
    header!.classList.toggle('menu-open', open);
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  });
  nav.addEventListener('click', () => { header!.classList.remove('menu-open'); menu.setAttribute('aria-expanded', 'false'); });
  header = h('header', { class: 'site-header' },
    h('a', { class: 'brand', href: './', 'data-link': true, 'aria-label': 'Merz Mapper home' },
      h('span', { class: 'brand-mark', icon: 'logo' }), h('span', { class: 'brand-name', text: 'Merz Mapper' })),
    bundle?.manifest.sample ? h('span', { class: 'sample-badge', title: 'Made-up data until the rover surveys Merz Court' },
      h('span', { class: 'dot', 'aria-hidden': 'true' }), 'Sample data') : null,
    nav, h('div', { class: 'header-tools' }, themeToggle(), menu));
  document.body.insertBefore(header, app);
  return header;
}

function markNav(page: string) {
  header?.querySelectorAll('[data-nav]').forEach((a) => {
    if ((a as HTMLElement).dataset.nav === PAGES[page]?.nav) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
}

function serverDown(error: unknown) {
  shell(null);
  document.body.dataset.page = 'down';
  const retry = h('button', { class: 'button primary', type: 'button', icon: 'retry' }, 'Try again');
  retry.addEventListener('click', () => { retry.disabled = true; boot(); });
  app.replaceChildren(h('main', { id: 'main', class: 'page page-down', tabindex: '-1' },
    h('div', { class: 'down glass' },
      h('div', { class: 'down-visual', 'aria-hidden': 'true' }, h('span', { class: 'down-sweep' }), icon('laser')),
      h('p', { class: 'eyebrow', text: 'Signal lost' }),
      h('h1', { class: 'display-s', text: 'The map server is not answering' }),
      h('p', { class: 'lede', text: 'Merz Mapper could not download the robot’s data. Check your connection (on the demo Wi-Fi, check you are on the right network), then try again.' }),
      h('p', { class: 'mono small muted', text: error instanceof Error ? error.message : 'Unknown error' }),
      retry)));
  announce('The map server is not answering. Try again.');
}

// ------------------------------------------------------------------ rendering
let bundlePromise: Promise<Bundle> | null = null;

async function render(userAction = false) {
  const token = ++renderToken;
  const { page, params } = route();
  let bundle: Bundle;
  try {
    bundle = await (bundlePromise ??= loadBundle());
  } catch (error) {
    bundlePromise = null;
    if (error instanceof Unreachable || error instanceof TypeError) return serverDown(error);
    throw error;
  }
  shell(bundle);
  markNav(page);
  const module = await PAGES[page].load();
  if (token !== renderToken) return;
  const old = app.firstElementChild as HTMLElement | null;
  if (old && userAction && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    await gsap.to(old, { opacity: 0, y: -10, duration: 0.28, ease: 'power2.in' });
  }
  if (token !== renderToken) return;
  if (typeof cleanup === 'function') cleanup();
  killScroll();
  overlay.replaceChildren();
  document.body.dataset.page = page;
  document.title = `Merz Mapper · ${PAGES[page].title}`;
  const root = h('main', { id: 'main', class: `page page-${page}`, tabindex: '-1' });
  app.replaceChildren(root);
  window.scrollTo(0, 0);
  cleanup = await module.default({ bundle, root, overlay, params, scene: () => getScene(bundle), navigate });
  if (userAction) root.focus({ preventScroll: true });
}

function boot() {
  bundlePromise = null;
  render().catch((error) => serverDown(error));
}

boot();
