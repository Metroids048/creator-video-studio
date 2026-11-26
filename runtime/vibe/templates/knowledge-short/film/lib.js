// lib.js — shared drawing kit for knowledge shorts (Canvas2D, 1920×1080). Extracted from 同步·萤火 / 光在路上.
// Load before film.js. Everything here is deterministic: no Math.random, no Date — frames render out of order.
'use strict';
const W = 1920, H = 1080, TAU = Math.PI * 2;
const cv = document.getElementById('c');
let g = cv.getContext('2d');
function cvSwap(ctx) { const prev = g; g = ctx; return prev; }   // draw helpers into an offscreen context, then swap back

// ---------- maths ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, x) => { x = clamp((x - a) / (b - a)); return x * x * (3 - 2 * x); };   // 0→1 between times a and b
const eio = x => (x = clamp(x), x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const eout = x => 1 - Math.pow(1 - clamp(x), 3);
const wrap = x => ((x % TAU) + TAU) % TAU;
function rng(seed) { let a = seed >>> 0; return () => { a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const hash = i => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
function vnoise(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u); }
function fbm(x, seed = 0) { let s = 0, a = .5, f = 1; for (let o = 0; o < 4; o++) { s += a * vnoise(x * f + seed * 17.3 + o * 31.7); a *= .5; f *= 2.1; } return s; }
// precompute a simulation once, read it back per frame: sim(fps, t0, t1, init, step) → { at(t) }
function bake(fps, t0, t1, init, step, sub = 4) {
  const frames = Math.ceil((t1 - t0) * fps) + 1, store = []; let s = init();
  for (let f = 0; f < frames; f++) { store.push(JSON.parse(JSON.stringify(s))); for (let k = 0; k < sub; k++) s = step(s, t0 + (f + k / sub) / fps, 1 / fps / sub); }
  return { at: t => store[clamp(Math.round((t - t0) * fps), 0, frames - 1)] };
}

// ---------- light ----------
function sprite(size, stops) {
  const c = document.createElement('canvas'); c.width = c.height = size; const x = c.getContext('2d');
  const gr = x.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [o, col] of stops) gr.addColorStop(o, col);
  x.fillStyle = gr; x.fillRect(0, 0, size, size); return c;
}
const GLOW = {   // pre-rendered glow sprites; draw them with additive blending (see light())
  gold: sprite(256, [[0, 'rgba(255,246,220,1)'], [.07, 'rgba(255,224,160,.9)'], [.2, 'rgba(230,180,100,.35)'], [.45, 'rgba(200,140,60,.08)'], [1, 'rgba(180,120,40,0)']]),
  green: sprite(256, [[0, 'rgba(255,253,225,1)'], [.06, 'rgba(250,250,190,.95)'], [.16, 'rgba(214,236,110,.42)'], [.4, 'rgba(160,200,70,.10)'], [1, 'rgba(120,170,40,0)']]),
  coral: sprite(256, [[0, 'rgba(255,240,228,1)'], [.08, 'rgba(255,190,160,.85)'], [.22, 'rgba(240,120,100,.3)'], [.5, 'rgba(200,70,70,.07)'], [1, 'rgba(160,40,50,0)']]),
  ice: sprite(256, [[0, 'rgba(240,250,255,1)'], [.07, 'rgba(190,225,255,.9)'], [.2, 'rgba(110,170,240,.35)'], [.45, 'rgba(60,110,200,.08)'], [1, 'rgba(40,80,160,0)']]),
  soft: sprite(256, [[0, 'rgba(255,255,255,1)'], [1, 'rgba(255,255,255,0)']]),
};
function blit(img, x, y, r, a) { if (a <= .003 || r <= .2) return; g.globalAlpha = Math.min(1, a); g.drawImage(img, x - r, y - r, 2 * r, 2 * r); g.globalAlpha = 1; }
function light(fn) { const o = g.globalCompositeOperation; g.globalCompositeOperation = 'lighter'; fn(); g.globalCompositeOperation = o; }
function bloom(x, y, r, a, core = '255,252,232') {   // a big soft light that can swallow the frame (shape-continuous transitions)
  if (a <= 0) return; const gr = g.createRadialGradient(x, y, 0, x, y, r);
  gr.addColorStop(0, `rgba(${core},${a})`); gr.addColorStop(.35, `rgba(${core},${a * .85})`); gr.addColorStop(.7, `rgba(${core},${a * .4})`); gr.addColorStop(1, `rgba(${core},0)`);
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
}
function wash(a, col = '0,0,0') { if (a <= 0) return; g.fillStyle = `rgba(${col},${Math.min(1, a)})`; g.fillRect(0, 0, W, H); }
function strokeReveal(pts, prog) {   // draw a polyline up to a fraction of its length (fine-line infographics)
  if (prog <= 0 || pts.length < 2) return;
  let total = 0; const seg = []; for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
  let left = total * clamp(prog); g.beginPath(); g.moveTo(...pts[0]);
  for (let i = 1; i < pts.length && left > 0; i++) { const k = Math.min(1, left / seg[i - 1]); g.lineTo(lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k)); left -= seg[i - 1]; }
  g.stroke();
}

