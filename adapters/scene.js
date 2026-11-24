const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('2d');
const {width: w, height: h, title, kicker, accent, motif} = shot;
canvas.width = w;
canvas.height = h;
window.DUR = shot.frames / shot.fps;
window.FPS = shot.fps;
window.FRAME_FORMAT = 'jpeg';

function rect(x, y, width, height, radius, fill) {
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  ctx.fill();
}

function text(value, x, y, size, color, align = 'left', family = 'Studio') {
  ctx.font = `${size}px ${family}`;
  ctx.textAlign = align;
  ctx.fillStyle = color;
  ctx.fillText(value, x, y);
}

function lines(value, width, size) {
  ctx.font = `${size}px Studio`;
  const result = [''];
  for (const glyph of value) {
    if (glyph === '\n') result.push('');
    else {
      if (ctx.measureText(result.at(-1) + glyph).width > width) result.push('');
      result[result.length - 1] += glyph;
    }
  }
  return result;
}

function drawPhone(x, y, scale, phase) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.rotate(motif === 'draft' ? -0.12 : 0.05);
  rect(-115, -166, 230, 332, 26, '#14171d');
  rect(-108, -159, 216, 318, 22, '#252a34');
  rect(-30, -143, 60, 5, 2, '#858a91');
  if (motif === 'draft') {
    rect(-79, -57, 158, 77, 14, accent);
    text('我没事', 0, -10, 32, '#1f2528', 'center');
    const progress = Math.min(1, Math.max(0, (phase - 0.35) * 3));
    rect(-78, 32, progress * 156, 5, 2, '#efaa87');
    text('未发送', 0, 86, 22, '#c8bdac', 'center');
  } else if (motif === 'typing') {
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.fillStyle = accent;
      ctx.arc(-40 + i * 40, 4 + 8 * Math.sin(phase * 13 - i), 7, 0, Math.PI * 2);
      ctx.fill();
    }
    text('对方正在输入', 0, 68, 22, '#c8bdac', 'center');
  } else if (motif === 'answer') {
    const rise = Math.min(1, phase * 3);
    rect(-86, 28 - rise * 77, 172, 80, 13, accent);
    text('我听着', 0, 78 - rise * 77, 31, '#202625', 'center');
  } else {
    rect(-76, -41, 152, 82, 14, accent);
    text('换个办法', 0, 10, 29, '#202625', 'center');
  }
  ctx.restore();
}

function drawLetter(x, y, scale, phase) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(0.12 * (1 - Math.min(1, phase * 3)));
  ctx.scale(scale, scale);
  rect(-165, -113, 330, 226, 8, '#dfd3b5');
  ctx.strokeStyle = '#9e896f';
  ctx.lineWidth = 2;
  for (let y = -70; y < 95; y += 28) {
    ctx.beginPath();
    ctx.moveTo(-133, y);
    ctx.lineTo(133, y);
    ctx.stroke();
  }
  text('我今天有点难过', 0, 4, 33, '#322521', 'center');
  ctx.restore();
}

function drawTelescope(x, y, scale, phase) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.rotate(-0.18 + 0.10 * Math.sin(phase * Math.PI));
  rect(-151, -87, 302, 174, 12, '#5a504e');
  rect(-142, -78, 284, 156, 8, '#ded1b3');
  ctx.fillStyle = '#504f58';
  for (const row of [-39, 3, 45]) {
    for (const col of [-98, -38, 28, 92]) rect(col - 13, row - 9, 26, 19, 3, '#9b816e');
  }
  if (motif === 'last-desk') rect(79, 36, 27, 19, 3, accent);
  if (motif === 'telescope') {
    ctx.rotate(-.32);
    rect(-117, -25, 187, 46, 13, '#676980');
    rect(46, -37, 78, 69, 13, '#a79eb3');
    rect(108, -39, 18, 73, 8, accent);
    rect(-129, -16, 24, 27, 5, accent);
  }
  ctx.restore();
}

function draw(time) {
  const unit = Math.min(w / 540, h / 740);
  const portrait = h > w;
  const x = portrait ? w / 2 : w * 0.72;
  const y = portrait ? h * 0.52 : h * 0.50;
  const gradient = ctx.createLinearGradient(0, 0, w, h);
  gradient.addColorStop(0, '#292637');
  gradient.addColorStop(1, '#141820');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 92; i++) {
    ctx.fillStyle = i % 4 === 0 ? '#ffffff28' : '#ffffff10';
    ctx.fillRect((73 * i * i + 39) % w, (93 * i + 29 * i * i) % h, 2 * unit, 2 * unit);
  }
  const phase = Math.max(0, Math.min(1, time / DUR));
  const light = ctx.createRadialGradient(x, y, 16, x, y, 224 * unit);
  light.addColorStop(0, accent + '55');
  light.addColorStop(1, accent + '00');
  ctx.fillStyle = light;
  ctx.fillRect(0, 0, w, h);
  rect(w * .085, h * .085, 26 * unit, 2 * unit, 1, accent);
  text(kicker, w * .085, h * .085 + 28 * unit, 17 * unit, accent);
  lines(title, w * (portrait ? .83 : .44), 39 * unit).forEach((line, i) =>
    text(line, w * .085, h * .22 + i * 49 * unit, 39 * unit, '#f4ecde'));
  const drawObject = {
    letter: drawLetter,
    telescope: drawTelescope,
    'last-desk': drawTelescope,
  }[motif] || drawPhone;
  drawObject(x, y + Math.sin(phase * Math.PI) * 10 * unit, unit, phase);
  const cue = shot.cues.find(c => time >= c.start / FPS && time < c.end / FPS);
  if (cue) {
    const rows = lines(cue.text, w * .76, 25 * unit);
    const top = h * .842 - rows.length * 15 * unit;
    rect(w * .075, top - 23 * unit, w * .85, (rows.length * 34 + 15) * unit, 10 * unit, '#10131ce8');
    rows.forEach((line, i) => text(line, w / 2, top + i * 34 * unit, 25 * unit, '#f4ecde', 'center'));
  }
  rect(w * .085, h * .946, w * .83, 2 * unit, 1, '#ffffff33');
  rect(w * .085, h * .946, Math.max(1, w * .83 * phase), 2 * unit, 1, accent);
}

window.renderAt = (time, type = 'image/jpeg', quality = .93) => {
  draw(time);
  return canvas.toDataURL(type, quality);
};
document.fonts.load('30px Studio').then(() => {
  const previewStart = performance.now();
  window.ready = true;
  if (!location.search.includes('render')) {
    const preview = now => {
      draw((now - previewStart) / 1000 % DUR);
      requestAnimationFrame(preview);
    };
    requestAnimationFrame(preview);
  }
});
