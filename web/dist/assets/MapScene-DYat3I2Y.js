import{Scene as _,PerspectiveCamera as B,Group as j,Clock as I,WebGLRenderer as N,ShaderMaterial as S,Color as v,Mesh as x,PlaneGeometry as D,LinearFilter as K,LinearMipmapLinearFilter as X,NearestFilter as H,Vector2 as y,NormalBlending as P,AdditiveBlending as F,MeshBasicMaterial as W,Vector3 as M,MathUtils as G,Raycaster as Y,Plane as Z,BoxGeometry as q,InstancedMesh as J,Matrix4 as Q,BufferGeometry as z,Float32BufferAttribute as b,Shape as $,ShapeGeometry as tt,Sprite as et,SpriteMaterial as it,CanvasTexture as ot,LineSegments as L,LineBasicMaterial as k,Points as U,PointsMaterial as rt,BufferAttribute as E,RingGeometry as st,DoubleSide as at}from"./three-DdJfuIKW.js";import{p as nt}from"./index-CnpOjQDe.js";import"./gsap-DjKJqAo0.js";const V=`
  varying vec2 vUv;
  varying vec3 vWorld;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`,lt=`
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
      fresh = known * (1.0 - smoothstep(0.0, 4.0, uRevealK - k));
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
    col = mix(col, uAccent, fresh * 0.45);
    col = mix(col, uWall, occ);
    float alpha = known * max(fre, occ * uWallFlat) * uOpacity;
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(col, alpha);
  }
`,ht=`
  uniform vec3 uDot;
  uniform vec3 uCentre;
  uniform float uOpacity;
  varying vec3 vWorld;
  void main() {
    vec2 p = vWorld.xz / 2.0;
    vec2 f = abs(fract(p) - 0.5);
    float dotMask = 1.0 - smoothstep(0.035, 0.035 + fwidth(p.x) * 1.5, length(vec2(0.5) - f));
    float fade = 1.0 - smoothstep(30.0, 120.0, distance(vWorld.xz, uCentre.xz));
    float a = dotMask * fade * uOpacity;
    if (a < 0.01) discard;
    gl_FragColor = vec4(uDot, a);
  }
`,ut=`
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
`,ct=`
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
  }
`,dt=`
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
`,mt=`
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
  }
`,ft=`
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
`,vt=`
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
  }
`,pt=2.4,T=(p,t,i=0)=>new M(p,i,-t);function w(p){const t=getComputedStyle(document.documentElement).getPropertyValue(p).trim();return new v(t||"#ffffff")}function yt(p){return p<.5?4*p*p*p:1-Math.pow(-2*p+2,3)/2}class Mt{constructor(t,i,o){this.host=t,this.bundle=i,this.scene=new _,this.camera=new B(34,1,.1,2e3),this.rig={x:0,y:0,dist:80,tilt:0,az:0},this.eye=null,this.eyeBlend=0,this.walls=null,this.route=null,this.trail=null,this.cloud=null,this.robot=new j,this.rays=null,this.hits=null,this.ellipse=null,this.graphLines=null,this.clock=new I,this.tweens=[],this.listeners=new Set,this.running=!0,this.continuous=0,this.dirty=!0,this.wallHeight=0,this.reducedMotion=matchMedia("(prefers-reduced-motion: reduce)").matches,this.onVisibility=()=>{this.running=!document.hidden,this.running&&(this.clock.getDelta(),this.loop())},this.resize=()=>{const l=this.host.clientWidth||window.innerWidth,h=this.host.clientHeight||window.innerHeight;this.renderer.setSize(l,h,!1),this.camera.aspect=l/h,this.camera.updateProjectionMatrix(),this.dirty=!0},this.loop=()=>{if(!this.running)return;requestAnimationFrame(this.loop);const l=performance.now();if(this.tweens.length&&(this.tweens=this.tweens.filter(c=>c.update(l)),this.dirty=!0),!this.dirty&&!this.continuous)return;const h=this.clock.getElapsedTime();this.route&&(this.route.core.material.uniforms.uTime.value=h,this.route.glow.material.uniforms.uTime.value=h),this.robot.children[1]?.scale.setScalar(1+.12*Math.sin(h*3)),this.updateCamera(),this.renderer.render(this.scene,this.camera);for(const c of this.listeners)c();this.dirty=!1},this.renderer=new N({antialias:!0,alpha:!0,powerPreference:"high-performance"}),this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2)),this.renderer.setClearColor(0,0),t.appendChild(this.renderer.domElement),this.renderer.domElement.setAttribute("aria-hidden","true");const e=i.manifest.map,s=e.width*e.resolution,r=e.height*e.resolution;this.centre={x:e.origin[0]+s/2,y:e.origin[1]+r/2,w:s,h:r};const a=new S({vertexShader:V,fragmentShader:ht,transparent:!0,depthWrite:!1,uniforms:{uDot:{value:new v},uCentre:{value:T(this.centre.x,this.centre.y)},uOpacity:{value:1}}});this.ground=new x(new D(600,600),a),this.ground.rotation.x=-Math.PI/2,this.ground.position.copy(T(this.centre.x,this.centre.y,-.02)),this.scene.add(this.ground),o.state.magFilter=K,o.state.minFilter=X,o.state.anisotropy=this.renderer.capabilities.getMaxAnisotropy();const n=o.reveal??o.state;n.magFilter=H,n.minFilter=H,n.generateMipmaps=!1;const u=new S({vertexShader:V,fragmentShader:lt,transparent:!0,depthWrite:!1,uniforms:{tState:{value:o.state},tReveal:{value:n},uRevealK:{value:999},uHasReveal:{value:o.reveal?1:0},uFloor:{value:new v},uWall:{value:new v},uAccent:{value:new v},uGrid:{value:new v},uTexel:{value:new y(1/e.width,1/e.height)},uOpacity:{value:1},uAO:{value:0},uWallFlat:{value:1},uGridAmount:{value:.35}}});this.floor=new x(new D(s,r),u),this.floor.rotation.x=-Math.PI/2,this.floor.position.copy(T(this.centre.x,this.centre.y,0)),this.floor.renderOrder=1,this.scene.add(this.floor),this.buildRobot(),this.applyTheme(),this.resize(),window.addEventListener("resize",this.resize),document.addEventListener("visibilitychange",this.onVisibility),this.loop()}onFrame(t){return this.listeners.add(t),()=>this.listeners.delete(t)}hold(){return this.continuous++,()=>{this.continuous=Math.max(0,this.continuous-1)}}invalidate(){this.dirty=!0}applyTheme(){const t=document.documentElement.dataset.theme||"dark",i=this.floor.material.uniforms;if(i.uFloor.value.copy(w("--floor")),i.uWall.value.copy(w("--wall")),i.uAccent.value.copy(w("--accent")),i.uGrid.value.copy(w("--line-strong")),i.uGridAmount.value=t==="light"?.55:.4,this.ground.material.uniforms.uDot.value.copy(w("--line-strong")),this.walls){const r=this.walls.material.uniforms;r.uSide.value.copy(t==="light"?new v("#e9e4d4"):new v("#2a3a58")),r.uCap.value.copy(w("--wall"))}const o=w("--accent-mark"),e=w("--accent");for(const r of[this.route,this.trail])r&&(r.core.material.uniforms.uColor.value.copy(t==="light"?o:e),r.glow.material.uniforms.uColor.value.copy(o));this.cloud&&(this.cloud.material.uniforms.uColor.value.copy(w("--cloud")),this.cloud.material.uniforms.uAccent.value.copy(e),this.cloud.material.blending=t==="light"?P:F),this.robot.children[0].material=new W({color:e}),this.robot.children[1].material.color.copy(o),this.rays&&this.rays.material.color.copy(e),this.hits&&this.hits.material.color.copy(e),this.ellipse&&this.ellipse.material.color.copy(e),this.graphLines&&this.graphLines.material.color.copy(e),this.dirty=!0}updateCamera(){const t=this.rig,i=T(t.x,t.y,0),o=t.dist*Math.sin(t.tilt),e=new M(i.x+Math.sin(t.az)*o,t.dist*Math.cos(t.tilt),i.z+Math.cos(t.az)*o),r=new M(-Math.sin(t.az),0,-Math.cos(t.az)).lerp(new M(0,1,0),G.smoothstep(t.tilt,0,.25)).normalize();if(this.eye&&this.eyeBlend>0){const a=this.eye,n=this.eyeBlend;e.lerp(T(a.px,a.py,a.ph),n),i.lerp(T(a.tx,a.ty,a.th),n),r.lerp(new M(0,1,0),n).normalize()}this.camera.position.copy(e),this.camera.up.copy(r),this.camera.lookAt(i)}tween(t,i,o){if(this.reducedMotion||t<=0){i(1),o?.(),this.dirty=!0;return}const e=performance.now();this.tweens.push({update:s=>{const r=Math.min(1,(s-e)/t);return i(yt(r)),r>=1?(o?.(),!1):!0}}),this.dirty=!0}stopTweens(){this.tweens=[]}flyTo(t,i=1400,o){const e={...this.rig},s={...this.rig,...t};let r=s.az-e.az;r=Math.atan2(Math.sin(r),Math.cos(r)),this.stopTweens(),this.tween(i,a=>{this.rig.x=e.x+(s.x-e.x)*a,this.rig.y=e.y+(s.y-e.y)*a,this.rig.dist=Math.exp(Math.log(e.dist)+(Math.log(s.dist)-Math.log(e.dist))*a),this.rig.tilt=e.tilt+(s.tilt-e.tilt)*a,this.rig.az=e.az+r*a},o)}fitDistance(t,i,o=80,e=this.rig.tilt){const s=G.degToRad(this.camera.fov),r=this.renderer.domElement.clientWidth||window.innerWidth,a=this.renderer.domElement.clientHeight||window.innerHeight,n=r/Math.max(1,r-o*2),u=a/Math.max(1,a-o*2),l=i*u/2/Math.tan(s/2),h=t*n/2/Math.tan(s/2)/this.camera.aspect;return Math.max(l,h)*(1+Math.sin(e)*.35)}fit(t,i={}){const o=t.map(m=>m[0]),e=t.map(m=>m[1]),s=Math.min(...o),r=Math.max(...o),a=Math.min(...e),n=Math.max(...e),u=i.az??this.rig.az,l=Math.cos(u),h=Math.sin(u),c=[[s,a],[r,a],[s,n],[r,n]].map(([m,R])=>[m*l-R*h,m*h+R*l]),d=Math.max(...c.map(m=>m[0]))-Math.min(...c.map(m=>m[0])),C=Math.max(...c.map(m=>m[1]))-Math.min(...c.map(m=>m[1])),g=i.tilt??this.rig.tilt,A=Math.max(8,this.fitDistance(Math.max(d,4),Math.max(C,4),i.padding??90,g)),f=(i.offsetX??0)*A,O=(i.offsetY??0)*A;this.flyTo({x:(s+r)/2-(f*l+O*h),y:(a+n)/2-(-f*h+O*l),dist:A,tilt:g,az:u},i.duration??1400)}overview(t=0,i=1400,o=0){const e=this.bundle.manifest.map,s=[[e.origin[0],e.origin[1]],[e.origin[0]+e.width*e.resolution,e.origin[1]+e.height*e.resolution]];this.fit(s,{tilt:t,az:o,duration:i,padding:40})}project(t,i,o=0){const e=T(t,i,o).project(this.camera);if(e.z>1)return null;const s=this.renderer.domElement,r=(e.x*.5+.5)*s.clientWidth,a=(-e.y*.5+.5)*s.clientHeight;return{x:r,y:a,visible:e.x>-1.2&&e.x<1.2&&e.y>-1.2&&e.y<1.2}}unproject(t,i){const o=this.renderer.domElement,e=new y(t/o.clientWidth*2-1,-(i/o.clientHeight)*2+1),s=new Y;s.setFromCamera(e,this.camera);const r=new M;return s.ray.intersectPlane(new Z(new M(0,1,0),0),r)?[r.x,-r.z]:null}async ensureWalls(){if(this.walls)return;const t=await fetch(this.bundle.url(this.bundle.manifest.map.walls)).then(r=>r.json()),i=new q(1,1,1);i.translate(0,.5,0);const o=new S({vertexShader:ut,fragmentShader:ct,transparent:!0,uniforms:{uHeight:{value:.001},uSide:{value:new v},uCap:{value:new v},uLight:{value:new M(.5,.8,.3)},uOpacity:{value:1}}}),e=new J(i,o,t.length),s=new Q;t.forEach(([r,a,n,u],l)=>{s.makeScale(Math.max(n-r,.05),pt,Math.max(u-a,.05)),s.setPosition((r+n)/2,0,-(a+u)/2),e.setMatrixAt(l,s)}),e.instanceMatrix.needsUpdate=!0,e.frustumCulled=!1,e.visible=!1,e.renderOrder=2,this.walls=e,this.scene.add(e),this.applyTheme()}async setWalls(t,i=1100){if(t&&await this.ensureWalls(),!this.walls)return;const o=this.walls,e=this.wallHeight,s=t?1:0;o.visible=!0;const r=this.floor.material.uniforms;this.tween(i,a=>{this.wallHeight=e+(s-e)*a,o.material.uniforms.uHeight.value=Math.max(.001,this.wallHeight),r.uAO.value=this.wallHeight,r.uWallFlat.value=1-this.wallHeight*.85},()=>{o.visible=this.wallHeight>.01})}ribbonGeometry(t,i,o){const e=[],s=[],r=[],a=[],n=[];let u=0;for(let h=0;h<t.length;h++){const c=t[h],d=t[Math.max(0,h-1)],C=t[Math.min(t.length-1,h+1)];h>0&&(u+=c.distanceTo(d));const g=new y().subVectors(C,d);g.lengthSq()<1e-9&&g.set(1,0),g.normalize();const A=new y(-g.y,g.x).multiplyScalar(i/2);for(const f of[-1,1])e.push(c.x+A.x*f,.04,-(c.y+A.y*f)),s.push(u),r.push(f),a.push(o?o[h]:0);if(h>0){const f=(h-1)*2;n.push(f,f+1,f+2,f+1,f+3,f+2)}}const l=new z;return l.setAttribute("position",new b(e,3)),l.setAttribute("aDist",new b(s,1)),l.setAttribute("aSide",new b(r,1)),l.setAttribute("aT",new b(a,1)),l.setIndex(n),{geometry:l,total:u}}ribbonMaterial(t,i){return new S({vertexShader:dt,fragmentShader:mt,transparent:!0,depthWrite:!1,blending:t&&document.documentElement.dataset.theme!=="light"?F:P,uniforms:{uColor:{value:new v},uDraw:{value:0},uTime:{value:0},uGlow:{value:t?1:0},uOpacity:{value:1},uTrail:{value:i?1:0},uT:{value:0},uFade:{value:120},uMinAlpha:{value:.3}}})}densify(t,i=.25){const o=[];for(let e=0;e<t.length-1;e++){const s=new y(...t[e]),r=new y(...t[e+1]),a=Math.max(1,Math.ceil(s.distanceTo(r)/i));for(let n=0;n<a;n++)o.push(s.clone().lerp(r,n/a))}return o.push(new y(...t[t.length-1])),o}setRoute(t){if(this.route&&(this.scene.remove(this.route.core,this.route.glow),this.route.core.geometry.dispose(),this.route.glow.geometry.dispose(),this.route=null),!t||t.length<2)return this.dirty=!0,0;const i=this.densify(t),o=this.ribbonGeometry(i,.32),e=this.ribbonGeometry(i,2.4),s=new x(o.geometry,this.ribbonMaterial(!1,!1)),r=new x(e.geometry,this.ribbonMaterial(!0,!1));return s.renderOrder=5,r.renderOrder=4,this.route={core:s,glow:r,length:o.total},this.scene.add(r,s),this.applyTheme(),o.total}drawRoute(t=1800,i=0){if(!this.route)return;const o=this.route;this.tween(t,e=>{const s=i+(o.length-i)*e+.01;o.core.material.uniforms.uDraw.value=s,o.glow.material.uniforms.uDraw.value=s})}routeLength(){return this.route?.length??0}setTrail(t,i=120,o=.3){if(this.trail&&(this.scene.remove(this.trail.core,this.trail.glow),this.trail=null),!t)return;const e=[],s=[];let r=null;for(const d of t)r&&Math.hypot(d[1]-r[1],d[2]-r[2])>2&&(e.push(new y(r[1],r[2]),new y(d[1],d[2])),s.push(-1,-1)),e.push(new y(d[1],d[2])),s.push(d[0]),r=d;const a=this.ribbonGeometry(e,.14,s),n=this.ribbonGeometry(e,1.1,s),u=this.ribbonMaterial(!1,!0),l=this.ribbonMaterial(!0,!0);for(const d of[u,l])d.uniforms.uFade.value=i,d.uniforms.uMinAlpha.value=o;l.uniforms.uMinAlpha.value=o*.3;const h=new x(a.geometry,u),c=new x(n.geometry,l);h.renderOrder=6,c.renderOrder=5,this.trail={core:h,glow:c},this.scene.add(c,h),this.applyTheme()}setTrailTime(t){this.trail&&(this.trail.core.material.uniforms.uT.value=t,this.trail.glow.material.uniforms.uT.value=t,this.dirty=!0)}buildRobot(){const t=new $;t.moveTo(.55,0),t.lineTo(-.35,.34),t.lineTo(-.18,0),t.lineTo(-.35,-.34),t.closePath();const i=new x(new tt(t),new W);i.rotation.x=-Math.PI/2,i.position.y=.12;const o=document.createElement("canvas");o.width=o.height=128;const e=o.getContext("2d"),s=e.createRadialGradient(64,64,0,64,64,64);s.addColorStop(0,"rgba(255,255,255,0.9)"),s.addColorStop(.25,"rgba(255,255,255,0.35)"),s.addColorStop(1,"rgba(255,255,255,0)"),e.fillStyle=s,e.fillRect(0,0,128,128);const r=new et(new it({map:new ot(o),transparent:!0,depthWrite:!1,blending:F}));r.position.y=.1,r.scale.setScalar(3.2),this.robot.add(i,r),this.robot.visible=!1,this.robot.renderOrder=8,this.scene.add(this.robot)}setRobot(t){this.robot.visible=!!t,t&&(this.robot.position.set(t.x,0,-t.y),this.robot.children[0].rotation.z=t.yaw),this.dirty=!0}setScan(t,i,o=0,e=0){if(!t||!i){this.rays&&(this.rays.visible=!1),this.hits&&(this.hits.visible=!1),this.dirty=!0;return}const s=i.length;if(!this.rays){const u=new z;u.setAttribute("position",new b(new Float32Array(s*6),3)),this.rays=new L(u,new k({transparent:!0,opacity:.16,blending:F,depthWrite:!1}));const l=new z;l.setAttribute("position",new b(new Float32Array(s*3),3)),this.hits=new U(l,new rt({size:3.2,sizeAttenuation:!1,transparent:!0,opacity:.95,depthWrite:!1})),this.rays.renderOrder=7,this.hits.renderOrder=7,this.scene.add(this.rays,this.hits),this.applyTheme()}const r=this.rays.geometry.getAttribute("position"),a=this.hits.geometry.getAttribute("position");let n=0;for(let u=0;u<s;u++){const l=i[u]/100;if(l<=.05)continue;const h=t.yaw+o+u*e,c=t.x+Math.cos(h)*l,d=t.y+Math.sin(h)*l;r.setXYZ(n*2,t.x,.3,-t.y),r.setXYZ(n*2+1,c,.3,-d),a.setXYZ(n,c,.3,-d),n++}this.rays.geometry.setDrawRange(0,n*2),this.hits.geometry.setDrawRange(0,n),r.needsUpdate=!0,a.needsUpdate=!0,this.rays.visible=!0,this.hits.visible=!0,this.dirty=!0}setCloud(t){if(this.cloud&&(this.scene.remove(this.cloud),this.cloud=null),!t)return;const i=t.length/3,o=new Float32Array(i*3),e=new Float32Array(i);for(let a=0;a<i;a++)o[a*3]=t[a*3]/100,o[a*3+1]=.08,o[a*3+2]=-t[a*3+1]/100,e[a]=(t[a*3+2]+32768)/10;const s=new z;s.setAttribute("position",new E(o,3)),s.setAttribute("aT",new E(e,1));const r=new S({vertexShader:ft,fragmentShader:vt,transparent:!0,depthWrite:!1,blending:F,uniforms:{uT:{value:0},uSize:{value:2.2},uPixelRatio:{value:this.renderer.getPixelRatio()},uColor:{value:new v},uAccent:{value:new v},uOpacity:{value:1}}});this.cloud=new U(s,r),this.cloud.renderOrder=3,this.cloud.frustumCulled=!1,this.scene.add(this.cloud),this.applyTheme()}setCloudState(t,i=1){this.cloud&&(this.cloud.material.uniforms.uT.value=t,this.cloud.material.uniforms.uOpacity.value=i,this.cloud.visible=i>.01,this.dirty=!0)}setReveal(t){this.floor.material.uniforms.uRevealK.value=t,this.dirty=!0}setMapOpacity(t){this.floor.material.uniforms.uOpacity.value=t,this.dirty=!0}setGroundOpacity(t){this.ground.material.uniforms.uOpacity.value=t,this.dirty=!0}showEllipse(t){if(!t){this.ellipse&&(this.ellipse.visible=!1),this.dirty=!0;return}this.ellipse||(this.ellipse=new x(new st(.94,1,96),new W({transparent:!0,opacity:.95,depthWrite:!1,side:at})),this.ellipse.rotation.x=-Math.PI/2,this.ellipse.renderOrder=9,this.scene.add(this.ellipse),this.applyTheme()),this.ellipse.scale.set(Math.max(.08,t.sd[0]*2.45),Math.max(.08,t.sd[1]*2.45),1),this.ellipse.position.set(t.x,.06,-t.y),this.ellipse.visible=!0,this.dirty=!0}setGraph(t){if(this.graphLines&&(this.scene.remove(this.graphLines),this.graphLines=null),!t){this.dirty=!0;return}const i=[];for(const[[e,s],[r,a]]of t)i.push(e,.06,-s,r,.06,-a);const o=new z;o.setAttribute("position",new b(i,3)),this.graphLines=new L(o,new k({transparent:!0,opacity:.75})),this.graphLines.renderOrder=6,this.scene.add(this.graphLines),this.applyTheme()}route2points(t,i){return[[i.x,i.y],...t.steps.map(o=>[o.x,o.y]),[t.destination.x,t.destination.y]]}poseAt(t,i){return nt(t,i)}}export{Mt as MapScene};