// ---------- depth, fog, highlights, motion blur (aesthetics.md §2–§4) ----------
const _off = {}; function offscreen(key, w = W, h = H) {   // reusable scratch canvases
  if (!_off[key]) { const c = document.createElement('canvas'); c.width = w; c.height = h; _off[key] = c; }
  return _off[key];
}
// draw fn() as an out-of-focus layer: blur ≤ 24 px, push it back by dimming (bg 0.3–0.5) rather than by blur alone
function dof(fn, px = 6, dim = 0) {
  const c = offscreen('dof'), x = c.getContext('2d'); x.setTransform(1, 0, 0, 1, 0, 0); x.clearRect(0, 0, W, H);
  const prev = cvSwap(x); fn(); cvSwap(prev);
  g.save(); g.filter = `blur(${Math.min(24, px)}px)${dim ? ` brightness(${1 - dim})` : ''}`; g.drawImage(c, 0, 0); g.restore();
}
// halation: highlights (≈ above mid-grey) bleed a soft glow — call after the scene, before subtitles. a 0.3–0.5 for dark films
function halation(a = .4, r = 12) {
  const c = offscreen('hal', W / 4, H / 4), x = c.getContext('2d');
  x.filter = `brightness(.55) contrast(2.2) blur(${Math.max(1, r / 4)}px)`; x.clearRect(0, 0, W / 4, H / 4); x.drawImage(cv, 0, 0, W / 4, H / 4); x.filter = 'none';
  g.save(); g.globalCompositeOperation = 'screen'; g.globalAlpha = a; g.drawImage(c, 0, 0, W, H); g.restore();
}
// 2–3 drifting fog bands; layer speeds ≈ 1:2; each 0.08–0.25 alpha. col 'r,g,b'
function fogLayers(t, { y = H * .62, h = 260, col = '200,215,230', a = [.18, .12], speed = [12, 24], seed = 3 } = {}) {
  a.forEach((al, k) => { for (let i = 0; i < 9; i++) {
    const r = h * (1.4 + hash(seed * 31 + k * 9 + i)), px = ((hash(seed + k * 13 + i) * (W + 2 * r) + t * speed[k]) % (W + 2 * r)) - r;
    const py = y + (hash(seed * 7 + k * 5 + i) - .5) * h + k * h * .35, gr = g.createRadialGradient(px, py, 0, px, py, r);
    gr.addColorStop(0, `rgba(${col},${al})`); gr.addColorStop(1, `rgba(${col},0)`);
    g.fillStyle = gr; g.save(); g.translate(px, py); g.scale(1, .32); g.translate(-px, -py); g.fillRect(px - r, py - r, 2 * r, 2 * r); g.restore();
  } });
}
// average n samples of drawAt(t') across the shutter (0.5 = 180°) — only for whips and fast fly-ins (it costs n× a frame).
// Not for thin lines or many small figures (rings of cars, ant legs): even 10–16 samples read as stacked copies there
// (蚂蚁不堵车 v7 and v8, both 必须) — use a faster ease and a cut instead. n must cover the motion: n ≥ (on-screen travel per frame × shutter) / 3 px, or thin lines turn into a stack of copies
// (蚂蚁不堵车 v7: 10 samples on a fast push-in drew the ring as 6–8 concentric wires — a 必须). Shorter shutter if n gets big.
function motionBlur(drawAt, t, fps, shutter = .5, n = 12) {
  const c = offscreen('mb'), x = c.getContext('2d'), acc = offscreen('mbacc'), ax = acc.getContext('2d'); ax.clearRect(0, 0, W, H);
  for (let i = 0; i < n; i++) {
    x.setTransform(1, 0, 0, 1, 0, 0); x.clearRect(0, 0, W, H); const prev = cvSwap(x); drawAt(t + (i / (n - 1) - .5) * shutter / fps); cvSwap(prev);
    ax.globalAlpha = 1 / (i + 1); ax.drawImage(c, 0, 0);
  }
  ax.globalAlpha = 1; g.drawImage(acc, 0, 0);
}
// whole-frame colour temperature (tempArc from motion.js): cool open → warm climax → neutral close, ≤ 8 %
function tint(t, keys) { if (typeof tempArc !== 'function') return; g.save(); g.globalCompositeOperation = 'soft-light'; g.fillStyle = tempArc(t, keys); g.fillRect(0, 0, W, H); g.restore(); }

