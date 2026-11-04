import{Scene as rt,PerspectiveCamera as at,Group as st,Clock as nt,WebGLRenderer as lt,ShaderMaterial as A,Color as m,Mesh as g,PlaneGeometry as N,LinearFilter as ht,LinearMipmapLinearFilter as ct,NearestFilter as K,Vector2 as p,NormalBlending as X,AdditiveBlending as S,MeshBasicMaterial as D,Vector3 as x,MathUtils as P,Raycaster as ut,Plane as dt,BoxGeometry as mt,InstancedMesh as ft,Matrix4 as vt,BufferGeometry as W,Float32BufferAttribute as b,DoubleSide as Y,Shape as pt,ShapeGeometry as yt,Sprite as wt,SpriteMaterial as gt,CanvasTexture as xt,LineSegments as Z,LineBasicMaterial as q,Points as J,PointsMaterial as Mt,BufferAttribute as Q,RingGeometry as bt}from"./three-DdJfuIKW.js";import{p as Tt}from"./index-9NhEqVB4.js";import"./gsap-DjKJqAo0.js";const $=`
  varying vec2 vUv;
  varying vec3 vWorld;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`,At=`
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
`,St=`
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
`,Wt=`
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
`,Ft=`
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
`,zt=`
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
`,Ct=`
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
`,Ot=`
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
`,Ht=`
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
`,Rt=1.8,T=(v,t,i=0)=>new x(v,i,-t);function y(v){const t=getComputedStyle(document.documentElement).getPropertyValue(v).trim();return new m(t||"#ffffff")}function Dt(v){return v<.5?4*v*v*v:1-Math.pow(-2*v+2,3)/2}class kt{constructor(t,i,o){this.host=t,this.bundle=i,this.scene=new rt,this.camera=new at(34,1,.1,2e3),this.rig={x:0,y:0,dist:80,tilt:0,az:0},this.eye=null,this.eyeBlend=0,this.walls=null,this.route=null,this.trail=null,this.cloud=null,this.robot=new st,this.rays=null,this.hits=null,this.ellipse=null,this.graphLines=null,this.clock=new nt,this.tweens=[],this.listeners=new Set,this.running=!0,this.continuous=0,this.dirty=!0,this.wallHeight=0,this.reducedMotion=matchMedia("(prefers-reduced-motion: reduce)").matches,this.onVisibility=()=>{this.running=!document.hidden,this.running&&(this.clock.getDelta(),this.loop())},this.resize=()=>{const h=this.host.clientWidth||window.innerWidth,l=this.host.clientHeight||window.innerHeight;this.renderer.setSize(h,l,!1),this.camera.aspect=h/l,this.camera.updateProjectionMatrix(),this.dirty=!0},this.loop=()=>{if(!this.running)return;requestAnimationFrame(this.loop);const h=performance.now();if(this.tweens.length&&(this.tweens=this.tweens.filter(d=>d.update(h)),this.dirty=!0),!this.dirty&&!this.continuous)return;const l=this.clock.getElapsedTime();this.route&&(this.route.core.material.uniforms.uTime.value=l,this.route.glow.material.uniforms.uTime.value=l),this.robot.children[1]?.scale.setScalar(1+.12*Math.sin(l*3)),this.updateCamera(),this.renderer.render(this.scene,this.camera);for(const d of this.listeners)d();this.dirty=!1},this.renderer=new lt({antialias:!0,alpha:!0,powerPreference:"high-performance"}),this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2)),this.renderer.setClearColor(0,0),t.appendChild(this.renderer.domElement),this.renderer.domElement.setAttribute("aria-hidden","true");const e=i.manifest.map,a=e.width*e.resolution,r=e.height*e.resolution;this.centre={x:e.origin[0]+a/2,y:e.origin[1]+r/2,w:a,h:r};const s=new A({vertexShader:$,fragmentShader:St,transparent:!0,depthWrite:!1,uniforms:{uDot:{value:new m},uCentre:{value:T(this.centre.x,this.centre.y)},uOpacity:{value:1}}});this.ground=new g(new N(600,600),s),this.ground.rotation.x=-Math.PI/2,this.ground.position.copy(T(this.centre.x,this.centre.y,-.02)),this.scene.add(this.ground),o.state.magFilter=ht,o.state.minFilter=ct,o.state.anisotropy=this.renderer.capabilities.getMaxAnisotropy();const n=o.reveal??o.state;n.magFilter=K,n.minFilter=K,n.generateMipmaps=!1;const c=new A({vertexShader:$,fragmentShader:At,transparent:!0,depthWrite:!1,uniforms:{tState:{value:o.state},tReveal:{value:n},uRevealK:{value:999},uHasReveal:{value:o.reveal?1:0},uFloor:{value:new m},uWall:{value:new m},uAccent:{value:new m},uGrid:{value:new m},uTexel:{value:new p(1/e.width,1/e.height)},uOpacity:{value:1},uAO:{value:0},uWallFlat:{value:1},uGridAmount:{value:.35}}});this.floor=new g(new N(a,r),c),this.floor.rotation.x=-Math.PI/2,this.floor.position.copy(T(this.centre.x,this.centre.y,0)),this.floor.renderOrder=1,this.scene.add(this.floor),this.buildRobot(),this.applyTheme(),this.resize(),window.addEventListener("resize",this.resize),document.addEventListener("visibilitychange",this.onVisibility),this.loop()}onFrame(t){return this.listeners.add(t),()=>this.listeners.delete(t)}hold(){return this.continuous++,()=>{this.continuous=Math.max(0,this.continuous-1)}}invalidate(){this.dirty=!0}applyTheme(){const t=document.documentElement.dataset.theme||"dark",i=this.floor.material.uniforms;if(i.uFloor.value.copy(y("--floor")),i.uWall.value.copy(y("--wall")),i.uAccent.value.copy(y("--accent")),i.uGrid.value.copy(y("--line-strong")),i.uGridAmount.value=t==="light"?.55:.4,this.ground.material.uniforms.uDot.value.copy(y("--line-strong")),this.walls){const r=this.walls.material.uniforms;r.uSide.value.copy(t==="light"?new m("#e6e0cd"):new m("#3b4f74")),r.uCap.value.copy(y("--wall"))}const o=y("--accent-mark"),e=y("--accent");for(const r of[this.route,this.trail])r&&(r.core.material.uniforms.uColor.value.copy(t==="light"?o:e),r.glow.material.uniforms.uColor.value.copy(o));this.cloud&&(this.cloud.material.uniforms.uColor.value.copy(y("--cloud")),this.cloud.material.uniforms.uAccent.value.copy(e),this.cloud.material.blending=t==="light"?X:S),this.robot.children[0].material=new D({color:e}),this.robot.children[1].material.color.copy(o),this.rays&&this.rays.material.color.copy(e),this.hits&&this.hits.material.color.copy(e),this.ellipse&&this.ellipse.material.color.copy(e),this.graphLines&&this.graphLines.material.color.copy(e),this.dirty=!0}updateCamera(){const t=this.rig,i=T(t.x,t.y,0),o=t.dist*Math.sin(t.tilt),e=new x(i.x+Math.sin(t.az)*o,t.dist*Math.cos(t.tilt),i.z+Math.cos(t.az)*o),r=new x(-Math.sin(t.az),0,-Math.cos(t.az)).lerp(new x(0,1,0),P.smoothstep(t.tilt,0,.25)).normalize();if(this.eye&&this.eyeBlend>0){const s=this.eye,n=this.eyeBlend;e.lerp(T(s.px,s.py,s.ph),n),i.lerp(T(s.tx,s.ty,s.th),n),r.lerp(new x(0,1,0),n).normalize()}this.camera.position.copy(e),this.camera.up.copy(r),this.camera.lookAt(i)}tween(t,i,o,e="misc"){if(this.reducedMotion||t<=0){i(1),o?.(),this.dirty=!0;return}const a=performance.now();e!=="misc"&&(this.tweens=this.tweens.filter(r=>r.channel!==e)),this.tweens.push({channel:e,update:r=>{const s=Math.min(1,(r-a)/t);return i(Dt(s)),s>=1?(o?.(),!1):!0}}),this.dirty=!0}stopTweens(t="camera"){this.tweens=this.tweens.filter(i=>i.channel!==t)}flyTo(t,i=1400,o){const e={...this.rig},a={...this.rig,...t};let r=a.az-e.az;r=Math.atan2(Math.sin(r),Math.cos(r)),this.tween(i,s=>{this.rig.x=e.x+(a.x-e.x)*s,this.rig.y=e.y+(a.y-e.y)*s,this.rig.dist=Math.exp(Math.log(e.dist)+(Math.log(a.dist)-Math.log(e.dist))*s),this.rig.tilt=e.tilt+(a.tilt-e.tilt)*s,this.rig.az=e.az+r*s},o,"camera")}fitDistance(t,i,o=80,e=this.rig.tilt){const a=P.degToRad(this.camera.fov),r=this.renderer.domElement.clientWidth||window.innerWidth,s=this.renderer.domElement.clientHeight||window.innerHeight,n=r/Math.max(1,r-o*2),c=s/Math.max(1,s-o*2),h=i*c/2/Math.tan(a/2),l=t*n/2/Math.tan(a/2)/this.camera.aspect;return Math.max(h,l)*(1+Math.sin(e)*.35)}fit(t,i={}){const o=t.map(M=>M[0]),e=t.map(M=>M[1]),a=Math.min(...o),r=Math.max(...o),s=Math.min(...e),n=Math.max(...e),c=i.az??this.rig.az,h=i.tilt??this.rig.tilt,l=Math.cos(c),d=Math.sin(c),u=[[a,s],[r,s],[a,n],[r,n]],F=u.map(([M,R])=>M*l+R*d),w=u.map(([M,R])=>-M*d+R*l),z=Math.max(4,Math.max(...F)-Math.min(...F)),f=Math.max(4,(Math.max(...w)-Math.min(...w))*Math.max(.45,Math.cos(h))),G=this.renderer.domElement,L=G.clientWidth||window.innerWidth,O=G.clientHeight||window.innerHeight,C=i.padding??60,k=(i.pad?.l??0)+C,E=(i.pad?.r??0)+C,U=(i.pad?.t??0)+C,_=(i.pad?.b??0)+C,tt=Math.max(80,L-k-E),et=Math.max(80,O-U-_),H=Math.tan(P.degToRad(this.camera.fov)/2),V=Math.max(8,Math.max(z*L/tt/(2*H*this.camera.aspect),f*O/et/(2*H))),B=2*V*H/O,j=(k-E)/2*B,I=(U-_)/2*B,it=(a+r)/2,ot=(s+n)/2;this.flyTo({x:it-j*l-I*d,y:ot-j*d+I*l,dist:V,tilt:h,az:c},i.duration??1400)}overview(t=0,i=1400,o=0){const e=this.bundle.manifest.map,a=[[e.origin[0],e.origin[1]],[e.origin[0]+e.width*e.resolution,e.origin[1]+e.height*e.resolution]];this.fit(a,{tilt:t,az:o,duration:i,padding:40})}project(t,i,o=0){const e=T(t,i,o).project(this.camera);if(e.z>1)return null;const a=this.renderer.domElement,r=(e.x*.5+.5)*a.clientWidth,s=(-e.y*.5+.5)*a.clientHeight;return{x:r,y:s,visible:e.x>-1.2&&e.x<1.2&&e.y>-1.2&&e.y<1.2}}unproject(t,i){const o=this.renderer.domElement,e=new p(t/o.clientWidth*2-1,-(i/o.clientHeight)*2+1),a=new ut;a.setFromCamera(e,this.camera);const r=new x;return a.ray.intersectPlane(new dt(new x(0,1,0),0),r)?[r.x,-r.z]:null}async ensureWalls(){if(this.walls)return;const t=await fetch(this.bundle.url(this.bundle.manifest.map.walls)).then(r=>r.json()),i=new mt(1,1,1);i.translate(0,.5,0);const o=new A({vertexShader:Wt,fragmentShader:Ft,transparent:!0,uniforms:{uHeight:{value:.001},uSide:{value:new m},uCap:{value:new m},uLight:{value:new x(.5,.8,.3)},uOpacity:{value:1}}}),e=new ft(i,o,t.length),a=new vt;t.forEach(([r,s,n,c],h)=>{a.makeScale(Math.max(n-r,.05),Rt,Math.max(c-s,.05)),a.setPosition((r+n)/2,0,-(s+c)/2),e.setMatrixAt(h,a)}),e.instanceMatrix.needsUpdate=!0,e.frustumCulled=!1,e.visible=!1,e.renderOrder=2,this.walls=e,this.scene.add(e),this.applyTheme()}async setWalls(t,i=1100){if(t&&await this.ensureWalls(),!this.walls)return;const o=this.walls,e=this.wallHeight,a=t?1:0;o.visible=!0;const r=this.floor.material.uniforms;this.tween(i,s=>{this.wallHeight=e+(a-e)*s,o.material.uniforms.uHeight.value=Math.max(.001,this.wallHeight),r.uAO.value=this.wallHeight,r.uWallFlat.value=1-this.wallHeight*.85},()=>{o.visible=this.wallHeight>.01},"walls")}ribbonGeometry(t,i,o){const e=[],a=[],r=[],s=[],n=[];let c=0;for(let l=0;l<t.length;l++){const d=t[l],u=t[Math.max(0,l-1)],F=t[Math.min(t.length-1,l+1)];l>0&&(c+=d.distanceTo(u));const w=new p().subVectors(F,u);w.lengthSq()<1e-9&&w.set(1,0),w.normalize();const z=new p(-w.y,w.x).multiplyScalar(i/2);for(const f of[-1,1])e.push(d.x+z.x*f,.08,-(d.y+z.y*f)),a.push(c),r.push(f),s.push(o?o[l]:0);if(l>0){const f=(l-1)*2;n.push(f,f+1,f+2,f+1,f+3,f+2)}}const h=new W;return h.setAttribute("position",new b(e,3)),h.setAttribute("aDist",new b(a,1)),h.setAttribute("aSide",new b(r,1)),h.setAttribute("aT",new b(s,1)),h.setIndex(n),{geometry:h,total:c}}ribbonMaterial(t,i){return new A({vertexShader:zt,fragmentShader:Ct,transparent:!0,depthWrite:!1,side:Y,blending:t&&document.documentElement.dataset.theme!=="light"?S:X,uniforms:{uColor:{value:new m},uDraw:{value:0},uTime:{value:0},uGlow:{value:t?1:0},uOpacity:{value:1},uTrail:{value:i?1:0},uT:{value:0},uFade:{value:120},uMinAlpha:{value:.3}}})}densify(t,i=.25){const o=[];for(let e=0;e<t.length-1;e++){const a=new p(...t[e]),r=new p(...t[e+1]),s=Math.max(1,Math.ceil(a.distanceTo(r)/i));for(let n=0;n<s;n++)o.push(a.clone().lerp(r,n/s))}return o.push(new p(...t[t.length-1])),o}setRoute(t){if(this.route&&(this.scene.remove(this.route.core,this.route.glow),this.route.core.geometry.dispose(),this.route.glow.geometry.dispose(),this.route=null),!t||t.length<2)return this.dirty=!0,0;const i=this.densify(t),o=this.ribbonGeometry(i,.5),e=this.ribbonGeometry(i,3.2),a=new g(o.geometry,this.ribbonMaterial(!1,!1)),r=new g(e.geometry,this.ribbonMaterial(!0,!1));for(const s of[a,r])s.material.depthTest=!1;return a.renderOrder=11,r.renderOrder=10,this.route={core:a,glow:r,length:o.total},this.scene.add(r,a),this.applyTheme(),o.total}drawRoute(t=1800,i=0){if(!this.route)return;const o=this.route;this.tween(t,e=>{const a=i+(o.length-i)*e+.01;o.core.material.uniforms.uDraw.value=a,o.glow.material.uniforms.uDraw.value=a},void 0,"route")}routeLength(){return this.route?.length??0}setTrail(t,i=120,o=.3){if(this.trail&&(this.scene.remove(this.trail.core,this.trail.glow),this.trail=null),!t)return;const e=[],a=[];let r=null;for(const u of t)r&&Math.hypot(u[1]-r[1],u[2]-r[2])>2&&(e.push(new p(r[1],r[2]),new p(u[1],u[2])),a.push(-1,-1)),e.push(new p(u[1],u[2])),a.push(u[0]),r=u;const s=this.ribbonGeometry(e,.14,a),n=this.ribbonGeometry(e,1.1,a),c=this.ribbonMaterial(!1,!0),h=this.ribbonMaterial(!0,!0);for(const u of[c,h])u.uniforms.uFade.value=i,u.uniforms.uMinAlpha.value=o;h.uniforms.uMinAlpha.value=o*.3;const l=new g(s.geometry,c),d=new g(n.geometry,h);l.renderOrder=6,d.renderOrder=5,this.trail={core:l,glow:d},this.scene.add(d,l),this.applyTheme()}setTrailTime(t){this.trail&&(this.trail.core.material.uniforms.uT.value=t,this.trail.glow.material.uniforms.uT.value=t,this.dirty=!0)}buildRobot(){const t=new pt;t.moveTo(.55,0),t.lineTo(-.35,.34),t.lineTo(-.18,0),t.lineTo(-.35,-.34),t.closePath();const i=new g(new yt(t),new D);i.rotation.x=-Math.PI/2,i.position.y=.12;const o=document.createElement("canvas");o.width=o.height=128;const e=o.getContext("2d"),a=e.createRadialGradient(64,64,0,64,64,64);a.addColorStop(0,"rgba(255,255,255,0.9)"),a.addColorStop(.25,"rgba(255,255,255,0.35)"),a.addColorStop(1,"rgba(255,255,255,0)"),e.fillStyle=a,e.fillRect(0,0,128,128);const r=new wt(new gt({map:new xt(o),transparent:!0,depthWrite:!1,blending:S}));r.position.y=.1,r.scale.setScalar(3.2),this.robot.add(i,r),this.robot.visible=!1,this.robot.renderOrder=8,this.scene.add(this.robot)}setRobot(t){this.robot.visible=!!t,t&&(this.robot.position.set(t.x,0,-t.y),this.robot.children[0].rotation.z=t.yaw),this.dirty=!0}setScan(t,i,o=0,e=0){if(!t||!i){this.rays&&(this.rays.visible=!1),this.hits&&(this.hits.visible=!1),this.dirty=!0;return}const a=i.length;if(!this.rays){const c=new W;c.setAttribute("position",new b(new Float32Array(a*6),3)),this.rays=new Z(c,new q({transparent:!0,opacity:.07,blending:S,depthWrite:!1}));const h=new W;h.setAttribute("position",new b(new Float32Array(a*3),3)),this.hits=new J(h,new Mt({size:3.2,sizeAttenuation:!1,transparent:!0,opacity:.95,depthWrite:!1})),this.rays.renderOrder=7,this.hits.renderOrder=7,this.scene.add(this.rays,this.hits),this.applyTheme()}const r=this.rays.geometry.getAttribute("position"),s=this.hits.geometry.getAttribute("position");let n=0;for(let c=0;c<a;c++){const h=i[c]/100;if(h<=.05)continue;const l=t.yaw+o+c*e,d=t.x+Math.cos(l)*h,u=t.y+Math.sin(l)*h;r.setXYZ(n*2,t.x,.3,-t.y),r.setXYZ(n*2+1,d,.3,-u),s.setXYZ(n,d,.3,-u),n++}this.rays.geometry.setDrawRange(0,n*2),this.hits.geometry.setDrawRange(0,n),r.needsUpdate=!0,s.needsUpdate=!0,this.rays.visible=!0,this.hits.visible=!0,this.dirty=!0}setCloud(t){if(this.cloud&&(this.scene.remove(this.cloud),this.cloud=null),!t)return;const i=t.length/3,o=new Float32Array(i*3),e=new Float32Array(i);for(let s=0;s<i;s++)o[s*3]=t[s*3]/100,o[s*3+1]=.08,o[s*3+2]=-t[s*3+1]/100,e[s]=(t[s*3+2]+32768)/10;const a=new W;a.setAttribute("position",new Q(o,3)),a.setAttribute("aT",new Q(e,1));const r=new A({vertexShader:Ot,fragmentShader:Ht,transparent:!0,depthWrite:!1,blending:S,uniforms:{uT:{value:0},uSize:{value:4.6},uPixelRatio:{value:this.renderer.getPixelRatio()},uColor:{value:new m},uAccent:{value:new m},uOpacity:{value:1}}});this.cloud=new J(a,r),this.cloud.renderOrder=3,this.cloud.frustumCulled=!1,this.scene.add(this.cloud),this.applyTheme()}setCloudState(t,i=1){this.cloud&&(this.cloud.material.uniforms.uT.value=t,this.cloud.material.uniforms.uOpacity.value=i,this.cloud.visible=i>.01,this.dirty=!0)}setReveal(t){this.floor.material.uniforms.uRevealK.value=t,this.dirty=!0}setMapOpacity(t){this.floor.material.uniforms.uOpacity.value=t,this.dirty=!0}setGroundOpacity(t){this.ground.material.uniforms.uOpacity.value=t,this.dirty=!0}showEllipse(t){if(!t){this.ellipse&&(this.ellipse.visible=!1),this.dirty=!0;return}this.ellipse||(this.ellipse=new g(new bt(.94,1,96),new D({transparent:!0,opacity:.95,depthWrite:!1,side:Y})),this.ellipse.rotation.x=-Math.PI/2,this.ellipse.renderOrder=9,this.scene.add(this.ellipse),this.applyTheme()),this.ellipse.scale.set(Math.max(.08,t.sd[0]*2.45),Math.max(.08,t.sd[1]*2.45),1),this.ellipse.position.set(t.x,.06,-t.y),this.ellipse.visible=!0,this.dirty=!0}setGraph(t){if(this.graphLines&&(this.scene.remove(this.graphLines),this.graphLines=null),!t){this.dirty=!0;return}const i=[];for(const[[e,a],[r,s]]of t)i.push(e,.06,-a,r,.06,-s);const o=new W;o.setAttribute("position",new b(i,3)),this.graphLines=new Z(o,new q({transparent:!0,opacity:.75})),this.graphLines.renderOrder=6,this.scene.add(this.graphLines),this.applyTheme()}route2points(t,i){return[[i.x,i.y],...t.steps.map(o=>[o.x,o.y]),[t.destination.x,t.destination.y]]}poseAt(t,i){return Tt(t,i)}}export{kt as MapScene};
