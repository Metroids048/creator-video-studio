// motion.js — named motion vocabulary shared by both templates (copied into each project by new_film.sh).
// Numbers from references/aesthetics.md §4: entrances expo-out 0.4–0.8 s, exits ≈0.7× the entrance with ease-in,
// overshoot by register (text 0, character landing ≤12 %, celebration ≤25 %), stagger groups capped at 0.6 s.
// Everything is a pure function of t (frames render out of order). No globals named clamp/lerp/ease here: the
// templates define their own, and top-level const names are shared across classic scripts.
'use strict';
const MO = (() => {
  const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  // cubic-bezier(x1,y1,x2,y2) → easing fn of x∈[0,1] (Newton on x, then y)
  function bez(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = u => ((ax * u + bx) * u + cx) * u, sy = u => ((ay * u + by) * u + cy) * u, dx = u => (3 * ax * u + 2 * bx) * u + cx;
    return x => {
      x = cl(x); if (x === 0 || x === 1) return x;
      let u = x; for (let i = 0; i < 8; i++) { const d = dx(u); if (Math.abs(d) < 1e-6) break; u -= (sx(u) - x) / d; }
      if (u < 0 || u > 1) { let lo = 0, hi = 1; u = x; for (let i = 0; i < 30; i++) { sx(u) < x ? lo = u : hi = u; u = (lo + hi) / 2; } }
      return sy(u);
    };
  }
  // closed-form spring step response, p = seconds since release; response ≈ settle period (s), zeta = damping ratio.
  // zeta 1 = no overshoot (default); 0.7 ≈ 4.6 % overshoot (character landing); below 0.55 is banned (jelly).
  function springAt(p, { response = .5, zeta = 1 } = {}) {
    if (p <= 0) return 0; const w = 2 * Math.PI / response, z = Math.max(.55, zeta);
    if (z >= 1) return 1 - Math.exp(-w * p) * (1 + w * p);
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * p) * (Math.cos(wd * p) + z * w / wd * Math.sin(wd * p));
  }
  return { cl, bez, springAt };
})();

const EASE = {
  out: MO.bez(.22, 1, .36, 1),            // default entrance (power3-ish)
  expoOut: MO.bez(.16, 1, .3, 1),          // snappy entrance, long settle
  inOut: MO.bez(.65, 0, .35, 1),           // moves between positions, camera
  exit: MO.bez(.55, .055, .675, .19),      // leaving: accelerate away
  sine: x => .5 - .5 * Math.cos(Math.PI * MO.cl(x)),   // lyrical drift
  linear: x => MO.cl(x),                   // only for constant drift / machines
  backOut: (s = 1.2) => x => { x = MO.cl(x); return 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2); },   // overshoot: s 1.2 ≈ 5 %, 1.7 ≈ 10 %, 1.9 ≈ 12 % (core.js backOut)
};
const springAt = MO.springAt;

// tween: value from a to b over [t0, t0+dur] (numbers or equal-length arrays)
function tw(t, t0, dur, a = 0, b = 1, ease = EASE.out) {
  const k = ease(MO.cl((t - t0) / dur));
  return Array.isArray(a) ? a.map((v, i) => v + (b[i] - v) * k) : a + (b - a) * k;
}
// 0→1 entrance at tIn (dur), 1→0 exit at tOut (dur × 0.7, ease-in): opacity / scale envelopes in one call
function enterExit(t, tIn, tOut, dur = .6, { ein = EASE.expoOut, eout = EASE.exit } = {}) {
  const d2 = dur * .7;
  return ein(MO.cl((t - tIn) / dur)) * (1 - eout(MO.cl((t - tOut) / d2)));
}
// start time of item i of n in a stagger group whose total spread is capped (default 0.5 s, per-item ≤ 0.12 s)
const staggerAt = (i, n, total = .5, per = .12) => i * Math.min(per, n > 1 ? total / (n - 1) : 0);
// beat pulse: 0→1 attack (30 ms) then exponential decay (250 ms) after every beat; phase = time of beat 0
function onBeat(t, bpm, phase = 0, { attack = .03, decay = .25, every = 1 } = {}) {
  const B = 60 / bpm * every, u = ((t - phase) % B + B) % B;
  return u < attack ? u / attack : Math.exp(-(u - attack) / decay);
}
// camera keys [[t, {x, y, z, r}], ...] → {x, y, z, r} with eased segments (default inOut); z = zoom (1 = none)
function camKeys(t, keys, ease = EASE.inOut) {
  const pick = k => ({ x: 0, y: 0, z: 1, r: 0, ...k });
  if (t <= keys[0][0]) return pick(keys[0][1]);
  for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) {
    const [ta, a] = keys[i - 1], [tb, b] = keys[i], k = ease((t - ta) / (tb - ta)), A = pick(a), Bk = pick(b);
    return { x: A.x + (Bk.x - A.x) * k, y: A.y + (Bk.y - A.y) * k, z: A.z + (Bk.z - A.z) * k, r: A.r + (Bk.r - A.r) * k };
  }
  return pick(keys[keys.length - 1][1]);
}
// colour-temperature arc: keys [[t, temp]], temp −1 (cool) … +1 (warm) → css rgba to fill over the frame with
// globalCompositeOperation 'soft-light' (or 'overlay'); strength capped at 8 % (aesthetics.md §3)
function tempArc(t, keys, max = .08) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) { const [ta, a] = keys[i - 1], [tb, b] = keys[i]; if (t >= ta) v = t >= tb ? b : a + (b - a) * EASE.inOut((t - ta) / (tb - ta)); }
  const a = Math.min(max, Math.abs(v) * max);
  return v >= 0 ? `rgba(255,170,90,${a.toFixed(3)})` : `rgba(90,150,255,${a.toFixed(3)})`;
}
