import type { MapScene } from './MapScene';

// Map gestures. One finger or mouse drag pans (with inertia); two fingers pinch to zoom, twist to rotate and move
// up/down together to tilt; right-drag or Ctrl/Shift-drag rotates and tilts; the wheel zooms towards the cursor.
// Keyboard (when the map has focus): arrows pan, + and - zoom, Q and E rotate, W and S tilt, N faces north.
export interface ControlOptions { onUserMove?: () => void; minDist?: number; maxDist?: number }

export function attachControls(surface: HTMLElement, scene: MapScene, options: ControlOptions = {}) {
  const minDist = options.minDist ?? 6;
  const maxDist = options.maxDist ?? 260;
  const pointers = new Map<number, { x: number; y: number }>();
  let mode: 'pan' | 'orbit' | null = null;
  let last: { x: number; y: number } | null = null;
  let gesture: { dist: number; angle: number; midY: number } | null = null;
  let velocity = { x: 0, y: 0 };
  let inertia = 0;
  const rect = () => surface.getBoundingClientRect();

  function local(e: { clientX: number; clientY: number }) {
    const r = rect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function panBy(from: { x: number; y: number }, to: { x: number; y: number }) {
    const a = scene.unproject(from.x, from.y);
    const b = scene.unproject(to.x, to.y);
    if (!a || !b) return { dx: 0, dy: 0 };
    const dx = a[0] - b[0];
    const dy = a[1] - b[1];
    scene.rig.x += dx;
    scene.rig.y += dy;
    scene.invalidate();
    return { dx, dy };
  }

  function zoomAt(point: { x: number; y: number }, factor: number) {
    const before = scene.unproject(point.x, point.y);
    scene.rig.dist = Math.min(maxDist, Math.max(minDist, scene.rig.dist * factor));
    scene.invalidate();
    // Keep the point under the cursor fixed while zooming.
    scene.updateCamera();
    const after = scene.unproject(point.x, point.y);
    if (before && after) {
      scene.rig.x += before[0] - after[0];
      scene.rig.y += before[1] - after[1];
    }
  }

  function userMoved() {
    scene.stopTweens();
    scene.eyeBlend = 0;
    options.onUserMove?.();
  }

  const onDown = (e: PointerEvent) => {
    if ((e.target as HTMLElement).closest('button, a, input, [data-no-drag]')) return;
    surface.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, local(e));
    cancelAnimationFrame(inertia);
    velocity = { x: 0, y: 0 };
    mode = e.button === 2 || e.ctrlKey || e.shiftKey ? 'orbit' : 'pan';
    last = local(e);
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      gesture = { dist: Math.hypot(a.x - b.x, a.y - b.y), angle: Math.atan2(b.y - a.y, b.x - a.x), midY: (a.y + b.y) / 2 };
    }
    surface.classList.add('is-dragging');
    userMoved();
  };

  const onMove = (e: PointerEvent) => {
    if (!pointers.has(e.pointerId)) return;
    const p = local(e);
    pointers.set(e.pointerId, p);
    if (pointers.size === 2 && gesture) {
      const [a, b] = [...pointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const angle = Math.atan2(b.y - a.y, b.x - a.x);
      const midY = (a.y + b.y) / 2;
      const mid = { x: (a.x + b.x) / 2, y: midY };
      zoomAt(mid, gesture.dist / Math.max(1, dist));
      scene.rig.az -= angle - gesture.angle;
      scene.rig.tilt = Math.min(1.15, Math.max(0, scene.rig.tilt + (midY - gesture.midY) * 0.004));
      gesture = { dist, angle, midY };
      scene.invalidate();
      return;
    }
    if (!last) return;
    if (mode === 'orbit') {
      scene.rig.az -= (p.x - last.x) * 0.006;
      scene.rig.tilt = Math.min(1.15, Math.max(0, scene.rig.tilt + (p.y - last.y) * 0.004));
      scene.invalidate();
    } else {
      const moved = panBy(last, p);
      velocity = { x: moved.dx, y: moved.dy };
    }
    last = p;
  };

  const onUp = (e: PointerEvent) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) gesture = null;
    if (pointers.size === 0) {
      surface.classList.remove('is-dragging');
      last = null;
      if (mode === 'pan' && !scene.reducedMotion && Math.hypot(velocity.x, velocity.y) > 0.01) {
        const glide = () => {
          velocity.x *= 0.9;
          velocity.y *= 0.9;
          scene.rig.x += velocity.x;
          scene.rig.y += velocity.y;
          scene.invalidate();
          if (Math.hypot(velocity.x, velocity.y) > 0.002) inertia = requestAnimationFrame(glide);
        };
        inertia = requestAnimationFrame(glide);
      }
      mode = null;
    } else {
      last = [...pointers.values()][0];
    }
  };

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    userMoved();
    const factor = Math.exp((e.deltaMode ? e.deltaY * 16 : e.deltaY) * 0.0016);
    zoomAt(local(e), factor);
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.target !== surface) return;
    const step = scene.rig.dist * 0.08;
    const c = Math.cos(scene.rig.az), s = Math.sin(scene.rig.az);
    const pan = (rx: number, ry: number) => { scene.rig.x += rx * c - ry * s; scene.rig.y += rx * s + ry * c; };
    const keys: Record<string, () => void> = {
      ArrowLeft: () => pan(-step, 0), ArrowRight: () => pan(step, 0), ArrowUp: () => pan(0, step), ArrowDown: () => pan(0, -step),
      '+': () => { scene.rig.dist = Math.max(minDist, scene.rig.dist / 1.25); },
      '=': () => { scene.rig.dist = Math.max(minDist, scene.rig.dist / 1.25); },
      '-': () => { scene.rig.dist = Math.min(maxDist, scene.rig.dist * 1.25); },
      q: () => { scene.rig.az += 0.15; }, e: () => { scene.rig.az -= 0.15; },
      w: () => { scene.rig.tilt = Math.min(1.15, scene.rig.tilt + 0.1); },
      s: () => { scene.rig.tilt = Math.max(0, scene.rig.tilt - 0.1); },
      n: () => scene.flyTo({ az: 0 }, 600),
    };
    const action = keys[e.key] ?? keys[e.key.toLowerCase()];
    if (!action) return;
    e.preventDefault();
    userMoved();
    action();
    scene.invalidate();
  };

  const onContext = (e: Event) => e.preventDefault();
  surface.addEventListener('pointerdown', onDown);
  surface.addEventListener('pointermove', onMove);
  surface.addEventListener('pointerup', onUp);
  surface.addEventListener('pointercancel', onUp);
  surface.addEventListener('wheel', onWheel, { passive: false });
  surface.addEventListener('keydown', onKey);
  surface.addEventListener('contextmenu', onContext);
  return () => {
    cancelAnimationFrame(inertia);
    surface.removeEventListener('pointerdown', onDown);
    surface.removeEventListener('pointermove', onMove);
    surface.removeEventListener('pointerup', onUp);
    surface.removeEventListener('pointercancel', onUp);
    surface.removeEventListener('wheel', onWheel);
    surface.removeEventListener('keydown', onKey);
    surface.removeEventListener('contextmenu', onContext);
  };
}
