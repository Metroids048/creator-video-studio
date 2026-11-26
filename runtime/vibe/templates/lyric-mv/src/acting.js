// acting.js — body-acting helpers on top of clawd() (load after clawd.js). Names avoid p5 globals (point, line, …). Each returns a fragment of clawd() options
// ({ dx, dy, sq, rot, aL, aR }) to spread into the call, so a shot reads as ACTION, not just a face changing:
//   clawd(x, y, u, { ...feel('happy', t), ...anticipate(t, 3.2), ...reach(t, 3.2, 3.6, "R", .9) })
// Richness rule (references/lyric-mv.md): every shot has at least one body action (reach, jump, point, hug, sit, run…)
// plus one emotion change, and accessories follow through (follow()) instead of moving rigidly with the body.
// Pure functions of t, like everything else.

// Anticipation → action → overshoot around t0: crouch (squash) before, stretch at t0, settle with a small bounce.
function anticipate(t, t0, amt = 1, pre = .22) {
  if (t < t0 - pre || t > t0 + .6) return {};
  const a = t < t0 ? -Math.sin(seg(t, t0 - pre, t0) * Math.PI / 2) * .18 : .14 * spring(t, t0, 7, 22);
  return { sq: a * amt, dy: t < t0 ? .25 * amt * seg(t, t0 - pre, t0) : 0 };
}
// Follow-through for things that hang off the body (hat bobble, scarf, ears, a held lantern): the same motion, late
// and springy. Pass the body's own offset function; returns [dx, dy] for the accessory.
function follow(t, bodyAt, delay = .08, k = 5, w = 16) {
  const [x0, y0] = bodyAt(t - delay), [x1, y1] = bodyAt(t);
  return [x0 - x1 + (x1 - x0) * .4 * Math.exp(-k * delay) * Math.sin(w * t), y0 - y1];
}
// Arm actions. side 'L' | 'R'; angle in clawd's arm units (0 = straight out, + = up). backOut gives the snap.
function reach(t, t0, t1, side = 'R', to = .9, from = -.3) {
  if (t < t0) return {};
  const a = lerp(from, to, backOut(seg(t, t0, t1)));
  return side === 'L' ? { aL: a } : { aR: a };
}
function pointArm(t, t0, side = 'R', dur = 1.2) {   // a quick raised point with a little jab on arrival
  if (t < t0 || t > t0 + dur) return {};
  const a = 1.1 * backOut(seg(t, t0, t0 + .18)) + .08 * Math.sin((t - t0) * 30) * Math.exp(-(t - t0) * 8);
  return side === 'L' ? { aL: a, rot: -.04 } : { aR: a, rot: .04 };
}
function wave(t, t0, dur = 1.4, side = 'R') {   // hello / goodbye
  if (t < t0 || t > t0 + dur) return {};
  const a = 1 + .35 * Math.sin((t - t0) * 14) * Math.min(1, (t0 + dur - t) * 3);
  return side === 'L' ? { aL: a } : { aR: a };
}
// Two characters: walk toward each other and close the gap at t1 (hug) / end side by side holding hands.
// Returns { a: opts for the left one, b: opts for the right one } with dx in u, so call clawd(xA, …, { ...h.a }).
function hug(t, t0, t1, gapU = 6) {
  const p = ease(seg(t, t0, t1)), s = .1 * spring(t, t1, 6, 18);
  return { a: { dx: gapU * .5 * p, aR: lerp(-.2, .55, p), sq: -s, rot: .06 * p }, b: { dx: -gapU * .5 * p, aL: lerp(-.2, .55, p), sq: -s, rot: -.06 * p } };
}
function holdHands(t, t0, swing = 1) {   // arms reach down toward each other and swing together on the beat
  if (t < t0) return { a: {}, b: {} };
  const k = ease(seg(t, t0, t0 + .3)), sw = .12 * swing * Math.sin(bpOf(t) * Math.PI);
  return { a: { aR: lerp(0, -.35, k) + sw }, b: { aL: lerp(0, -.35, k) + sw } };
}
function sit(t, t0, dur = .35) {   // drop onto a seat/ground: lower, squash on contact, settle
  if (t < t0) return {};
  const p = easeOut(seg(t, t0, t0 + dur));
  return { dy: 1.6 * p, sq: .22 * Math.exp(-(t - t0 - dur) * 6) * (t > t0 + dur ? 1 : 0) + .08 * p, noLegs: p > .9 };
}
// Idle life when nothing else is happening: breathing squash, a slow weight shift, an occasional blink handled by feel().
function idle(t, seed = 0, amt = 1) { return { sq: .03 * amt * Math.sin(t * 2.4 + seed), dx: .15 * amt * Math.sin(t * .5 + seed * 2), rot: .015 * amt * Math.sin(t * .8 + seed) }; }
// Merge option fragments (later ones win per key, except dx/dy/sq/rot which add).
function act(...parts) {
  const o = {};
  for (const p of parts) for (const [k, v] of Object.entries(p || {})) o[k] = ['dx', 'dy', 'sq', 'rot'].includes(k) ? (o[k] || 0) + v : v;
  return o;
}
