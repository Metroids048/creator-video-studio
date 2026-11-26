// film.js — DEMO knowledge short (12 s). Replace everything below with your film; keep the contract at the bottom.
// Brief: 一个硬知识（阻尼振动）+ 一个能画的隐喻（一颗光点在晃）+ 一句道理（能量没消失，只是变成了热）.
// The model drives the picture AND the sound: events() hands the zero crossings to score.py.
'use strict';
const FPS = 30, DUR = 12;
const T = { trace: -1.2, bloom: 10.2 };   // trace already drawn at t=0: frame 0 is the thumbnail, open mid-motion
const SUBS = [
  [-1.0, 4.6, '一根弹簧，每晃一下，都比上一下**小一点**。', 'Every swing is a little smaller than the last.'],
  [5.4, 9.4, '能量没有消失，只是悄悄变成了**热**。', 'The energy is not gone. It quietly became heat.'],
];

// ---------- model: damped oscillator x(t) = A·e^(−ζωt)·cos(ω_d t) ----------
const OSC = { A: 330, w: TAU / 1.7, z: .04, t0: -2.5 };   // started before frame 0
const wd = OSC.w * Math.sqrt(1 - OSC.z ** 2);
const osc = t => { const u = Math.max(0, t - OSC.t0); return OSC.A * Math.exp(-OSC.z * OSC.w * u) * Math.cos(wd * u); };
const energy = t => { const u = Math.max(0, t - OSC.t0); return Math.exp(-2 * OSC.z * OSC.w * u); };   // E/E0

const DUST = (() => { const R = rng(11), a = []; for (let i = 0; i < 160; i++) a.push({ x: R() * W, y: R() * H, r: .6 + R() * 1.6, s: R() }); return a; })();
const CY = 430;

function draw(t) {
  const f = Math.round(t * FPS);
  // ground: deep night gradient + slow mist
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#05070d'); bg.addColorStop(1, '#0d1018'); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  fogLayers(t, { y: 860, col: '120,140,170', a: [.10, .07] });   // depth: a low mist band, two speeds
  light(() => { for (const d of DUST) blit(GLOW.soft, (d.x + t * 6 * (d.s - .5)) % W, d.y + Math.sin(t * .4 + d.s * 9) * 6, d.r * 3, .05 + .05 * d.s); });

  // the anchor and the spring as one fine gold line
  const x = 960 + osc(t);
  g.strokeStyle = 'rgba(232,200,134,.55)'; g.lineWidth = 1.4;
  g.beginPath(); g.moveTo(560, CY); for (let i = 0; i <= 60; i++) { const k = i / 60, px = lerp(560, x, k); g.lineTo(px, CY + (i % 2 ? -14 : 14) * Math.sin(k * Math.PI)); } g.stroke();
  g.fillStyle = 'rgba(232,200,134,.7)'; g.fillRect(552, CY - 40, 3, 80);

  // strip chart: the same x(t), drawn as a time trace below — the infographic IS the model
  const k = smooth(T.trace, T.trace + 1.2, t);
  if (k > 0) {
    g.save(); g.globalAlpha = k; g.strokeStyle = 'rgba(232,200,134,.8)'; g.lineWidth = 1.6; g.beginPath();
    const span = 6, x0 = 360, x1 = 1560;
    let started = false;
    for (let i = 0; i <= 600; i++) { const tt = t - span + span * i / 600; if (tt < OSC.t0) continue; const px = lerp(x0, x1, i / 600), py = 700 + osc(tt) * .32; started ? g.lineTo(px, py) : g.moveTo(px, py); started = true; }
    g.stroke();
    g.setLineDash([3, 6]); g.strokeStyle = 'rgba(216,201,166,.35)';   // the decay envelope
    for (const s of [1, -1]) { g.beginPath(); for (let i = 0; i <= 120; i++) { const tt = t - span + span * i / 120, px = lerp(x0, x1, i / 120), py = 700 + s * OSC.A * .32 * Math.sqrt(energy(tt)); i ? g.lineTo(px, py) : g.moveTo(px, py); } g.stroke(); }
    g.restore();
  }
  hud('01 · 阻尼振动  DAMPED OSCILLATION', `E / E₀ = ${energy(t).toFixed(2)}`, smooth(T.trace, T.trace + 1, t) * (1 - smooth(T.bloom, T.bloom + .4, t)));

  // the hero: one point of light (the through-line device)
  light(() => { blit(GLOW.gold, x, CY, 120 + 40 * energy(t), .95); blit(GLOW.gold, x, CY, 26, 1); });
  // ending: the light swallows the frame (shape-continuous, no cross-dissolve)
  bloom(x, CY, lerp(40, 2600, eio(smooth(T.bloom, DUR - .6, t))), smooth(T.bloom, T.bloom + .6, t) * .95, '255,236,200');

  halation(.35);                                   // highlights bleed (dark film)
  tint(t, [[0, -.6], [8, .8], [DUR, .2]]);         // colour-temperature arc: cool → warm → neutral (motion.js tempArc)
  subtitles(t, SUBS);
  post(f, 'night');
  // no fade-in from black: frame 0 is the feed thumbnail and must already be the full picture (QA checks it)
  wash(smooth(DUR - .5, DUR, t));
}

// ---------- sound events from the same model ----------
function events() {
  const cross = [];
  for (let t = 0; t < DUR; t += 1 / 240) if (Math.sign(osc(t)) !== Math.sign(osc(t + 1 / 240))) cross.push({ t: +t.toFixed(4), e: +energy(t).toFixed(3), pan: 0 });
  return { DUR, T, cross };
}

Object.assign(window, { DUR, FPS, events });
filmReady();
