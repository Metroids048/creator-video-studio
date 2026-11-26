// fx.js — reusable effects for lyric MVs (p5.brush engine). Load after core.js / clawd.js, before the scenes.
// Every function is a pure function of t (frames render in parallel and out of order): positions come from hash(i) and t,
// never from state. Generalised from 挪威的森林's set pieces, keeping the fixes its review rounds forced:
//   · slow textures (fxSlowSeed): background brush texture changes ≤4×/s — 12×/s read as flickering stains;
//   · out-of-focus near particles are drawn as LIGHT (glow), not cream paint (that dried to dark rings = "extra moons");
//   · the vignette never reaches into the frame (it used to stain faces).
// Richness rule (references/lyric-mv.md): every shot has an ambient layer (particles or light) and the big moments get an
// accent (burst, rays, impact). Pick by the world: snow/petals/leaves/rain/fireflies/dust/embers/bubbles.
// All take o = { n, speed, size, col, … }; sensible defaults. Screen space unless called inside camBegin().

const fxSlowSeed = key => { const b = BOILN; BOILN = Math.floor(T * 4); boilSeed(key); BOILN = b; };

// ---------- particles ----------
// Generic looping field: particle i starts at a hashed place and moves with (vx, vy) px/s, wrapping in the area.
// draw(x, y, i, h) paints it (h = its own 0..1 random). Use for anything that drifts through the whole shot.
function fxField(t, o, draw) {
  const n = o.n ?? 40, [x0, y0, x1, y1] = o.area || [-200, -200, W + 200, H + 200], wx = x1 - x0, wy = y1 - y0, sp = o.speed ?? 1;
  for (let i = 0; i < n; i++) {
    const h = hash(i * 7.13 + (o.seed || 0)), vx = (o.vx ?? 0) * (.6 + .8 * hash(i + 31)) * sp, vy = (o.vy ?? 60) * (.6 + .8 * hash(i + 17)) * sp;
    const x = x0 + (((hash(i + 3) * wx + t * vx) % wx) + wx) % wx + (o.sway ?? 30) * Math.sin(t * (o.swayF ?? .8) + i * 2.1);
    const y = y0 + (((hash(i + 5) * wy + t * vy) % wy) + wy) % wy;
    draw(x, y, i, h);
  }
}
function fxSnow(t, o = {}) {        // falling flakes; o.near adds big soft out-of-focus flakes as light
  fxField(t, { n: o.n ?? 45, vy: 70, vx: o.wind ?? 0, sway: 30, speed: o.speed, seed: 1 }, (x, y, i, h) => {
    fxSlowSeed('fxsn' + i); const s = (o.size ?? 1) * (3 + 6 * h); paint(ellPts(x, y, s, s, 8), { wash: o.col || PAL.cream, washOp: 200, ink: null });
  });
  fxField(t, { n: o.near ?? 0, vy: 200, vx: (o.wind ?? 0) * 2, sway: 60, speed: o.speed, seed: 2 }, (x, y, i, h) => glow(x, y, 26 + 26 * h, '#FFF5E2', .3));
}
function fxPetals(t, o = {}) {      // sakura / flower petals: fall slowly, tumble (squashed ellipse that rotates)
  const cols = o.cols || ['#F7B6C8', '#F9CFDA', '#EE9BB2'];
  fxField(t, { n: o.n ?? 26, vy: 55, vx: o.wind ?? 40, sway: 50, swayF: .6, speed: o.speed, seed: 3 }, (x, y, i, h) => {
    fxSlowSeed('fxpe' + i); const s = (o.size ?? 1) * (8 + 8 * h), r = t * (1.5 + 2 * h) + i, fl = .35 + .65 * Math.abs(Math.sin(t * 2.2 + i));
    paint(ellPts(x, y, s, s * .55 * fl, 10, 0, r), { wash: cols[i % cols.length], washOp: 220, ink: PAL.ink, sw: .6 });
  });
}
function fxLeaves(t, o = {}) {      // autumn leaves: like petals, bigger, warmer, more tumble
  fxPetals(t, { n: 16, wind: 70, size: 1.6, cols: ['#E07A2E', '#C9502C', '#E8A93A', '#9C6B2E'], ...o });
}
function fxRain(t, o = {}) {        // slanted streaks + splashes where they land (o.ground)
  const g = o.ground ?? H - 80, ang = o.slant ?? .25;
  for (let i = 0; i < (o.n ?? 70); i++) {
    const h = hash(i + 101), span = g + 300, y = ((hash(i + 7) * span + t * (900 + 500 * h)) % span) - 300, x = hash(i + 9) * (W + 400) - 200 - ang * y;
    fxSlowSeed('fxrn' + i); inkLine([[x, y], [x - ang * 46, y + 46]], 1.2 + h, o.col || '#BFD3EA', 'ink', 0);
    const sp = frac((hash(i + 13) + t * 1.7)); if (sp < .12) { const q = sp / .12; paint(ellPts(hash(i + 15) * W, g, 10 * q, 3 * q, 8), { wash: '#DCE7F5', washOp: 160 * (1 - q), ink: null }); }
  }
}
function fxFireflies(t, o = {}) {   // warm points that wander and blink
  for (let i = 0; i < (o.n ?? 18); i++) {
    const [x0, y0, x1, y1] = o.area || [0, H * .35, W, H * .9];
    const x = lerp(x0, x1, hash(i + 201)) + 70 * Math.sin(t * (.3 + .4 * hash(i + 2)) + i), y = lerp(y0, y1, hash(i + 203)) + 40 * Math.sin(t * (.5 + .3 * hash(i + 4)) + i * 1.7);
    const b = Math.max(0, Math.sin(t * (1.2 + hash(i + 5)) + i * 3)) ** 2;
    if (b > .05) { glow(x, y, 46 * b * (o.size ?? 1), o.col || '#F7E27A', .7 * b); glow(x, y, 8, '#FFFBE0', b); }
  }
}
function fxDust(t, o = {}) {        // motes floating in a light beam / sunbeam (slow, small, faint)
  fxField(t, { n: o.n ?? 30, vy: -8, vx: 6, sway: 20, swayF: .3, area: o.area, seed: 4 }, (x, y, i, h) => glow(x, y, 6 + 8 * h, o.col || '#FFF1C8', .35 + .3 * Math.sin(t * 2 + i)));
}
function fxEmbers(t, o = {}) {      // rising sparks from a fire (o.x, o.y = source), fading as they climb
  for (let i = 0; i < (o.n ?? 24); i++) {
    const life = 1.6 + hash(i + 301), a = frac(t / life + hash(i + 303)), x = (o.x ?? W / 2) + (hash(i + 305) - .5) * (o.w ?? 160) + 40 * Math.sin(a * 6 + i);
    const y = (o.y ?? H - 150) - a * (o.h ?? 420); glow(x, y, 12 * (1 - a), o.col || '#FF9A3C', 1 - a);
  }
}
function fxBubbles(t, o = {}) {     // rising outlined bubbles (underwater, soda, dreamy)
  fxField(t, { n: o.n ?? 20, vy: -90, sway: 25, seed: 5, area: o.area }, (x, y, i, h) => {
    fxSlowSeed('fxbu' + i); const r = (o.size ?? 1) * (8 + 18 * h); inkLine(ellPts(x, y, r, r, 14), 1.4, o.col || '#DDF3FF', 'ink', .5); glow(x - r * .35, y - r * .35, r * .35, '#FFFFFF', .5);
  });
}
function fxGlints(t, y0, y1, o = {}) {   // twinkling crystals / stars that catch the light
  for (let i = 0; i < (o.n ?? 24); i++) {
    const tw = Math.max(0, Math.sin(t * (2 + 3 * hash(i + 400)) + i * 7)) ** 6; if (tw < .05) continue;
    const x = (o.x0 ?? 0) + hash(i + 410) * ((o.x1 ?? W) - (o.x0 ?? 0)), y = lerp(y0, y1, hash(i + 420));
    fxSlowSeed('fxgl' + i); paint(starPts(x, y, 5 + 7 * tw, .3, 4), { wash: '#FFFFFF', washOp: 230 * tw, ink: null }); glow(x, y, 26 * tw, o.col || '#DDE8FF', .5 * tw);
  }
}
// One-shot bursts at t0 (gravity, spin, fade). Put them on story beats: the catch, the kiss, the punchline.
function fxConfetti(t, t0, x, y, o = {}) {
  const a = t - t0, life = o.life ?? 2.2; if (a < 0 || a > life) return;
  const cols = o.cols || ['#FFC94D', '#FF7A9A', '#7AD3FF', '#9BE07A', '#C79BFF'];
  for (let i = 0; i < (o.n ?? 40); i++) {
    const ang = -Math.PI / 2 + (hash(i + 501) - .5) * (o.spread ?? 2.2), v = (o.power ?? 900) * (.5 + .5 * hash(i + 503));
    const px = x + Math.cos(ang) * v * a, py = y + Math.sin(ang) * v * a + 900 * a * a, fade = 1 - seg(a, life * .65, life);
    fxSlowSeed('fxcf' + i); paint(rectPts(px - 7, py - 4, 14, 8 * Math.abs(Math.cos(a * 9 + i)) + 1), { wash: cols[i % cols.length], washOp: 240 * fade, ink: null });
  }
}
function fxHeartsBurst(t, t0, x, y, o = {}) {   // little hearts rise and spread from a point (love beats)
  const a = t - t0, life = o.life ?? 1.8; if (a < 0 || a > life) return;
  for (let i = 0; i < (o.n ?? 9); i++) {
    const ang = -Math.PI / 2 + (hash(i + 601) - .5) * 1.8, d = (140 + 160 * hash(i + 603)) * easeOut(a / life);
    const s = (o.size ?? 1) * (14 + 12 * hash(i + 605)) * backOut(clamp(a * 4 - hash(i) * .5)), fade = 1 - seg(a, life * .6, life);
    if (s > 1) { fxSlowSeed('fxht' + i); paint(heartPts(x + Math.cos(ang) * d, y + Math.sin(ang) * d - 60 * a, s), { wash: o.col || '#FF6F8E', washOp: 240 * fade, ink: PAL.ink, sw: .8 }); }
  }
}

