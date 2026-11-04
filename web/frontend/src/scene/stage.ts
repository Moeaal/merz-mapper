import type { Bundle } from '../data';
import type { MapScene } from './MapScene';

// The single scene, created on first need. three.js is loaded lazily so text and controls appear first.
let pending: Promise<MapScene | null> | null = null;
let current: MapScene | null = null;

export function webglAvailable(): boolean {
  if ((window as any).__merzForce2D) return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

export function getScene(bundle: Bundle): Promise<MapScene | null> {
  if (pending) return pending;
  pending = (async () => {
    if (!webglAvailable()) return null;
    const [{ MapScene }, THREE] = await Promise.all([import('./MapScene'), import('three')]);
    const loader = new THREE.TextureLoader();
    const level = bundle.manifest.map.levels.find((l) => l.factor === 1) ?? bundle.manifest.map.levels[0];
    const load = (url: string) => new Promise<InstanceType<typeof THREE.Texture>>((resolve, reject) =>
      loader.load(url, resolve, undefined, reject));
    const state = await load(bundle.url(level.file));
    const reveal = bundle.manifest.files.mission ? await load(bundle.url('mission/reveal.png')).catch(() => undefined) : undefined;
    const host = document.getElementById('stage')!;
    current = new MapScene(host, bundle, { state, reveal });
    document.documentElement.classList.add('has-webgl');
    return current;
  })().catch((error) => {
    console.warn('3D map unavailable, using the 2D map', error);
    pending = Promise.resolve(null);
    return null;
  });
  return pending;
}

export function sceneNow() { return current; }
