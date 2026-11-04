// Glyphs drawn for this site on a 24 px grid, 1.6 px strokes, round joins. Fixed strings only: never data.
const s = (body: string, vb = 24) =>
  `<svg viewBox="0 0 ${vb} ${vb}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;

export const icons = {
  logo: `<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><circle cx="16" cy="16" r="14.5" fill="none" stroke="currentColor" stroke-opacity=".35"/><path d="M16 4.5a11.5 11.5 0 0 1 11.5 11.5" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round"/><path d="M11 21.5 16 9.5l5 12-5-3.2z" fill="var(--accent)"/></svg>`,
  find: s('<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/>'),
  mission: s('<path d="M3 17c3-6 6 2 9-4s5-6 9-3"/><circle cx="21" cy="10" r="1.6" fill="currentColor"/><path d="M3 21h18" opacity=".5"/>'),
  results: s('<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/><path d="m15.5 8.5 4-4M17 4.5h2.5V7"/>'),
  about: s('<rect x="5" y="9" width="14" height="7" rx="2"/><circle cx="8" cy="18.5" r="1.8"/><circle cx="16" cy="18.5" r="1.8"/><path d="M12 9V5.5M9.5 4h5"/>'),
  search: s('<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>'),
  close: s('<path d="m6 6 12 12M18 6 6 18"/>'),
  menu: s('<path d="M4 8h16M4 16h10"/>'),
  play: s('<path d="M8 5.5v13l11-6.5z" fill="currentColor"/>'),
  pause: s('<path d="M8 5v14M16 5v14" stroke-width="2.6"/>'),
  prev: s('<path d="m14.5 6-6 6 6 6"/>'),
  next: s('<path d="m9.5 6 6 6-6 6"/>'),
  back: s('<path d="M19 12H5m6-6-6 6 6 6"/>'),
  arrow: s('<path d="M5 12h14m-6-6 6 6-6 6"/>'),
  cube: s('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>'),
  flat: s('<path d="M3 15.5 12 20l9-4.5L12 11z"/><path d="M3 11.5 12 7l9 4.5" opacity=".45"/>'),
  compass: s('<circle cx="12" cy="12" r="8.5"/><path d="m12 5.5 2.4 6.5h-4.8z" fill="currentColor" stroke="none"/><path d="m12 18.5-2.4-6.5h4.8z" opacity=".5"/>'),
  locate: s('<circle cx="12" cy="12" r="3.5"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/>'),
  walk: s('<circle cx="13" cy="4.5" r="1.8"/><path d="m10 21 2-6 3 2v4M8 12l2.5-4.5 4 1.5 2 3.5M12.5 8.5l-1 5"/>'),
  plus: s('<path d="M12 5v14M5 12h14"/>'),
  minus: s('<path d="M5 12h14"/>'),
  sun: s('<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>'),
  moon: s('<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>'),
  retry: s('<path d="M20 12a8 8 0 1 1-2.4-5.7M20 4v5h-5"/>'),
  check: s('<path d="m5 12.5 4.5 4.5L19 7.5" stroke-width="2.2"/>'),
  cross: s('<path d="m6.5 6.5 11 11M17.5 6.5l-11 11" stroke-width="2.2"/>'),
  dash: s('<path d="M6 12h12" stroke-width="2.2" stroke-dasharray="2 3"/>'),
  info: s('<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8v.2" stroke-width="2"/>'),
  lock: s('<rect x="5.5" y="10.5" width="13" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>'),
  door: s('<path d="M14 4h5v16h-5M3 12h11m-4-4 4 4-4 4"/>'),
  straight: s('<path d="M12 20V5m-6 6 6-6 6 6"/>', 24),
  left: s('<path d="M16 20v-8a4 4 0 0 0-4-4H5m5-5-5 5 5 5"/>'),
  right: s('<path d="M8 20v-8a4 4 0 0 1 4-4h7m-5-5 5 5-5 5"/>'),
  backturn: s('<path d="M16 20V10a4 4 0 0 0-8 0v6m-3.5-3.5L8 16l3.5-3.5"/>'),
  arrive: s('<path d="M7 21V4m0 1h11l-3 4 3 4H7"/>'),
  room_sign: s('<rect x="4" y="7" width="16" height="10" rx="1.5"/><path d="M8 12h8" stroke-width="2"/>'),
  lift: s('<rect x="5" y="3.5" width="14" height="17" rx="1.5"/><path d="M12 3.5v17M8 9.5l1.5-2 1.5 2M13 14.5l1.5 2 1.5-2"/>'),
  stairs: s('<path d="M4 20h4v-4h4v-4h4V8h4"/>'),
  exit_sign: s('<rect x="3.5" y="6.5" width="17" height="11" rx="1.5"/><path d="M9 12h7m-3-3 3 3-3 3"/>'),
  laser: s('<circle cx="12" cy="12" r="2.5"/><path d="M12 3a9 9 0 0 1 9 9M12 6.5a5.5 5.5 0 0 1 5.5 5.5" opacity=".7"/>'),
  camera: s('<rect x="3.5" y="7" width="17" height="12" rx="2"/><circle cx="12" cy="13" r="3.5"/><path d="M8.5 7 10 4.5h4L15.5 7"/>'),
  chip: s('<rect x="6" y="6" width="12" height="12" rx="1.5"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>'),
  depth: s('<rect x="3" y="8" width="18" height="8" rx="2"/><circle cx="7.5" cy="12" r="1.6"/><circle cx="16.5" cy="12" r="1.6"/><circle cx="12" cy="12" r=".8" fill="currentColor"/>'),
  external: s('<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>'),
};

export type IconName = keyof typeof icons;

export function turnIcon(turn: string): IconName {
  return ({ left: 'left', right: 'right', back: 'backturn', arrive: 'arrive' } as Record<string, IconName>)[turn] ?? 'straight';
}

export function landmarkIcon(cls: string): IconName {
  return (cls in icons ? cls : 'room_sign') as IconName;
}

export const CLASS_NAMES: Record<string, string> = {
  room_sign: 'Room sign', door: 'Door', lift: 'Lift', stairs: 'Stairs', exit_sign: 'Exit sign',
};