// ---------- light ----------
function fxGodRays(t, x, y, o = {}) {   // shafts of light fanning down from (x, y) (sun through trees, window light)
  const n = o.n ?? 7, len = o.len ?? 1100, k = o.k ?? 1;
  for (let i = 0; i < n; i++) {
    const a = (o.dir ?? Math.PI / 2) + (i - (n - 1) / 2) * (o.fan ?? .12) + .03 * Math.sin(t * .4 + i), w = (40 + 50 * hash(i + 701)) * (.75 + .25 * Math.sin(t * .7 + i * 2));
    fxSlowSeed('fxgr' + i);
    paint(ribbon([[x, y], [x + Math.cos(a) * len, y + Math.sin(a) * len]], w * .2, w * 1.6), { fill: o.col || '#FFF0C2', fillOp: 34 * k, bleed: .4, ink: null });
  }
  glow(x, y, 220 * k, o.col || '#FFF0C2', .45 * k);
}
function fxLensFlare(x, y, a = 1, col = '#FFE7B0') {   // a bright source + ghosts along the line through the frame centre
  glow(x, y, 260, col, .55 * a); glow(x, y, 60, '#FFFFFF', .9 * a);
  for (const [f, r, al] of [[.35, 40, .25], [.7, 70, .15], [1.25, 30, .22], [1.6, 90, .1]]) glow(lerp(x, W / 2, f) + (W / 2 - x) * (f > 1 ? f - 1 : 0), lerp(y, H / 2, f) + (H / 2 - y) * (f > 1 ? f - 1 : 0), r, col, al * a);
}
function fxLightSweep(t, t0, dur = .9, col = '#FFF6DA') {   // a diagonal sheen crossing the frame (reveal, title, magic)
  const p = seg(t, t0, t0 + dur); if (p <= 0 || p >= 1) return;
  const x = lerp(-500, W + 500, ease(p));
  fxSlowSeed('fxsw'); paint([[x - 120, -60], [x + 40, -60], [x - 260, H + 60], [x - 420, H + 60]], { fill: col, fillOp: 60 * Math.sin(p * Math.PI), bleed: .5, ink: null });
}
function fxBeatGlow(t, x, y, r, col = '#FFC766', k = 1) { glow(x, y, r * (1 + .25 * pulse(t, 4)), col, (.35 + .4 * pulse(t, 4)) * k); }   // breathes on the beat
function fxAurora(t, k = 1, yb = 260, cols = ['#7FE3C2', '#B79CFF']) {   // ribbons of light that breathe on the beat
  if (k <= 0) return;
  for (let j = 0; j < 3; j++) {
    fxSlowSeed('fxau' + j);
    const P = []; for (let i = 0; i <= 10; i++) { const x = -300 + i * (W + 600) / 10; P.push([x, yb + j * 70 + 70 * Math.sin(i * .7 + t * .6 + j * 1.7) + 30 * Math.sin(i * 1.9 - t * .9)]); }
    const col = cols[j % cols.length], w = (60 + 40 * pulse(t, 3)) * k;
    paint(ribbon(through(P, 4), w * .5, w * 1.4), { fill: col, fillOp: 80 * k, bleed: .35, tex: .6, ink: null });
    for (let i = 1; i < 10; i += 2) glow(P[i][0], P[i][1], 160 * k, col, .25 * k);
  }
}
function fxShootingStar(t, t0, x0, y0, x1, y1, dur = .7) {
  const k = seg(t, t0, t0 + dur); if (k <= 0 || k >= 1) return;
  const x = lerp(x0, x1, easeOut(k)), y = lerp(y0, y1, easeOut(k));
  inkLine([[lerp(x0, x, .25), lerp(y0, y, .25)], [lerp(x0, x, .7), lerp(y0, y, .7)]], 2 * (1 - k) + .5, '#C9D8FF', 'ink');
  inkLine([[lerp(x0, x, .7), lerp(y0, y, .7)], [x, y]], 5 * (1 - k) + 1, '#FFF6DA', 'ink');
  glow(x, y, 110, '#FFF6DA', 1 - k * .7); glow(x, y, 40, '#FFFFFF', 1 - k * .5);
}
function fxFog(y, h, a = 1, t = 0, col = '#AEBBE0') { fxSlowSeed('fxfg' + y); paint(ellPts(W / 2 + 80 * Math.sin(t * .1), y, W * 1.3, h, 30, 12), { fill: col, fillOp: 55 * a, bleed: .4, tex: .5, ink: null }); }

