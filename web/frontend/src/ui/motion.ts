import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { reducedMotion } from './dom';

gsap.registerPlugin(ScrollTrigger);
gsap.defaults({ ease: 'expo.out', duration: 0.7 });

export { gsap, ScrollTrigger };

/** Stagger children in: rise and fade. With reduced motion, a short fade. */
export function reveal(targets: ArrayLike<Element>, delay = 0, stagger = 0.07) {
  const list = Array.from(targets);
  if (!list.length) return;
  if (reducedMotion()) {
    gsap.fromTo(list, { opacity: 0 }, { opacity: 1, duration: 0.12, delay: 0 });
    return;
  }
  gsap.fromTo(list, { opacity: 0, y: 22, filter: 'blur(6px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, delay, stagger, clearProps: 'filter,transform' });
}

/** Count a number up with tabular figures. */
export function countUp(el: HTMLElement, value: number | null, digits = 0, suffix = '', delay = 0) {
  if (value === null || value === undefined) { el.textContent = '—'; return; }
  const format = (v: number) => v.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits }) + suffix;
  if (reducedMotion()) { el.textContent = format(value); return; }
  const state = { v: 0 };
  el.textContent = format(0);
  gsap.to(state, { v: value, duration: 1.8, delay, ease: 'power3.out', onUpdate: () => { el.textContent = format(state.v); } });
}

/** Draw an SVG stroke from nothing. */
export function drawLines(paths: SVGGeometryElement[], duration = 1.4, delay = 0) {
  for (const path of paths) {
    const length = path.getTotalLength();
    path.style.strokeDasharray = `${length}`;
    path.style.strokeDashoffset = reducedMotion() ? '0' : `${length}`;
  }
  if (!reducedMotion()) gsap.to(paths, { strokeDashoffset: 0, duration, delay, ease: 'power2.inOut', stagger: 0.08 });
}

export function revealOnScroll(root: HTMLElement) {
  const items = root.querySelectorAll('[data-reveal]');
  items.forEach((item) => {
    if (reducedMotion()) return;
    gsap.fromTo(item, { opacity: 0, y: 36 }, {
      opacity: 1, y: 0, duration: 1, ease: 'expo.out',
      scrollTrigger: { trigger: item, start: 'top 85%', once: true },
    });
  });
}

export function killScroll() { ScrollTrigger.getAll().forEach((t) => t.kill()); }
