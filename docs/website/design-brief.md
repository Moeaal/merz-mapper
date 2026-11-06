# Merz Mapper website: design brief

**Status: PROPOSED design, IMPLEMENTED on branch `build/website-v2`.** The website is a demonstrator of the robot's
results (decisions #5, #12), not a project aim. It is the first thing to cut if time is short.

## 1. Concept: "The robot's eyes"
A visitor first sees the building the way the rover saw it: laser returns scattered in the dark, a trajectory glowing
through them, a map growing out of nothing. Then the noise resolves into a calm, precise plan they can use to find a
room. Every visual is driven by the rover's own outputs (map, database, bag, evaluation results), so the site is also
evidence: what you see is what the robot recorded.

Two registers, one system:
- **Night (default): cinematic mission control.** Near-black navy, a single warm signal colour, soft glows, grain.
- **Day: blueprint on paper.** Warm drafting paper, ink-blue linework, the same signal colour burnt down to print strength.

## 2. Mood
Quiet confidence. Dark, deep, spacious; light used as information, never decoration. The accent appears only where
something is *live or important*: the robot, its path, the route, a measured value. If everything glows, nothing does.
Telemetry is precise and slightly technical (monospace, units, tabular figures); headlines are big, architectural
and calm.

Avoid: neon clutter, rainbow data, generic dashboards, Bootstrap cards, stock icons, plain lists with "Next" buttons.

## 3. Palette
One accent (signal amber). Status colours are reserved for objective pass/fail and always carry an icon and a word.
Landmark classes are told apart by **glyph**, not colour. Chart marks use the "mark" steps; text uses the "text" steps.
Checked with the dataviz validator (`validate_palette.js --pairs all`) and WCAG 2.2 contrast.

### Night (dark)
| Token | Hex | Use | Contrast |
| --- | --- | --- | --- |
| `--bg` | `#05080f` | Page, map void | - |
| `--surface` | `#0a101c` | Panels (before glass) | - |
| `--raised` | `#111a2b` | Raised controls | - |
| `--ink` | `#eef1f6` | Primary text | 17.7:1 on bg |
| `--ink-2` | `#9aa6b8` | Secondary text, axes | 8.1:1 on bg, 7.7:1 on surface |
| `--line` | `#1c2840` | Hairlines, grid | decorative |
| `--accent` | `#ffb547` | Accent text, glow core, robot | 11.4:1 on bg |
| `--accent-mark` | `#c47f12` | Route body, chart marks | >= 3:1 (validator) |
| `--pass` / `--pass-mark` | `#6bd3ee` / `#239cbd` | Objective met | 11.0:1 text |
| `--fail` / `--fail-mark` | `#ff7fae` / `#de4a86` | Objective missed | 8.1:1 text |
| `--wall` | `#c9d6ea` | Walls in the map | - |
| `--floor` | `#0e1729` | Explored floor | - |

Validator, dark (surface `#0a101c`): amber/pass/fail marks `#c47f12, #239cbd, #de4a86`: all checks PASS; worst CVD
ΔE 9.5 (deutan), worst normal-vision ΔE 19.6.

### Day (blueprint on paper)
| Token | Hex | Use | Contrast |
| --- | --- | --- | --- |
| `--bg` | `#f3f0e6` | Paper | - |
| `--surface` | `#fbfaf5` | Panels | - |
| `--ink` | `#13233a` | Primary text | 13.9:1 |
| `--ink-2` | `#4a5a72` | Secondary text | 6.2:1 |
| `--blueprint` | `#1d3a7a` | Linework, walls | 9.5:1 |
| `--accent` | `#8f4c06` | Accent text | 5.6:1 |
| `--accent-mark` | `#b4610a` | Route, chart marks | 4.0:1 (graphics need 3:1) |
| `--pass` | `#0b6fa0` | Objective met | 4.9:1 |
| `--fail` | `#c22d64` | Objective missed | 4.8:1 |

Validator, light (surface `#f3f0e6`): `#b4610a, #0b6fa0, #c22d64`: all checks PASS; worst CVD ΔE 9.6, normal 15.6.

Texture: a 2-3 % film-grain overlay (an SVG noise tile) on night surfaces; a faint 8 m / 1 m drafting grid on day.

## 4. Type
All fonts are self-hosted (`@fontsource-variable`, SIL OFL), so the site works offline and on GitHub Pages.
| Role | Face | Settings |
| --- | --- | --- |
| Display | **Archivo** variable, expanded (`wdth 125`) | 800 weight, tracking -0.035em, line-height 0.92 |
| UI / body | **Geist** variable | 400/500/600, tracking -0.01em |
| Telemetry | **Geist Mono** variable | 400/500, tabular figures, uppercase labels tracked +0.12em |

Scale (fluid, `clamp`): Hero 64 → 168 px · H1 40 → 88 · H2 28 → 48 · H3 20 → 24 · Body 16 → 17 · Small 14 ·
Telemetry 11 → 12 (uppercase labels), 13 → 15 (values). Big measured numbers in results: 72 → 144 px display.

## 5. Motion
Motion explains the data: it shows *how* the robot built the map, *where* the route goes, *what* changed.
- **Ease:** `cubic-bezier(0.22, 1, 0.36, 1)` ("expo-out") for entrances; `power2.inOut` for camera moves.
- **Durations:** micro 160 ms · UI 320 ms · reveals 700 ms · camera 1.2-1.8 s · hero intro ~7 s, skippable.
- **Stagger:** 60-80 ms between siblings; never more than 8 items animated at once.
- **Signature moves:** scan points condensing into walls; lines drawing themselves (stroke-dashoffset / growing
  geometry); numbers counting up with tabular figures; camera dollies, never cuts; landmarks appearing with a
  single ripple.
- **Nothing jumps:** layout changes are cross-faded; skeletons match the final layout.
- **Reduced motion:** every sequence has a still end-state; animation is replaced by a 120 ms fade, autoplay is off,
  the camera moves instantly.
- **Performance:** 60 fps target: transforms and opacity only in the DOM; one WebGL canvas, paused when hidden.

## 6. Components
- **Glass panel:** `rgba(10,16,28,0.62)`, `backdrop-filter: blur(18px) saturate(140%)`, 1 px inner hairline
  `rgba(255,255,255,0.08)`, 20 px radius, deep soft shadow. Day: `rgba(251,250,245,0.78)` with blueprint hairline.
- **Telemetry chip:** mono label above a mono value; units in `--ink-2`.
- **Bottom sheet (phone):** three snap points (peek, half, full), drag handle, thumb-reachable controls.
- **Map glyphs:** robot = amber chevron with a soft halo; entrance = pulsing ring ("you are here"); destination =
  amber beacon; room sign = small plate; door, lift, stairs, exit = simple line glyphs drawn for this site.

## 7. References (described as styles, not copied)
1. **Space-mission control visualisations:** a dark void, a single bright object moving along a precise trajectory,
   restrained monospace readouts at the edges, and a timeline you can scrub. Calm, not busy.
2. **Architectural competition boards and blueprints:** expanded grotesk titles, thin precise linework on warm
   paper, generous margins, axonometric views of a floor plate extruded in 3D, scale bars and north arrows.
3. **Cinematic scroll-told product stories:** one idea per screen, large type, the object (here the rover and its
   map) staying centre stage while the camera moves around it as you scroll.

## 8. Accessibility rules
Contrast >= 4.5:1 for text (checked above); touch targets >= 44 px; everything works by keyboard, with visible focus;
each map and chart has a text alternative (step list, data table, summary sentence); live regions announce route
steps and replay events at a calm rate; `prefers-reduced-motion` and `forced-colors` are honoured; WebGL failure
falls back to a 2D map.