// ---------- camera language ----------
// Impact: a hit, a landing, a punchline. Returns a camera offset to add to camBegin(), decaying in ~.35 s; draw
// fxImpactLines() on top in screen space for the speed burst.
function fxImpact(t, t0, amt = 18) { const a = t - t0; if (a < 0 || a > .45) return [0, 0]; const [dx, dy] = shakeXY(t, amt * Math.exp(-a * 9)); return [dx, dy]; }
function fxImpactLines(t, t0, x = W / 2, y = H / 2) { const a = t - t0; if (a >= 0 && a < .3) { fxFocusLines(t, x, y, 1 - a / .3); flash(.35 * (1 - a / .12), '#FFFDF6'); } }
function fxHandheld(t, amt = 1) { return [6 * amt * Math.sin(t * .9) + 3 * amt * Math.sin(t * 2.3 + 1), 4 * amt * Math.sin(t * 1.1 + 2), .004 * amt * Math.sin(t * .7)]; }   // [dx, dy, rot] for camBegin
function fxSpeedLines(t, k = 1, dir = 1, col = '#FFFFFF') {   // manga speed lines across the frame (dash, chase, whoosh)
  if (k <= .01) return;
  for (let i = 0; i < 26; i++) {
    const y = hash(i + 801) * H, len = (300 + 500 * hash(i + 803)) * k, x = frac(hash(i + 805) + t * 3 * dir) * (W + len) - len;
    fxSlowSeed('fxsl' + i); inkLine([[x, y], [x + len, y]], 2 + 4 * hash(i), col, 'dry', 0);
  }
}
function fxFocusLines(t, x, y, k = 1, col = PAL.ink) {   // radial concentration lines: the frame points at (x, y)
  if (k <= .01) return;
  for (let i = 0; i < 40; i++) {
    const a = i / 40 * TAU + hash(i + 901) * .1, r0 = (420 + 180 * hash(i + 903) + 30 * Math.sin(t * 20 + i)) * (1.3 - .3 * k), r1 = 1600;
    fxSlowSeed('fxfl' + i); paint([[x + Math.cos(a) * r0, y + Math.sin(a) * r0], [x + Math.cos(a + .02) * r1, y + Math.sin(a + .02) * r1], [x + Math.cos(a - .02) * r1, y + Math.sin(a - .02) * r1]], { wash: col, washOp: 200 * k, ink: null });
  }
}
// Whip pan transition: p 0→.5 the old shot streaks out, cut at .5, .5→1 the new one streaks in. Call last in both shots.
function fxWhip(p, dir = 1, cols = ['#FFFFFF', '#CFE0FF']) {
  if (p <= 0 || p >= 1) return; const k = Math.sin(p * Math.PI);
  for (let i = 0; i < 14; i++) { const y = (i + .5) / 14 * H, w = 60 + 60 * hash(i + 951); fxSlowSeed('fxwh' + i); paint(ribbon([[-200, y], [W + 200, y + 40 * dir]], w * k, w * k * .6), { wash: cols[i % 2], washOp: 255 * k, ink: null }); }
}

