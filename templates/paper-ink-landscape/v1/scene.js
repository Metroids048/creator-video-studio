/* Original, deterministic paper/ink scene. No traced reference paths or frames. */
const canvas = document.getElementById('frame');
const ctx = canvas.getContext('2d');
canvas.width = 1280; canvas.height = 720;
const W = 1280, H = 720, D = TEMPLATE_STORY;
window.DUR = D.duration; window.FPS = 30; window.FRAME_FORMAT = 'png';
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const smooth = v => v * v * (3 - 2 * v);
function interpolate(keys, t, field) {
  if (t <= keys[0].t) return keys[0][field];
  for (let i = 1; i < keys.length; i++) if (t <= keys[i].t) {
    const a = keys[i - 1], b = keys[i], u = smooth((t - a.t) / (b.t - a.t));
    return a[field] + (b[field] - a[field]) * u;
  }
  return keys[keys.length - 1][field];
}
function height(points, x) {
  if (x <= points[0][0]) return points[0][1];
  for (let i = 1; i < points.length; i++) if (x <= points[i][0]) {
    const a = points[i - 1], b = points[i], u = smooth((x - a[0]) / (b[0] - a[0]));
    return a[1] + (b[1] - a[1]) * u;
  }
  return points[points.length - 1][1];
}
function random(seed) {
  let n = seed >>> 0;
  return () => { n = (Math.imul(n, 1664525) + 1013904223) >>> 0; return n / 4294967296; };
}
const paper = document.createElement('canvas'); paper.width = W; paper.height = H;
const p = paper.getContext('2d'), rng = random(D.seed);
p.fillStyle = '#e9e1cf'; p.fillRect(0, 0, W, H);
const wash = p.createRadialGradient(630, 330, 30, 630, 330, 790);
wash.addColorStop(0, '#f5efdf'); wash.addColorStop(1, '#dfd5bf');
p.fillStyle = wash; p.fillRect(0, 0, W, H);
for (let i = 0; i < 90000; i++) {
  p.fillStyle = `rgba(68,55,38,${rng() * .045})`;
  p.fillRect(rng() * W, rng() * H, .5 + rng(), .4 + rng());
}
p.strokeStyle = 'rgba(112,94,64,.025)'; p.lineWidth = .6;
for (let i = 0; i < 420; i++) {
  const x = rng() * W, y = rng() * H;
  p.beginPath(); p.moveTo(x, y); p.quadraticCurveTo(x + 5, y + 3, x + 22 * rng(), y + 4); p.stroke();
}
function noise(x, y, seed) {
  const v = Math.sin(x * 127.1 + y * 311.7 + seed * .017) * 43758.5453;
  return v - Math.floor(v);
}
function valueNoise(x, y, seed) {
  const ix = Math.floor(x), iy = Math.floor(y), u = smooth(x - ix), v = smooth(y - iy);
  const a = noise(ix, iy, seed), b = noise(ix + 1, iy, seed), c = noise(ix, iy + 1, seed), d = noise(ix + 1, iy + 1, seed);
  return (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v;
}
// Reuse the study's generic crest/wash technique; geometry and texture are new.
function inkLayer(points, front) {
  const layer = document.createElement('canvas'); layer.width = D.worldWidth + 1; layer.height = 900;
  const c = layer.getContext('2d'), data = c.createImageData(layer.width, layer.height);
  for (let x = 0; x < layer.width; x++) {
    const crest = height(points, x) + (valueNoise(x / 24, 0, D.seed) - .5) * 1.6;
    for (let y = Math.max(0, Math.floor(crest)); y < Math.min(900, crest + 260); y++) {
      const depth = y - crest, grain = valueNoise(x / 9, y / 13, D.seed + 31);
      const fibres = valueNoise(x / 4, depth / 38, D.seed + 83);
      const bands = Math.pow(.5 + .5 * Math.cos(depth * .3 + valueNoise(x / 37, depth / 75, D.seed + 22) * 7), 5);
      const alpha = front
        ? (.29 * Math.exp(-depth / 16) + .075 * Math.exp(-depth / 78) + .09 * bands * Math.exp(-depth / 36)) * (.8 + grain * .4 + fibres * .3)
        : .105 * Math.exp(-depth / 135) * (.85 + grain * .3);
      const i = (y * layer.width + x) * 4;
      data.data[i] = 76; data.data[i + 1] = 69; data.data[i + 2] = 52; data.data[i + 3] = clamp(alpha, 0, 1) * 255;
    }
  }
  c.putImageData(data, 0, 0); return layer;
}
const distantInk = inkLayer(D.backdrop, false), foregroundInk = inkLayer(D.terrain, true);
function person(t) {
  const x = interpolate(D.traveler, t, 'x'), y = height(D.terrain, x);
  const step = .025, velocity = (interpolate(D.traveler, t + step, 'x') - interpolate(D.traveler, Math.max(0, t - step), 'x')) / (step * 2);
  const moving = clamp(Math.abs(velocity) / 20, 0, 1), phase = x / 3.6;
  const sway = Math.sin(phase) * .7 * moving;
  ctx.save(); ctx.translate(x, y + sway); ctx.scale(velocity < -.1 ? -1 : 1, 1);
  ctx.strokeStyle = '#383a34'; ctx.lineCap = 'round'; ctx.lineWidth = 1.4;
  for (const side of [-1, 1]) {
    const stride = Math.sin(phase + (side < 0 ? Math.PI : 0)) * 3 * moving;
    ctx.beginPath(); ctx.moveTo(side, -9); ctx.quadraticCurveTo(side * 2 + stride * .6, -4, side * 2 + stride, -.5); ctx.stroke();
  }
  ctx.fillStyle = '#4b4d43'; ctx.beginPath(); ctx.moveTo(-2, -19); ctx.quadraticCurveTo(3, -20, 4, -10); ctx.lineTo(-3, -9); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = '#484b42'; ctx.beginPath(); ctx.moveTo(1, -17); ctx.quadraticCurveTo(4, -13, 5, -12); ctx.stroke();
  ctx.fillStyle = '#423e34'; ctx.beginPath(); ctx.arc(0, -22, 2.5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#9d4836'; ctx.beginPath(); ctx.moveTo(-2, -19); ctx.quadraticCurveTo(-7, -17 + sway, -11, -19 + sway); ctx.lineTo(-5, -20); ctx.closePath(); ctx.fill();
  ctx.restore();
}
function draw(t) {
  t = clamp(t, 0, D.duration);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(paper, 0, 0);
  const zoom = interpolate(D.camera, t, 'zoom'), cx = interpolate(D.camera, t, 'x');
  ctx.save(); ctx.translate(W / 2, H * .57); ctx.scale(zoom, zoom); ctx.translate(-cx, -H * .57);
  ctx.drawImage(distantInk, 0, 0); ctx.drawImage(foregroundInk, 0, 0);
  ctx.strokeStyle = 'rgba(58,67,54,.22)'; ctx.lineWidth = .65;
  ctx.beginPath();
  for (let x = 0; x <= D.worldWidth; x += 3) { const y = height(D.terrain, x); x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
  ctx.stroke(); person(t);
  ctx.font = '400 17px PaperInk'; ctx.textAlign = 'center'; ctx.fillStyle = '#616354';
  for (const label of D.labels) ctx.fillText(label.text, label.x, height(D.terrain, label.x) - 40);
  ctx.restore();
  const scene = D.scenes.find(s => t >= s.start && t < s.end) || D.scenes[D.scenes.length - 1];
  const opacity = Math.min(1, (t - scene.start) / .35, (scene.end - t) / .3);
  ctx.globalAlpha = Math.max(0, opacity); ctx.textAlign = 'center'; ctx.fillStyle = '#373b33';
  ctx.font = '400 39px PaperInk'; ctx.fillText(scene.title, W / 2, 79);
  ctx.font = '400 20px PaperInk'; ctx.fillStyle = '#74705f'; ctx.fillText(scene.caption, W / 2, 119);
  ctx.globalAlpha = 1;
}
window.renderAt = t => { draw(t); return canvas.toDataURL('image/png'); };
const face = new FontFace('PaperInk', `url(${shot.localAssets['paperink-font']})`, {weight: '100 900'});
face.load().then(loaded => { document.fonts.add(loaded); draw(0); window.ready = true; });
