import type { PageContext } from '../main';
import { h, icon } from '../ui/dom';
import { gsap, reveal, revealOnScroll, ScrollTrigger, drawLines } from '../ui/motion';
import { reducedMotion } from '../ui/dom';

// Hardware: only what docs/HARDWARE_REGISTER.md records. The rover base itself is UNKNOWN until it arrives.
const PARTS = [
  { id: 'lidar', icon: 'laser', name: 'RPLIDAR S2', role: 'Spins a laser to measure distance to every wall around it: 10 scans a second. This is what draws the map.', y: 26 },
  { id: 'camera', icon: 'camera', name: 'Logitech C920', role: 'A webcam pointed at door height, for reading the room numbers on signs.', y: 92 },
  { id: 'depth', icon: 'depth', name: 'Intel RealSense D455', role: 'A depth camera: spots signs, doors and lifts, and measures how far away they are. Its motion sensor helps track turning.', y: 150 },
  { id: 'jetson', icon: 'chip', name: 'NVIDIA Jetson Orin Nano', role: 'The on-board computer. Runs the mapping, the sign detector and the text reader, all on the robot.', y: 214 },
  { id: 'base', icon: 'about', name: 'The rover base', role: 'A university-built rover. Its motors and size will be added here once it has been measured.', y: 286 },
];

const PIPELINE = [
  { name: 'SLAM', pkg: 'merz_bringup', text: 'Laser scans and motion become a map, and the robot always knows where it is on it.' },
  { name: 'Perception', pkg: 'merz_perception', text: 'Camera frames become detected signs, doors and lifts, and room numbers read from the signs.' },
  { name: 'Semantic map', pkg: 'merz_semantic_map', text: 'Each detection is placed on the map, and repeated sightings are averaged into one landmark.' },
  { name: 'Access zones', pkg: 'merz_exploration', text: 'From each entrance, a flood fill finds which rooms can be reached without a locked door.' },
  { name: 'Website', pkg: 'web', text: 'This site: routes over the junction graph, with the robot’s own photos at every turn.' },
];

const MEDIA = [
  { file: 'media/rover.jpg', alt: 'The Merz Mapper rover', caption: 'The rover, with its sensor mast.' },
  { file: 'media/sensors.jpg', alt: 'Close-up of the rover’s sensors', caption: 'Lidar, depth camera and sign camera.' },
  { file: 'media/mission.mp4', alt: 'The rover mapping a corridor', caption: 'A mapping run in Merz Court (video).' },
];