// ---------- finish: vignette + moving grain. Order in draw(): scene → halation → subtitles → post → tail fade ----------
// presets (aesthetics.md §3): night = dark film, paper = light paper / watercolour. Grain is 2 px: 1 px dies in platform re-encode.
const GRAIN = [0, 1, 2].map(k => {
  const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d'), d = x.createImageData(128, 128), R = rng(300 + k);
  for (let i = 0; i < d.data.length; i += 4) { const v = 100 + R() * 56; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
  x.putImageData(d, 0, 0); return c;
});
const POST = { night: { vignette: .5, grain: .09 }, paper: { vignette: .2, grain: .06 } };
function post(f, opt = {}) {
  const { vignette = .62, grain = .1, grainPx = 2 } = typeof opt === 'string' ? POST[opt] : opt, T = 128 * grainPx;
  const v = g.createRadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * 1.05);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, `rgba(0,0,0,${vignette})`); g.fillStyle = v; g.fillRect(0, 0, W, H);
  g.save(); g.globalCompositeOperation = 'overlay'; g.globalAlpha = grain; g.imageSmoothingEnabled = false;
  const tile = GRAIN[f % 3], ox = (hash(f) * T) | 0, oy = (hash(f + 77) * T) | 0;
  for (let y = -oy; y < H; y += T) for (let x = -ox; x < W; x += T) g.drawImage(tile, x, y, T, T);
  g.restore();
}