// ---------- shape transitions (iris variants) ----------
function fxHeartIris(cx, cy, r, col = PAL.ink) { if (r < 4) iris(cx, cy, 0, col); else irisShape(heartPts(cx, cy, r), col); }
function fxStarIris(cx, cy, r, col = PAL.ink) { if (r < 4) iris(cx, cy, 0, col); else irisShape(starPts(cx, cy, r, .45, 5), col); }
function fxInkBloom(p, cx, cy, col = PAL.ink) {   // an ink blot spreads to cover the frame (p 0→1); cut under full cover, then reverse
  if (p <= 0) return; const r = 2400 * ease(p);
  for (let j = 0; j < 3; j++) { fxSlowSeed('fxib' + j); paint(ellPts(cx + 30 * j, cy - 20 * j, r * (1 - .12 * j), r * (.9 - .1 * j), 30, 30), { wash: col, ink: null }); }
}

// ---------- depth ----------
// Parallax layers inside one shot: each layer is drawn shifted by (camX − W/2)·(f − 1) so far layers (f < 1) move less.
// fxLayers(camX, [{ f: .3, draw: () => ridges() }, { f: 1, draw: () => mid() }, { f: 1.4, draw: () => fxFgBranches(t, 1) }])
function fxLayers(camX, list) { for (const L of list) { push(); translate((W / 2 - camX) * (L.f - 1), 0); L.draw(); pop(); } }
function fxFgBranches(t, side, k = 1, y = 0, col = '#0F2427') {   // dark, soft foreground boughs framing the shot (depth)
  for (let j = 0; j < 2; j++) {
    boilSeed('fxfb' + side + j);
    const x0 = side < 0 ? -80 : W + 80, sw = 12 * Math.sin(t * .9 + j * 2), yy = y + 120 + j * 260;
    const P = []; for (let i = 0; i <= 8; i++) { const u = i / 8; P.push([x0 - side * u * 520 * k, yy + u * 120 + sw * u + (i % 2 ? -36 : 36) * u]); }
    paint(ribbon(P, 130, 20), { wash: col, fill: col, fillOp: 90, bleed: .1, tex: .5, ink: null });
  }
}
function fxVignette(a = 1, col = '#0D1230') {   // edges only, fixed seed: never reaches the characters
  randomSeed(9157);
  for (const [cx, cy, rx, ry] of [[W / 2, -230, 1500, 300], [W / 2, H + 250, 1500, 300], [-300, H / 2, 420, 950], [W + 300, H / 2, 420, 950]])
    paint(ellPts(cx, cy, rx, ry, 30, 0), { fill: col, fillOp: 85 * a, bleed: .1, tex: .15, border: .2, ink: null });
}
