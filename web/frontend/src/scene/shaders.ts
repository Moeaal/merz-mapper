// GLSL for the map scene. World: x = map x, z = -map y, y = up (metres).

export const floorVertex = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorld;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

// The occupancy grid, coloured by theme. tState: 0 unknown, 0.5 free, 1 occupied. tReveal: snapshot index (0-255)
// when each cell first became known, for the mission replay. Unknown space is transparent.
export const floorFragment = /* glsl */ `
  uniform sampler2D tState;
  uniform sampler2D tReveal;
  uniform float uRevealK;
  uniform float uHasReveal;
  uniform vec3 uFloor;
  uniform vec3 uWall;
  uniform vec3 uAccent;
  uniform vec3 uGrid;
  uniform vec2 uTexel;
  uniform float uOpacity;
  uniform float uAO;
  uniform float uWallFlat;
  uniform float uGridAmount;
  varying vec2 vUv;
  varying vec3 vWorld;

  float occAt(vec2 uv) { return smoothstep(0.72, 0.92, texture2D(tState, uv).r); }

  void main() {
    float s = texture2D(tState, vUv).r;
    float known = 1.0;
    float fresh = 0.0;
    if (uHasReveal > 0.5) {
      float k = floor(texture2D(tReveal, vUv).r * 255.0 + 0.5);
      known = step(0.5, k) * step(k, uRevealK + 0.001);
      fresh = known * (1.0 - smoothstep(0.0, 1.5, uRevealK - k));
    }
    float occ = smoothstep(0.72, 0.92, s);
    float fre = smoothstep(0.22, 0.42, s) * (1.0 - occ);
    float ao = 0.0;
    vec2 d = uTexel * 4.0;
    ao += occAt(vUv + vec2(d.x, 0.0)) + occAt(vUv - vec2(d.x, 0.0));
    ao += occAt(vUv + vec2(0.0, d.y)) + occAt(vUv - vec2(0.0, d.y));
    ao += occAt(vUv + d) + occAt(vUv - d) + occAt(vUv + vec2(d.x, -d.y)) + occAt(vUv + vec2(-d.x, d.y));
    ao = clamp(ao / 4.0, 0.0, 1.0);
    vec3 col = uFloor;
    // A faint 1 m drafting grid on the floor.
    vec2 g = abs(fract(vWorld.xz) - 0.5);
    float line = 1.0 - smoothstep(0.0, fwidth(vWorld.x) * 1.2, 0.5 - max(g.x, g.y));
    col = mix(col, uGrid, line * uGridAmount);
    col = mix(col, col * 0.62, ao * uAO);
    col = mix(col, uAccent, fresh * 0.06);
    col = mix(col, uWall, occ);
    float alpha = known * max(fre, occ * uWallFlat) * uOpacity;
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(col, alpha);
    #include <colorspace_fragment>
  }
`;

// The endless ground beyond the map: a dot grid that fades with distance, like drafting film.
export const groundFragment = /* glsl */ `
  uniform vec3 uDot;
  uniform vec3 uCentre;
  uniform float uOpacity;
  varying vec3 vWorld;
  void main() {
    vec2 p = vWorld.xz / 2.0;
    vec2 f = abs(fract(p) - 0.5);
    float r = max(0.018, fwidth(p.x) * 0.9);
    float dotMask = 1.0 - smoothstep(r, r + fwidth(p.x) * 1.2, length(vec2(0.5) - f));
    float fade = 1.0 - smoothstep(30.0, 120.0, distance(vWorld.xz, uCentre.xz));
    float a = dotMask * fade * uOpacity * 0.55;
    if (a < 0.01) discard;
    gl_FragColor = vec4(uDot, a);
    #include <colorspace_fragment>
  }
`;