export default async function about(ctx: PageContext) {
  const { root } = ctx;
  const exploded = explodedView();
  const pipeline = pipelineView();
  root.append(
    h('section', { class: 'about-hero' },
      h('p', { class: 'eyebrow accent', text: 'About the project' }),
      h('h1', { class: 'display about-title' }, 'Meet the ', h('em', { text: 'rover.' })),
      h('p', { class: 'lede', text: 'Merz Mapper is a final-year engineering project. A small robot explores a university building on its own, builds an accurate map, reads the door signs and works out which rooms can be reached from each entrance. The robot is the project; this website is how its results are shown.' })),
    h('section', { class: 'about-section hardware', 'aria-labelledby': 'hw-title' },
      h('div', { class: 'about-copy', 'data-reveal': true },
        h('p', { class: 'eyebrow', text: '01 · Hardware' }),
        h('h2', { id: 'hw-title', class: 'display-s', text: 'Five parts, one job each.' }),
        h('p', { class: 'muted', text: 'Scroll to take the rover apart. Each sensor answers one question: where are the walls, what is that sign, how far away is it, and where am I?' })),
      exploded),
    h('section', { class: 'about-section', 'aria-labelledby': 'sw-title' },
      h('div', { class: 'about-copy', 'data-reveal': true },
        h('p', { class: 'eyebrow', text: '02 · Software' }),
        h('h2', { id: 'sw-title', class: 'display-s', text: 'From laser light to directions.' }),
        h('p', { class: 'muted', text: 'Five stages, each a ROS 2 package in the repository. Data flows one way: what the robot measures becomes what you see here.' })),
      pipeline),
    h('section', { class: 'about-section', 'aria-labelledby': 'media-title' },
      h('div', { class: 'about-copy', 'data-reveal': true },
        h('p', { class: 'eyebrow', text: '03 · In the building' }),
        h('h2', { id: 'media-title', class: 'display-s', text: 'Photos and video.' }),
        h('p', { class: 'muted', text: 'Real photos of the rover will appear here once it has been built and tested.' })),
      h('div', { class: 'media-grid' }, ...MEDIA.map(mediaSlot))),
    h('section', { class: 'about-section status-section', 'aria-labelledby': 'status-title' },
      h('div', { class: 'about-copy', 'data-reveal': true },
        h('p', { class: 'eyebrow', text: '04 · Honest status' }),
        h('h2', { id: 'status-title', class: 'display-s', text: 'Where the project is now.' })),
      h('ol', { class: 'status-steps', 'data-reveal': true },
        h('li', { class: 'done' }, h('span', { class: 'mono', text: 'Written' }), 'Rover software, evaluation scripts and this website (not yet run on the rover).'),
        h('li', {}, h('span', { class: 'mono', text: 'Next' }), 'Assemble the rover, bring up each sensor, record the first map by driving it by hand.'),
        h('li', {}, h('span', { class: 'mono', text: 'Then' }), 'Explore Merz Court autonomously, one entrance at a time, and measure every objective.'),
        h('li', {}, h('span', { class: 'mono', text: 'Finally' }), 'Replace the synthetic sample data on this site with the rover’s own run, using one command.'))),
    h('footer', { class: 'site-footer' }, h('p', { class: 'small muted', text: 'EEE3094 individual project. Design notes: docs/WEBSITE_DESIGN.md.' })));
  reveal(root.querySelectorAll('.about-hero > *'), 0.05, 0.1);
  revealOnScroll(root);
  animateExploded(exploded);
  animatePipeline(pipeline);

  const scene = await ctx.scene();
  if (scene) {
    scene.setRoute(null); scene.setTrail(null); scene.setRobot(null); scene.setScan(null); scene.setGraph(null); scene.showEllipse(null);
    scene.setCloudState(0, 0); scene.eyeBlend = 0;
    scene.setWalls(true, 900);
    scene.overview(1.05, 1800, 0.6);
    const release = scene.hold();
    const spin = scene.onFrame(() => { scene.rig.az += 0.0003; });
    return () => { release(); spin(); };
  }
}

function explodedView() {
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('viewBox', '0 0 360 340');
  svg.setAttribute('class', 'exploded-svg');
  svg.setAttribute('aria-hidden', 'true');
  // Simple, honest outlines: the real rover's shape is not known yet.
  svg.innerHTML = `
    <g class="ex-part" data-part="lidar"><ellipse cx="180" cy="34" rx="34" ry="10"/><path d="M146 34v12a34 10 0 0 0 68 0V34"/><circle cx="180" cy="34" r="4" class="ex-accent"/></g>
    <g class="ex-part" data-part="camera"><rect x="150" y="84" width="60" height="18" rx="9"/><circle cx="180" cy="93" r="5" class="ex-accent"/></g>
    <g class="ex-part" data-part="depth"><rect x="128" y="140" width="104" height="22" rx="6"/><circle cx="146" cy="151" r="5"/><circle cx="214" cy="151" r="5"/><circle cx="180" cy="151" r="3" class="ex-accent"/></g>
    <g class="ex-part" data-part="jetson"><rect x="132" y="200" width="96" height="30" rx="4"/><path d="M146 200v-6M162 200v-6M178 200v-6M194 200v-6M210 200v-6"/><rect x="160" y="208" width="40" height="14" rx="2" class="ex-accent-fill"/></g>
    <g class="ex-part" data-part="base"><rect x="96" y="262" width="168" height="40" rx="10"/><circle cx="122" cy="310" r="16"/><circle cx="238" cy="310" r="16"/><circle cx="122" cy="310" r="5"/><circle cx="238" cy="310" r="5"/></g>`;
  const labels = h('ol', { class: 'ex-labels' }, ...PARTS.map((p) => h('li', { 'data-part': p.id },
    h('span', { class: 'ex-icon', icon: p.icon as any }),
    h('div', {}, h('p', { class: 'ex-name', text: p.name }), h('p', { class: 'ex-role', text: p.role })))));
  return h('div', { class: 'exploded' }, h('div', { class: 'ex-figure glass' }, svg as unknown as HTMLElement), labels);
}