// ---------- type: the film's style font (style.js, `./vf style <preset>`) + small italic English, revealed char by char ----------
// Sizes are measured glyph heights from the preset (kit/styles/_targets.json): smaller than the old 44/58 px by the user's call.
const ST = window.STYLE || { css: '"Songti SC", "STSong", serif', canvas: { sub: 40, center: 54 }, colors: { base: '#efe7d6' } };
const ZH = ST.css, EN = 'Baskerville, "Times New Roman", serif', MONO = 'Menlo, monospace';
const INK = ST.colors.base;
function spaced(text, x, y, font, spacing, color, alpha, align = 'center', reveal = null) {
  g.font = font; g.textBaseline = 'alphabetic';
  const chars = [...text], ws = chars.map(c => g.measureText(c).width), total = ws.reduce((a, b) => a + b, 0) + spacing * (chars.length - 1);
  let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  chars.forEach((c, i) => {
    const k = reveal ? reveal(i, chars.length) : 1;
    g.fillStyle = typeof color === 'function' ? color(i) : color;
    if (k > 0) { g.globalAlpha = alpha * k; g.fillText(c, cx, y + (1 - k) * 8); }
    cx += ws[i] + spacing;
  });
  g.globalAlpha = 1; return total;
}
// SUBS rows: [start, end, 中文, English, mode?]; mode 'center' = a statement line in the middle of the frame.
// Mark ONE keyword per line with **…**: it takes the preset's accent colour (aesthetics.md §6) — colour, not size, is the hierarchy.
// Bottom subtitles sit at y≈958 — inside the 16:9 safe area AND inside the band a vertical crop keeps.
const ACCENT = ST.colors.fill || '#FFD54A';
// Line changes: no empty band AND no two lines on top of each other (review 应修 #4 / #2, 蚂蚁不堵车 v6 and v7). When
// the next line of the same mode starts within 1 s of this one's end, this one holds until 0.14 s before it and is
// gone 0.02 s before it; the next line's first characters then come in fast (0.035 s stagger, 0.3 s each).
function subtitles(t, SUBS) {
  SUBS.forEach(([a, b, raw, en, mode], k) => {
    const nx = SUBS.slice(k + 1).find(r => (r[4] === 'center') === (mode === 'center'));
    const handoff = nx && nx[0] - b < 1 && nx[0] >= b - .3;
    const outT = handoff ? nx[0] - .14 : b, outD = handoff ? .12 : .55;
    if (t < a - .05 || t > outT + outD + .1) return;
    const hot = new Set(); let zh = '', on = false;
    for (const part of raw.split('**')) { if (on) for (let i = 0; i < [...part].length; i++) hot.add([...zh].length + i); zh += part; on = !on; }
    const outA = 1 - smooth(outT, outT + outD, t), center = mode === 'center';
    const size = center ? ST.canvas.center : ST.canvas.sub, yz = center ? 520 : 962, ye = yz + size * .55 + 18;
    g.save(); g.shadowColor = 'rgba(0,0,0,.8)'; g.shadowBlur = 16;
    spaced(zh, W / 2, yz, `400 ${size}px ${ZH}`, size * .12, i => hot.has(i) ? ACCENT : INK, outA, 'center', i => smooth(a + i * .035, a + i * .035 + .3, t));
    if (en) spaced(en, W / 2, ye, `italic ${Math.round(size * .56)}px ${EN}`, 1.2, '#b9ae98', .78 * outA * smooth(a + .35, a + 1.0, t));   // English line ≈ 55–60 % of the Chinese
    g.restore();
  });
}
function hud(tl, br, alpha = 1) {   // corner brackets + chapter label + live readout from the model
  const a = .5 * alpha; if (a <= 0) return;
  g.save(); g.globalAlpha = a; g.strokeStyle = '#d8c9a6'; g.lineWidth = 1.2;
  const m = 44, l = 26;
  for (const [x, y, sx, sy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) { g.beginPath(); g.moveTo(x, y + sy * l); g.lineTo(x, y); g.lineTo(x + sx * l, y); g.stroke(); }
  g.font = `${Math.round(ST.canvas.sub * .4)}px ${MONO}`; g.fillStyle = '#d8c9a6'; g.textBaseline = 'middle';
  if (tl) { g.textAlign = 'left'; g.fillText(tl, m + 40, m + 8); }
  if (br) { g.textAlign = 'right'; g.fillText(br, W - m - 40, H - m - 8); }
  g.textAlign = 'left'; g.restore();
}

// ---------- page contract for kit/render.mjs ----------
// film.js defines DUR, FPS, draw(t) and optionally events(); this wires them up once fonts are in.
// Anything bigger than a subtitle (an anchor word slammed in at the climax, ≈ 1/3 of the frame width) is a multiple of
// ST.canvas.center — e.g. `${Math.round(ST.canvas.center * 3.6)}px ${ZH}` — never a literal px size.
function filmReady(fonts = [`${ST.canvas.sub}px ${ZH}`, `italic 22px ${EN}`]) {
  window.FRAME_FORMAT = 'png';   // glow gradients band in JPEG; frames stay lossless until the final encode
  window.renderAt = (t, type = 'image/png', q = .92) => {
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    draw(t); return cv.toDataURL(type, q);
  };
  Promise.resolve(ST.fontReady).then(() => Promise.all(fonts.map(f => document.fonts.load(f, '知识Ag')))).finally(() => { window.renderAt(0); window.ready = true; });
}