export const wallVertex = /* glsl */ `
  uniform float uHeight;
  varying vec3 vNormal2;
  varying float vH;
  varying vec3 vWorld;
  void main() {
    vec3 p = position;
    vH = p.y;
    p.y *= uHeight;
    vec4 world = modelMatrix * instanceMatrix * vec4(p, 1.0);
    vWorld = world.xyz;
    vNormal2 = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

// Architectural-model walls: lighter caps, a soft gradient down to the floor (an ambient-occlusion feel).
export const wallFragment = /* glsl */ `
  uniform vec3 uSide;
  uniform vec3 uCap;
  uniform vec3 uLight;
  uniform float uOpacity;
  varying vec3 vNormal2;
  varying float vH;
  void main() {
    vec3 n = normalize(vNormal2);
    float lambert = 0.55 + 0.45 * max(dot(n, normalize(uLight)), 0.0);
    float occl = mix(0.42, 1.0, smoothstep(0.0, 0.85, vH));
    vec3 col = uSide * lambert * occl;
    col = mix(col, uCap, step(0.5, n.y));
    gl_FragColor = vec4(col, uOpacity);
    #include <colorspace_fragment>
  }
`;

export const ribbonVertex = /* glsl */ `
  attribute float aDist;
  attribute float aSide;
  attribute float aT;
  varying float vDist;
  varying float vSide;
  varying float vT;
  void main() {
    vDist = aDist;
    vSide = aSide;
    vT = aT;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// A glowing ribbon. Route mode: drawn up to uDraw (metres) with a bright head and pulses moving along it.
// Trail mode: shown up to time uT, fading with age.
export const ribbonFragment = /* glsl */ `
  uniform vec3 uColor;
  uniform float uDraw;
  uniform float uTime;
  uniform float uGlow;
  uniform float uOpacity;
  uniform float uTrail;
  uniform float uT;
  uniform float uFade;
  uniform float uMinAlpha;
  varying float vDist;
  varying float vSide;
  varying float vT;
  void main() {
    float across = abs(vSide);
    float a;
    vec3 col = uColor;
    if (uTrail > 0.5) {
      if (vT > uT || vT < -0.5) discard;
      float age = uT - vT;
      a = max(uMinAlpha, 1.0 - age / uFade);
    } else {
      if (vDist > uDraw) discard;
      float head = 1.0 - smoothstep(0.0, 3.0, uDraw - vDist);
      float pulse = smoothstep(0.85, 1.0, fract((vDist - uTime * 2.2) / 5.0));
      a = 0.85 + 0.15 * pulse;
      col = mix(col, vec3(1.0, 0.95, 0.85), head * 0.6 + pulse * 0.25);
    }
    float edge = uGlow > 0.5 ? pow(1.0 - across, 2.2) * 0.55 : 1.0 - smoothstep(0.75, 1.0, across);
    gl_FragColor = vec4(col, a * edge * uOpacity);
    #include <colorspace_fragment>
  }
`;

export const cloudVertex = /* glsl */ `
  attribute float aT;
  uniform float uT;
  uniform float uSize;
  uniform float uPixelRatio;
  varying float vFresh;
  varying float vShow;
  void main() {
    vShow = step(aT, uT);
    vFresh = vShow * (1.0 - smoothstep(0.0, 6.0, uT - aT));
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = uSize * uPixelRatio * (1.0 + vFresh * 1.6) * (60.0 / -mv.z);
    gl_Position = projectionMatrix * mv;
  }
`;

export const cloudFragment = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uAccent;
  uniform float uOpacity;
  varying float vFresh;
  varying float vShow;
  void main() {
    if (vShow < 0.5) discard;
    vec2 c = gl_PointCoord - 0.5;
    float r = length(c);
    if (r > 0.5) discard;
    float soft = 1.0 - smoothstep(0.15, 0.5, r);
    vec3 col = mix(uColor, uAccent, vFresh);
    gl_FragColor = vec4(col, soft * uOpacity * (0.55 + 0.45 * vFresh));
    #include <colorspace_fragment>
  }
`;
