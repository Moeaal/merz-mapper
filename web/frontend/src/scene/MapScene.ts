import * as THREE from 'three';
import type { Bundle, Landmark, Mission, Route } from '../data';
import { poseAt } from '../data';
import {
  cloudFragment, cloudVertex, floorFragment, floorVertex, groundFragment, ribbonFragment, ribbonVertex, wallFragment,
  wallVertex,
} from './shaders';

// One WebGL scene shared by every page. Map coordinates (x east, y north, metres) become world (x, 0, -y).
export interface Rig { x: number; y: number; dist: number; tilt: number; az: number }
export interface Eye { px: number; py: number; ph: number; tx: number; ty: number; th: number }
type Theme = 'dark' | 'light';

const WALL_HEIGHT = 2.4;
const v3 = (x: number, y: number, h = 0) => new THREE.Vector3(x, h, -y);

function css(name: string): THREE.Color {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return new THREE.Color(value || '#ffffff');
}

function easeInOut(t: number) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

export class MapScene {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(34, 1, 0.1, 2000);
  rig: Rig = { x: 0, y: 0, dist: 80, tilt: 0, az: 0 };
  eye: Eye | null = null;
  eyeBlend = 0;
  private floor!: THREE.Mesh<THREE.PlaneGeometry, THREE.ShaderMaterial>;
  private ground!: THREE.Mesh<THREE.PlaneGeometry, THREE.ShaderMaterial>;
  private walls: THREE.InstancedMesh<THREE.BoxGeometry, THREE.ShaderMaterial> | null = null;
  private route: { core: THREE.Mesh; glow: THREE.Mesh; length: number } | null = null;
  private trail: { core: THREE.Mesh; glow: THREE.Mesh } | null = null;
  private cloud: THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial> | null = null;
  private robot = new THREE.Group();
  private rays: THREE.LineSegments<THREE.BufferGeometry, THREE.LineBasicMaterial> | null = null;
  private hits: THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial> | null = null;
  private ellipse: THREE.Mesh<THREE.RingGeometry, THREE.MeshBasicMaterial> | null = null;
  private graphLines: THREE.LineSegments<THREE.BufferGeometry, THREE.LineBasicMaterial> | null = null;
  private clock = new THREE.Clock();
  private tweens: { update: (now: number) => boolean }[] = [];
  private listeners = new Set<() => void>();
  private running = true;
  private continuous = 0;
  private dirty = true;
  readonly centre: { x: number; y: number; w: number; h: number };
  wallHeight = 0;
  reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  constructor(readonly host: HTMLElement, readonly bundle: Bundle, textures: { state: THREE.Texture; reveal?: THREE.Texture }) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x000000, 0);
    host.appendChild(this.renderer.domElement);
    this.renderer.domElement.setAttribute('aria-hidden', 'true');
    const m = bundle.manifest.map;
    const w = m.width * m.resolution;
    const h = m.height * m.resolution;
    this.centre = { x: m.origin[0] + w / 2, y: m.origin[1] + h / 2, w, h };

    const groundMat = new THREE.ShaderMaterial({
      vertexShader: floorVertex, fragmentShader: groundFragment, transparent: true, depthWrite: false,
      uniforms: { uDot: { value: new THREE.Color() }, uCentre: { value: v3(this.centre.x, this.centre.y) }, uOpacity: { value: 1 } },
    });
    this.ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), groundMat);
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.position.copy(v3(this.centre.x, this.centre.y, -0.02));
    this.scene.add(this.ground);

    textures.state.magFilter = THREE.LinearFilter;
    textures.state.minFilter = THREE.LinearMipmapLinearFilter;
    textures.state.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
    const reveal = textures.reveal ?? textures.state;
    reveal.magFilter = THREE.NearestFilter;
    reveal.minFilter = THREE.NearestFilter;
    reveal.generateMipmaps = false;
    const floorMat = new THREE.ShaderMaterial({
      vertexShader: floorVertex, fragmentShader: floorFragment, transparent: true, depthWrite: false,
      uniforms: {
        tState: { value: textures.state }, tReveal: { value: reveal }, uRevealK: { value: 999 },
        uHasReveal: { value: textures.reveal ? 1 : 0 }, uFloor: { value: new THREE.Color() },
        uWall: { value: new THREE.Color() }, uAccent: { value: new THREE.Color() }, uGrid: { value: new THREE.Color() },
        uTexel: { value: new THREE.Vector2(1 / m.width, 1 / m.height) }, uOpacity: { value: 1 }, uAO: { value: 0 },
        uWallFlat: { value: 1 }, uGridAmount: { value: 0.35 },
      },
    });
    this.floor = new THREE.Mesh(new THREE.PlaneGeometry(w, h), floorMat);
    this.floor.rotation.x = -Math.PI / 2;
    this.floor.position.copy(v3(this.centre.x, this.centre.y, 0));
    this.floor.renderOrder = 1;
    this.scene.add(this.floor);

    this.buildRobot();
    this.applyTheme();
    this.resize();
    window.addEventListener('resize', this.resize);
    document.addEventListener('visibilitychange', this.onVisibility);
    this.loop();
  }

  // ------------------------------------------------------------------ lifecycle
  private onVisibility = () => { this.running = !document.hidden; if (this.running) { this.clock.getDelta(); this.loop(); } };

  resize = () => {
    const w = this.host.clientWidth || window.innerWidth;
    const h = this.host.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.dirty = true;
  };

  onFrame(fn: () => void) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  hold() { this.continuous++; return () => { this.continuous = Math.max(0, this.continuous - 1); }; }
  invalidate() { this.dirty = true; }

  private loop = () => {
    if (!this.running) return;
    requestAnimationFrame(this.loop);
    const now = performance.now();
    if (this.tweens.length) {
      this.tweens = this.tweens.filter((t) => t.update(now));
      this.dirty = true;
    }
    if (!this.dirty && !this.continuous) return;
    const time = this.clock.getElapsedTime();
    if (this.route) {
      (this.route.core.material as THREE.ShaderMaterial).uniforms.uTime.value = time;
      (this.route.glow.material as THREE.ShaderMaterial).uniforms.uTime.value = time;
    }
    this.robot.children[1]?.scale.setScalar(1 + 0.12 * Math.sin(time * 3));
    this.updateCamera();
    this.renderer.render(this.scene, this.camera);
    for (const fn of this.listeners) fn();
    this.dirty = false;
  };

  // ------------------------------------------------------------------ theme
  applyTheme() {
    const theme = (document.documentElement.dataset.theme as Theme) || 'dark';
    const f = this.floor.material.uniforms;
    f.uFloor.value.copy(css('--floor'));
    f.uWall.value.copy(css('--wall'));
    f.uAccent.value.copy(css('--accent'));
    f.uGrid.value.copy(css('--line-strong'));
    f.uGridAmount.value = theme === 'light' ? 0.55 : 0.4;
    this.ground.material.uniforms.uDot.value.copy(css('--line-strong'));
    if (this.walls) {
      const u = this.walls.material.uniforms;
      u.uSide.value.copy(theme === 'light' ? new THREE.Color('#e9e4d4') : new THREE.Color('#2a3a58'));
      u.uCap.value.copy(theme === 'light' ? css('--wall') : css('--wall'));
    }
    const accent = css('--accent-mark');
    const accentText = css('--accent');
    for (const ribbon of [this.route, this.trail]) {
      if (!ribbon) continue;
      (ribbon.core.material as THREE.ShaderMaterial).uniforms.uColor.value.copy(theme === 'light' ? accent : accentText);
      (ribbon.glow.material as THREE.ShaderMaterial).uniforms.uColor.value.copy(accent);
    }
    if (this.cloud) {
      this.cloud.material.uniforms.uColor.value.copy(css('--cloud'));
      this.cloud.material.uniforms.uAccent.value.copy(accentText);
      this.cloud.material.blending = theme === 'light' ? THREE.NormalBlending : THREE.AdditiveBlending;
    }
    (this.robot.children[0] as THREE.Mesh).material = new THREE.MeshBasicMaterial({ color: accentText });
    const halo = this.robot.children[1] as THREE.Sprite;
    halo.material.color.copy(accent);
    if (this.rays) this.rays.material.color.copy(accentText);
    if (this.hits) this.hits.material.color.copy(accentText);
    if (this.ellipse) this.ellipse.material.color.copy(accentText);
    if (this.graphLines) this.graphLines.material.color.copy(accentText);
    this.dirty = true;
  }

  // ------------------------------------------------------------------ camera
  updateCamera() {
    const r = this.rig;
    const target = v3(r.x, r.y, 0);
    const horizontal = r.dist * Math.sin(r.tilt);
    const pos = new THREE.Vector3(target.x + Math.sin(r.az) * horizontal, r.dist * Math.cos(r.tilt),
      target.z + Math.cos(r.az) * horizontal);
    // Looking straight down, "up" on screen is map north rotated by az; tilting blends towards world up.
    const north = new THREE.Vector3(-Math.sin(r.az), 0, -Math.cos(r.az));
    const up = north.lerp(new THREE.Vector3(0, 1, 0), THREE.MathUtils.smoothstep(r.tilt, 0, 0.25)).normalize();
    if (this.eye && this.eyeBlend > 0) {
      const e = this.eye;
      const k = this.eyeBlend;
      pos.lerp(v3(e.px, e.py, e.ph), k);
      target.lerp(v3(e.tx, e.ty, e.th), k);
      up.lerp(new THREE.Vector3(0, 1, 0), k).normalize();
    }
    this.camera.position.copy(pos);
    this.camera.up.copy(up);
    this.camera.lookAt(target);
  }

  tween(duration: number, step: (k: number) => void, done?: () => void) {
    if (this.reducedMotion || duration <= 0) { step(1); done?.(); this.dirty = true; return; }
    const start = performance.now();
    this.tweens.push({
      update: (now) => {
        const t = Math.min(1, (now - start) / duration);
        step(easeInOut(t));
        if (t >= 1) { done?.(); return false; }
        return true;
      },
    });
    this.dirty = true;
  }

  stopTweens() { this.tweens = []; }

  flyTo(to: Partial<Rig>, duration = 1400, done?: () => void) {
    const from = { ...this.rig };
    const goal = { ...this.rig, ...to };
    let daz = goal.az - from.az;
    daz = Math.atan2(Math.sin(daz), Math.cos(daz));
    this.stopTweens();
    this.tween(duration, (k) => {
      this.rig.x = from.x + (goal.x - from.x) * k;
      this.rig.y = from.y + (goal.y - from.y) * k;
      this.rig.dist = Math.exp(Math.log(from.dist) + (Math.log(goal.dist) - Math.log(from.dist)) * k);
      this.rig.tilt = from.tilt + (goal.tilt - from.tilt) * k;
      this.rig.az = from.az + daz * k;
    }, done);
  }

  /** Distance needed to fit a box of map metres on screen, with padding in pixels. */
  fitDistance(w: number, h: number, padding = 80, tilt = this.rig.tilt) {
    const vfov = THREE.MathUtils.degToRad(this.camera.fov);
    const W = this.renderer.domElement.clientWidth || window.innerWidth;
    const H = this.renderer.domElement.clientHeight || window.innerHeight;
    const scaleW = W / Math.max(1, W - padding * 2);
    const scaleH = H / Math.max(1, H - padding * 2);
    const byH = (h * scaleH) / 2 / Math.tan(vfov / 2);
    const byW = (w * scaleW) / 2 / Math.tan(vfov / 2) / this.camera.aspect;
    return Math.max(byH, byW) * (1 + Math.sin(tilt) * 0.35);
  }

  fit(points: [number, number][], opts: { tilt?: number; az?: number; padding?: number; duration?: number;
    offsetX?: number; offsetY?: number } = {}) {
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const az = opts.az ?? this.rig.az;
    // Rotate the box into screen axes to size it properly when the map is rotated.
    const c = Math.cos(az), s = Math.sin(az);
    const corners = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map(([x, y]) => [x * c - y * s, x * s + y * c]);
    const w = Math.max(...corners.map((p) => p[0])) - Math.min(...corners.map((p) => p[0]));
    const h = Math.max(...corners.map((p) => p[1])) - Math.min(...corners.map((p) => p[1]));
    const tilt = opts.tilt ?? this.rig.tilt;
    const dist = Math.max(8, this.fitDistance(Math.max(w, 4), Math.max(h, 4), opts.padding ?? 90, tilt));
    // Offsets shift the framed box away from panels (in metres, screen axes).
    const ox = (opts.offsetX ?? 0) * dist, oy = (opts.offsetY ?? 0) * dist;
    this.flyTo({ x: (x0 + x1) / 2 - (ox * c + oy * s), y: (y0 + y1) / 2 - (-ox * s + oy * c), dist, tilt, az },
      opts.duration ?? 1400);
  }

  overview(tilt = 0, duration = 1400, az = 0) {
    const m = this.bundle.manifest.map;
    const pts: [number, number][] = [[m.origin[0], m.origin[1]], [m.origin[0] + m.width * m.resolution, m.origin[1] + m.height * m.resolution]];
    this.fit(pts, { tilt, az, duration, padding: 40 });
  }

  /** Screen position (CSS pixels) of a map point; null if behind the camera. */
  project(x: number, y: number, h = 0): { x: number; y: number; visible: boolean } | null {
    const p = v3(x, y, h).project(this.camera);
    if (p.z > 1) return null;
    const el = this.renderer.domElement;
    const sx = (p.x * 0.5 + 0.5) * el.clientWidth;
    const sy = (-p.y * 0.5 + 0.5) * el.clientHeight;
    return { x: sx, y: sy, visible: p.x > -1.2 && p.x < 1.2 && p.y > -1.2 && p.y < 1.2 };
  }

  /** Map point under a screen position, on the floor plane. */
  unproject(sx: number, sy: number): [number, number] | null {
    const el = this.renderer.domElement;
    const ndc = new THREE.Vector2((sx / el.clientWidth) * 2 - 1, -(sy / el.clientHeight) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, this.camera);
    const hit = new THREE.Vector3();
    if (!ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit)) return null;
    return [hit.x, -hit.z];
  }

  // ------------------------------------------------------------------ walls (3D)
  async ensureWalls() {
    if (this.walls) return;
    const boxes = await fetch(this.bundle.url(this.bundle.manifest.map.walls)).then((r) => r.json()) as number[][];
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    geometry.translate(0, 0.5, 0);
    const material = new THREE.ShaderMaterial({
      vertexShader: wallVertex, fragmentShader: wallFragment, transparent: true,
      uniforms: { uHeight: { value: 0.001 }, uSide: { value: new THREE.Color() }, uCap: { value: new THREE.Color() },
        uLight: { value: new THREE.Vector3(0.5, 0.8, 0.3) }, uOpacity: { value: 1 } },
    });
    const mesh = new THREE.InstancedMesh(geometry, material, boxes.length);
    const matrix = new THREE.Matrix4();
    boxes.forEach(([x0, y0, x1, y1], i) => {
      matrix.makeScale(Math.max(x1 - x0, 0.05), WALL_HEIGHT, Math.max(y1 - y0, 0.05));
      matrix.setPosition((x0 + x1) / 2, 0, -(y0 + y1) / 2);
      mesh.setMatrixAt(i, matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
    mesh.frustumCulled = false;
    mesh.visible = false;
    mesh.renderOrder = 2;
    this.walls = mesh;
    this.scene.add(mesh);
    this.applyTheme();
  }

  async setWalls(on: boolean, duration = 1100) {
    if (on) await this.ensureWalls();
    if (!this.walls) return;
    const walls = this.walls;
    const from = this.wallHeight;
    const to = on ? 1 : 0;
    walls.visible = true;
    const f = this.floor.material.uniforms;
    this.tween(duration, (k) => {
      this.wallHeight = from + (to - from) * k;
      walls.material.uniforms.uHeight.value = Math.max(0.001, this.wallHeight);
      f.uAO.value = this.wallHeight;
      f.uWallFlat.value = 1 - this.wallHeight * 0.85;
    }, () => { walls.visible = this.wallHeight > 0.01; });
  }

  // ------------------------------------------------------------------ ribbons: route and trail
  private ribbonGeometry(points: THREE.Vector2[], width: number, times?: number[]) {
    // Dense resampling keeps corners clean; each vertex carries distance along the line and side (-1..1).
    const positions: number[] = [];
    const dists: number[] = [];
    const sides: number[] = [];
    const ts: number[] = [];
    const indices: number[] = [];
    let total = 0;
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const prev = points[Math.max(0, i - 1)];
      const next = points[Math.min(points.length - 1, i + 1)];
      if (i > 0) total += p.distanceTo(prev);
      const dir = new THREE.Vector2().subVectors(next, prev);
      if (dir.lengthSq() < 1e-9) dir.set(1, 0);
      dir.normalize();
      const normal = new THREE.Vector2(-dir.y, dir.x).multiplyScalar(width / 2);
      for (const side of [-1, 1]) {
        positions.push(p.x + normal.x * side, 0.04, -(p.y + normal.y * side));
        dists.push(total);
        sides.push(side);
        ts.push(times ? times[i] : 0);
      }
      if (i > 0) {
        const a = (i - 1) * 2;
        indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('aDist', new THREE.Float32BufferAttribute(dists, 1));
    geometry.setAttribute('aSide', new THREE.Float32BufferAttribute(sides, 1));
    geometry.setAttribute('aT', new THREE.Float32BufferAttribute(ts, 1));
    geometry.setIndex(indices);
    return { geometry, total };
  }

  private ribbonMaterial(glow: boolean, trail: boolean) {
    return new THREE.ShaderMaterial({
      vertexShader: ribbonVertex, fragmentShader: ribbonFragment, transparent: true, depthWrite: false,
      blending: glow && document.documentElement.dataset.theme !== 'light' ? THREE.AdditiveBlending : THREE.NormalBlending,
      uniforms: { uColor: { value: new THREE.Color() }, uDraw: { value: 0 }, uTime: { value: 0 }, uGlow: { value: glow ? 1 : 0 },
        uOpacity: { value: 1 }, uTrail: { value: trail ? 1 : 0 }, uT: { value: 0 }, uFade: { value: 120 },
        uMinAlpha: { value: 0.3 } },
    });
  }

  private densify(path: [number, number][], step = 0.25) {
    const out: THREE.Vector2[] = [];
    for (let i = 0; i < path.length - 1; i++) {
      const a = new THREE.Vector2(...path[i]);
      const b = new THREE.Vector2(...path[i + 1]);
      const n = Math.max(1, Math.ceil(a.distanceTo(b) / step));
      for (let k = 0; k < n; k++) out.push(a.clone().lerp(b, k / n));
    }
    out.push(new THREE.Vector2(...path[path.length - 1]));
    return out;
  }

  /** Show a route as a glowing ribbon. Returns its length; drawRoute animates it in. */
  setRoute(points: [number, number][] | null) {
    if (this.route) {
      this.scene.remove(this.route.core, this.route.glow);
      this.route.core.geometry.dispose();
      this.route.glow.geometry.dispose();
      this.route = null;
    }
    if (!points || points.length < 2) { this.dirty = true; return 0; }
    const dense = this.densify(points);
    const core = this.ribbonGeometry(dense, 0.32);
    const glow = this.ribbonGeometry(dense, 2.4);
    const coreMesh = new THREE.Mesh(core.geometry, this.ribbonMaterial(false, false));
    const glowMesh = new THREE.Mesh(glow.geometry, this.ribbonMaterial(true, false));
    coreMesh.renderOrder = 5;
    glowMesh.renderOrder = 4;
    this.route = { core: coreMesh, glow: glowMesh, length: core.total };
    this.scene.add(glowMesh, coreMesh);
    this.applyTheme();
    return core.total;
  }

  drawRoute(duration = 1800, from = 0) {
    if (!this.route) return;
    const route = this.route;
    this.tween(duration, (k) => {
      const d = from + (route.length - from) * k + 0.01;
      (route.core.material as THREE.ShaderMaterial).uniforms.uDraw.value = d;
      (route.glow.material as THREE.ShaderMaterial).uniforms.uDraw.value = d;
    });
  }

  routeLength() { return this.route?.length ?? 0; }

  /** A trajectory trail; points carry time so the replay can show it up to any moment. */
  setTrail(trajectory: Mission['trajectory'] | null, fadeSeconds = 120, minAlpha = 0.3) {
    if (this.trail) {
      this.scene.remove(this.trail.core, this.trail.glow);
      this.trail = null;
    }
    if (!trajectory) return;
    const pts: THREE.Vector2[] = [];
    const times: number[] = [];
    let previous: number[] | null = null;
    for (const p of trajectory) {
      if (previous && Math.hypot(p[1] - previous[1], p[2] - previous[2]) > 2) {
        // A jump between entrance runs: hide the joining segment.
        pts.push(new THREE.Vector2(previous[1], previous[2]), new THREE.Vector2(p[1], p[2]));
        times.push(-1, -1);
      }
      pts.push(new THREE.Vector2(p[1], p[2]));
      times.push(p[0]);
      previous = p;
    }
    const core = this.ribbonGeometry(pts, 0.14, times);
    const glow = this.ribbonGeometry(pts, 1.1, times);
    const coreMat = this.ribbonMaterial(false, true);
    const glowMat = this.ribbonMaterial(true, true);
    for (const m of [coreMat, glowMat]) { m.uniforms.uFade.value = fadeSeconds; m.uniforms.uMinAlpha.value = minAlpha; }
    glowMat.uniforms.uMinAlpha.value = minAlpha * 0.3;
    const coreMesh = new THREE.Mesh(core.geometry, coreMat);
    const glowMesh = new THREE.Mesh(glow.geometry, glowMat);
    coreMesh.renderOrder = 6;
    glowMesh.renderOrder = 5;
    this.trail = { core: coreMesh, glow: glowMesh };
    this.scene.add(glowMesh, coreMesh);
    this.applyTheme();
  }

  setTrailTime(t: number) {
    if (!this.trail) return;
    (this.trail.core.material as THREE.ShaderMaterial).uniforms.uT.value = t;
    (this.trail.glow.material as THREE.ShaderMaterial).uniforms.uT.value = t;
    this.dirty = true;
  }

  // ------------------------------------------------------------------ robot, lidar, cloud
  private buildRobot() {
    const shape = new THREE.Shape();
    shape.moveTo(0.55, 0);
    shape.lineTo(-0.35, 0.34);
    shape.lineTo(-0.18, 0);
    shape.lineTo(-0.35, -0.34);
    shape.closePath();
    const body = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial());
    body.rotation.x = -Math.PI / 2;
    body.position.y = 0.12;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 128;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.25, 'rgba(255,255,255,0.35)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 128);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true,
      depthWrite: false, blending: THREE.AdditiveBlending }));
    halo.position.y = 0.1;
    halo.scale.setScalar(3.2);
    this.robot.add(body, halo);
    this.robot.visible = false;
    this.robot.renderOrder = 8;
    this.scene.add(this.robot);
  }

  setRobot(pose: { x: number; y: number; yaw: number } | null) {
    this.robot.visible = !!pose;
    if (pose) {
      this.robot.position.set(pose.x, 0, -pose.y);
      this.robot.children[0].rotation.z = pose.yaw;
    }
    this.dirty = true;
  }

  setScan(origin: { x: number; y: number; yaw: number } | null, ranges?: Uint16Array, angleMin = 0, angleInc = 0) {
    if (!origin || !ranges) {
      if (this.rays) this.rays.visible = false;
      if (this.hits) this.hits.visible = false;
      this.dirty = true;
      return;
    }
    const n = ranges.length;
    if (!this.rays) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(n * 6), 3));
      this.rays = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({ transparent: true, opacity: 0.16,
        blending: THREE.AdditiveBlending, depthWrite: false }));
      const hitGeometry = new THREE.BufferGeometry();
      hitGeometry.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(n * 3), 3));
      this.hits = new THREE.Points(hitGeometry, new THREE.PointsMaterial({ size: 3.2, sizeAttenuation: false,
        transparent: true, opacity: 0.95, depthWrite: false }));
      this.rays.renderOrder = 7;
      this.hits.renderOrder = 7;
      this.scene.add(this.rays, this.hits);
      this.applyTheme();
    }
    const rayPos = this.rays.geometry.getAttribute('position') as THREE.BufferAttribute;
    const hitPos = this.hits!.geometry.getAttribute('position') as THREE.BufferAttribute;
    let k = 0;
    for (let i = 0; i < n; i++) {
      const r = ranges[i] / 100;
      if (r <= 0.05) continue;
      const a = origin.yaw + angleMin + i * angleInc;
      const hx = origin.x + Math.cos(a) * r;
      const hy = origin.y + Math.sin(a) * r;
      rayPos.setXYZ(k * 2, origin.x, 0.3, -origin.y);
      rayPos.setXYZ(k * 2 + 1, hx, 0.3, -hy);
      hitPos.setXYZ(k, hx, 0.3, -hy);
      k++;
    }
    this.rays.geometry.setDrawRange(0, k * 2);
    this.hits!.geometry.setDrawRange(0, k);
    rayPos.needsUpdate = true;
    hitPos.needsUpdate = true;
    this.rays.visible = true;
    this.hits!.visible = true;
    this.dirty = true;
  }

  setCloud(cloud: Int16Array | null) {
    if (this.cloud) { this.scene.remove(this.cloud); this.cloud = null; }
    if (!cloud) return;
    const n = cloud.length / 3;
    const positions = new Float32Array(n * 3);
    const times = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      positions[i * 3] = cloud[i * 3] / 100;
      positions[i * 3 + 1] = 0.08;
      positions[i * 3 + 2] = -cloud[i * 3 + 1] / 100;
      times[i] = (cloud[i * 3 + 2] + 32768) / 10;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('aT', new THREE.BufferAttribute(times, 1));
    const material = new THREE.ShaderMaterial({
      vertexShader: cloudVertex, fragmentShader: cloudFragment, transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uT: { value: 0 }, uSize: { value: 2.2 }, uPixelRatio: { value: this.renderer.getPixelRatio() },
        uColor: { value: new THREE.Color() }, uAccent: { value: new THREE.Color() }, uOpacity: { value: 1 } },
    });
    this.cloud = new THREE.Points(geometry, material);
    this.cloud.renderOrder = 3;
    this.cloud.frustumCulled = false;
    this.scene.add(this.cloud);
    this.applyTheme();
  }

  setCloudState(t: number, opacity = 1) {
    if (!this.cloud) return;
    this.cloud.material.uniforms.uT.value = t;
    this.cloud.material.uniforms.uOpacity.value = opacity;
    this.cloud.visible = opacity > 0.01;
    this.dirty = true;
  }

  // ------------------------------------------------------------------ map reveal, opacity, overlays
  setReveal(k: number) { this.floor.material.uniforms.uRevealK.value = k; this.dirty = true; }
  setMapOpacity(a: number) { this.floor.material.uniforms.uOpacity.value = a; this.dirty = true; }
  setGroundOpacity(a: number) { this.ground.material.uniforms.uOpacity.value = a; this.dirty = true; }

  showEllipse(lm: Landmark | null) {
    if (!lm) { if (this.ellipse) this.ellipse.visible = false; this.dirty = true; return; }
    if (!this.ellipse) {
      this.ellipse = new THREE.Mesh(new THREE.RingGeometry(0.94, 1, 96),
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.95, depthWrite: false, side: THREE.DoubleSide }));
      this.ellipse.rotation.x = -Math.PI / 2;
      this.ellipse.renderOrder = 9;
      this.scene.add(this.ellipse);
      this.applyTheme();
    }
    // 95% region of a 2D normal: 2.45 standard deviations.
    this.ellipse.scale.set(Math.max(0.08, lm.sd[0] * 2.45), Math.max(0.08, lm.sd[1] * 2.45), 1);
    this.ellipse.position.set(lm.x, 0.06, -lm.y);
    this.ellipse.visible = true;
    this.dirty = true;
  }

  setGraph(edges: [number, number][][] | null) {
    if (this.graphLines) { this.scene.remove(this.graphLines); this.graphLines = null; }
    if (!edges) { this.dirty = true; return; }
    const positions: number[] = [];
    for (const [[ax, ay], [bx, by]] of edges) positions.push(ax, 0.06, -ay, bx, 0.06, -by);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    this.graphLines = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({ transparent: true, opacity: 0.75 }));
    this.graphLines.renderOrder = 6;
    this.scene.add(this.graphLines);
    this.applyTheme();
  }

  route2points(route: Route, start: { x: number; y: number }): [number, number][] {
    return [[start.x, start.y], ...route.steps.map((s) => [s.x, s.y] as [number, number]),
      [route.destination.x, route.destination.y]];
  }

  poseAt(trajectory: Mission['trajectory'], t: number) { return poseAt(trajectory, t); }
}
