// The website reads only the static bundle made by tools/web_import.py, so it behaves the same from FastAPI or GitHub
// Pages. Every number shown comes from these files; nothing is invented in the browser.

export interface Photo { src: string; thumb: string; w: number; h: number }
export interface Entrance { id: string; name: string; x: number; y: number; yaw: number }
export interface JunctionInfo { id: number; x: number; y: number; photo: Photo | null; taken_s: number | null }
export interface RoomInfo { room: string; x: number; y: number; landmark_id: number; entrances: string[] }
export interface Graph {
  entrances: Entrance[];
  junctions: JunctionInfo[];
  edges: [number, number, number][];
  zones: Record<string, { rooms: string[]; landmarks: number[]; junctions: number[] }>;
  rooms: RoomInfo[];
}
export type Turn = 'straight' | 'left' | 'right' | 'back' | 'arrive';
export interface RouteStep {
  junction_id: number; x: number; y: number; turn: Turn; instruction: string; distance_m: number; photo: Photo | null;
}
export interface Route {
  length_m: number; graph_length_m: number; turns: number; steps: RouteStep[]; destination: { x: number; y: number };
}
export type Routes = Record<string, { routes: Record<string, Route>; unreachable: string[] }>;
export interface Landmark {
  id: number; class: string; text: string; x: number; y: number; z: number; sd: [number, number];
  confidence: number; count: number; first_seen_s: number | null; last_seen_s: number | null; photo: Photo | null;
  observations: [number | null, number, number, number | null][];
}
export interface MapInfo {
  resolution: number; origin: [number, number]; width: number; height: number;
  levels: { file: string; factor: number }[]; walls: string; values: { unknown: number; free: number; occupied: number };
}
export interface Manifest {
  format: number; run_id: string; name: string; sample: boolean; imported_at: string; recorded_at: string | null;
  stats: {
    metres_explored: number | null; duration_s: number | null; signs_read: number; rooms_mapped: number;
    landmarks: number; junctions: number; entrances: number; mapped_area_m2: number; landmark_error_m: number | null;
  };
  map: MapInfo;
  files: { graph: string; routes: string; landmarks: string; metrics: string; mission: string | null };
}
export interface Mission {
  duration_s: number; distance_m: number;
  segments: { name: string; start_s: number; end_s: number }[];
  trajectory: [number, number, number, number, number][];      // t, x, y, yaw, distance so far
  snapshot_times: number[];
  scans: { file: string; count: number; rays: number; meta: [number, number, number, number, number, number][] };
  cloud: { file: string; count: number };
  reveal: { file: string };
}
export interface MetricPart {
  label: string; value: number; unit: string; target: number; comparator: string; passed: boolean | null;
  plot?: string | null; stats?: Record<string, number | null>; samples?: number[];
  histogram?: { bins: number[]; range_m: [number, number] };
  single?: Record<string, number | null>; fused?: Record<string, number | null>;
  detail?: Record<string, any>;
}
export interface Objective { title: string; status: 'pass' | 'fail' | 'not_measured' | 'inconclusive'; parts: MetricPart[]; sources: string[] }
export interface Metrics { objectives: Record<string, Objective> }

export class Unreachable extends Error {}

export interface Bundle {
  base: string;
  manifest: Manifest;
  graph: Graph;
  routes: Routes;
  landmarks: Landmark[];
  metrics: Metrics;
  url(path: string): string;
}

async function getJson<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { cache: 'no-cache' });
  } catch {
    throw new Unreachable('The data could not be downloaded.');
  }
  if (!response.ok) throw new Unreachable(`The server answered ${response.status} for ${url}.`);
  try {
    return (await response.json()) as T;
  } catch {
    throw new Unreachable(`${url} was not valid data.`);
  }
}

let cached: Promise<Bundle> | null = null;

export function loadBundle(force = false): Promise<Bundle> {
  if (cached && !force) return cached;
  cached = (async () => {
    const index = await getJson<{ default: string; runs: { id: string }[] }>('data/index.json');
    const base = `data/${index.default}/`;
    const manifest = await getJson<Manifest>(base + 'manifest.json');
    const [graph, routes, landmarks, metrics] = await Promise.all([
      getJson<Graph>(base + manifest.files.graph),
      getJson<Routes>(base + manifest.files.routes),
      getJson<Landmark[]>(base + manifest.files.landmarks),
      getJson<Metrics>(base + manifest.files.metrics),
    ]);
    return { base, manifest, graph, routes, landmarks, metrics, url: (p: string) => base + p };
  })();
  cached.catch(() => { cached = null; });
  return cached;
}

let missionCache: Promise<{ mission: Mission; scans: Uint16Array; cloud: Int16Array } | null> | null = null;

export function loadMission(bundle: Bundle) {
  if (missionCache) return missionCache;
  missionCache = (async () => {
    if (!bundle.manifest.files.mission) return null;
    const mission = await getJson<Mission>(bundle.url(bundle.manifest.files.mission));
    const [scans, cloud] = await Promise.all([
      fetch(bundle.url(mission.scans.file)).then((r) => r.arrayBuffer()).then((b) => new Uint16Array(b)),
      fetch(bundle.url(mission.cloud.file)).then((r) => r.arrayBuffer()).then((b) => new Int16Array(b)),
    ]);
    return { mission, scans, cloud };
  })();
  missionCache.catch(() => { missionCache = null; });
  return missionCache;
}

export function poseAt(trajectory: Mission['trajectory'], t: number) {
  // Binary search, then interpolate: the replay can be scrubbed to any time.
  let lo = 0;
  let hi = trajectory.length - 1;
  if (t <= trajectory[0][0]) return trajectory[0];
  if (t >= trajectory[hi][0]) return trajectory[hi];
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (trajectory[mid][0] <= t) lo = mid; else hi = mid;
  }
  const a = trajectory[lo];
  const b = trajectory[hi];
  const k = (t - a[0]) / Math.max(1e-6, b[0] - a[0]);
  let dyaw = b[3] - a[3];
  dyaw = Math.atan2(Math.sin(dyaw), Math.cos(dyaw));
  return [t, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k, a[3] + dyaw * k, a[4] + (b[4] - a[4]) * k] as
    [number, number, number, number, number];
}
