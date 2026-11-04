import type { Landmark } from '../data';
import { h, icon } from './dom';
import { CLASS_NAMES, landmarkIcon } from './icons';

export function youAreHere(label: string) {
  return h('div', { class: 'pin-here', role: 'img', 'aria-label': `You are here: ${label}` },
    h('span', { class: 'pulse' }), h('span', { class: 'pulse delay' }), h('span', { class: 'core' }),
    h('span', { class: 'pin-label', text: 'You are here' }));
}

export function beacon(label: string) {
  return h('div', { class: 'pin-beacon', role: 'img', 'aria-label': `Destination: room ${label}` },
    h('span', { class: 'beam' }), h('span', { class: 'core' }), h('span', { class: 'pin-label strong', text: label }));
}

export function landmarkPin(lm: Landmark, onClick?: (lm: Landmark) => void) {
  const name = CLASS_NAMES[lm.class] ?? lm.class;
  const label = lm.text ? `${name} ${lm.text}` : name;
  const el = h('button', { class: `pin-landmark cls-${lm.class}`, type: 'button', 'aria-label': `${label}. Show details.`,
    'data-id': lm.id }, icon(landmarkIcon(lm.class)), lm.text ? h('span', { class: 'pin-text', text: lm.text }) : null);
  if (onClick) el.addEventListener('click', () => onClick(lm));
  else el.tabIndex = -1;
  return el;
}

export function stepPin(n: number, onClick?: () => void) {
  const el = h('button', { class: 'pin-step', type: 'button', text: String(n), 'aria-label': `Step ${n}`, tabindex: '-1' });
  if (onClick) el.addEventListener('click', onClick);
  return el;
}
