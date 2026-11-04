// A bottom sheet on phones (drag the handle between peek, half and full); a fixed side panel on wide screens.
export type Snap = 'peek' | 'half' | 'full';

export function attachSheet(panel: HTMLElement, handle: HTMLElement) {
  const narrow = () => window.innerWidth < 900;
  let state: Snap = 'half';
  const heights = () => {
    const vh = window.innerHeight;
    return { peek: 148, half: Math.round(vh * 0.48), full: Math.round(vh - 88) };
  };
  const apply = (animate = true) => {
    if (!narrow()) { panel.style.removeProperty('--sheet-h'); panel.dataset.snap = ''; return; }
    panel.style.transition = animate ? '' : 'none';
    panel.style.setProperty('--sheet-h', `${heights()[state]}px`);
    panel.dataset.snap = state;
    handle.setAttribute('aria-expanded', String(state !== 'peek'));
  };
  const snap = (s: Snap) => { state = s; apply(); };

  let startY = 0;
  let startH = 0;
  let dragging = false;
  const down = (e: PointerEvent) => {
    if (!narrow()) return;
    dragging = true;
    startY = e.clientY;
    startH = panel.getBoundingClientRect().height;
    panel.style.transition = 'none';
    handle.setPointerCapture(e.pointerId);
  };
  const move = (e: PointerEvent) => {
    if (!dragging) return;
    const hgt = Math.max(110, Math.min(heights().full, startH + (startY - e.clientY)));
    panel.style.setProperty('--sheet-h', `${hgt}px`);
  };
  const up = (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false;
    panel.style.transition = '';
    const moved = startY - e.clientY;
    const now = startH + moved;
    if (Math.abs(moved) < 6) { state = state === 'peek' ? 'half' : state === 'half' ? 'full' : 'peek'; apply(); return; }
    const hs = heights();
    state = (Object.entries(hs) as [Snap, number][]).sort((a, b) => Math.abs(a[1] - now) - Math.abs(b[1] - now))[0][0];
    apply();
  };
  const key = (e: KeyboardEvent) => {
    if (e.key === 'ArrowUp') { e.preventDefault(); snap(state === 'peek' ? 'half' : 'full'); }
    if (e.key === 'ArrowDown') { e.preventDefault(); snap(state === 'full' ? 'half' : 'peek'); }
  };
  const click = (e: MouseEvent) => { if (e.detail === 0) snap(state === 'peek' ? 'half' : state === 'half' ? 'full' : 'peek'); };
  handle.addEventListener('pointerdown', down);
  handle.addEventListener('pointermove', move);
  handle.addEventListener('pointerup', up);
  handle.addEventListener('keydown', key);
  handle.addEventListener('click', click);
  const resize = () => apply(false);
  window.addEventListener('resize', resize);
  apply(false);
  return {
    snap,
    destroy: () => { window.removeEventListener('resize', resize); },
  };
}