function animateExploded(root: HTMLElement) {
  const parts = root.querySelectorAll<SVGGElement>('.ex-part');
  const labels = root.querySelectorAll('.ex-labels li');
  if (reducedMotion()) return;
  // Start assembled; separate the layers as the section scrolls through.
  const offsets: Record<string, number> = { lidar: 70, camera: 34, depth: 8, jetson: -18, base: -40 };
  parts.forEach((p) => gsap.set(p, { y: offsets[p.dataset.part!] }));
  gsap.to(parts, {
    y: 0, ease: 'none', stagger: 0,
    scrollTrigger: { trigger: root, start: 'top 75%', end: 'center 45%', scrub: 0.8 },
  });
  gsap.fromTo(labels, { opacity: 0, x: 24 }, { opacity: 1, x: 0, stagger: 0.12, duration: 0.8,
    scrollTrigger: { trigger: root, start: 'top 60%', once: true } });
}

function pipelineView() {
  const items = PIPELINE.map((p, i) => h('li', { class: 'pipe-node glass' },
    h('span', { class: 'pipe-n mono', text: String(i + 1).padStart(2, '0') }),
    h('p', { class: 'pipe-name', text: p.name }),
    h('p', { class: 'pipe-text', text: p.text }),
    h('p', { class: 'pipe-pkg mono', text: p.pkg })));
  const flow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  flow.setAttribute('class', 'pipe-flow');
  flow.setAttribute('viewBox', '0 0 1000 20');
  flow.setAttribute('aria-hidden', 'true');
  return h('div', { class: 'pipeline' }, flow as unknown as HTMLElement, h('ol', { class: 'pipe-list' }, ...items));
}

function animatePipeline(root: HTMLElement) {
  const svg = root.querySelector('svg')!;
  svg.innerHTML = '<path d="M0 10 H1000" class="pipe-line"/><path d="M0 10 H1000" class="pipe-dash"/>';
  const nodes = root.querySelectorAll('.pipe-node');
  ScrollTrigger.create({
    trigger: root, start: 'top 70%', once: true,
    onEnter: () => {
      drawLines([svg.querySelector('.pipe-line') as SVGGeometryElement], 1.6, 0);
      if (!reducedMotion()) gsap.fromTo(nodes, { opacity: 0, y: 30 }, { opacity: 1, y: 0, stagger: 0.16, duration: 0.9 });
    },
  });
}

function mediaSlot(item: { file: string; alt: string; caption: string }) {
  const frame = h('div', { class: 'media-frame' }, h('div', { class: 'media-empty' }, icon(item.file.endsWith('.mp4') ? 'mission' : 'camera'),
    h('span', { text: item.file.endsWith('.mp4') ? 'Video to follow' : 'Photo to follow' })));
  const figure = h('figure', { class: 'media', 'data-reveal': true }, frame, h('figcaption', { class: 'small muted', text: item.caption }));
  // Real media is picked up automatically when the files are added to web/frontend/public/media/.
  if (item.file.endsWith('.mp4')) {
    const video = h('video', { src: item.file, controls: true, muted: true, playsinline: true, preload: 'metadata', 'aria-label': item.alt });
    video.addEventListener('loadedmetadata', () => { frame.replaceChildren(video); figure.classList.add('filled'); }, { once: true });
  } else {
    const img = new Image();
    img.onload = () => { img.alt = item.alt; frame.replaceChildren(img); figure.classList.add('filled'); };
    img.src = item.file;
  }
  return figure;
}
