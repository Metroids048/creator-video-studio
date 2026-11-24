// render.mjs — one renderer for every vibe-film project. Usually called through the project's ./vf wrapper,
// which passes --root. The page (film/index.html for knowledge shorts, studio.html for lyric MVs) must expose:
//   window.ready = true once fonts/assets are loaded
//   window.renderAt(t, type?, q?) → data URL of frame t (may be async). MUST be a pure function of t.
//   window.DUR (seconds), optional window.FPS, window.FRAME_FORMAT ('png' | 'jpeg'), window.events(), window.renderSheet()
//
// LOOK (open the image with Read):
//   --sheet=1,5,9 [--cols=3] [--w=640] [--crop=x,y,w,h] --out=out/check/a.jpg   contact sheet at chosen times
//   --sheet=every:2 …                                                         one tile every 2 s over the whole film
//   --strip=12.0:14.0 [--step=6] [--cols=6] [--w=320] --out=…                  motion strip: 6 fps (or every frame with --step=fps)
//   --stills=10.4,20 --out=out/stills                                          full-res frames
// MAKE:
//   --events --out=audio/events.json                                           sound events from the page's own model
//   --subs --out=out/subs.json                                                 subtitle rows [start, end, text, mode] (qa caption_sync)
//   --clip=0:10 [--audio=…] --out=out/check/open10.mp4                         fast preview MP4 (one worker) — the 10-second gate
//   --frames [--range=a:b] [--workers=4] [--reuse=out/frames:0:45]             frames → out/frames[-variant] (parallel, resumable)
//            [--fresh | --keep]     stale cache (sources edited since): wipe it / keep it (you deleted the changed ranges)
//   --encode [--audio=…] [--grade[=pop|night-film|paper|watercolor]] [--crf=16] --out=out/film.mp4               frames → MP4
// ANY MODE: --variant=<name> (page reads ?variant=, frames go to out/frames-<name>), --fps=N, --gpu=metal|soft|vulkan
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, existsSync, statSync, renameSync, readdirSync, copyFileSync, unlinkSync, constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve, join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { cpus } from 'node:os';

const KIT = dirname(fileURLToPath(import.meta.url));
const puppeteer = createRequire(join(KIT, 'package.json'))('puppeteer-core');
const args = Object.fromEntries(process.argv.slice(2).map(a => { const i = a.indexOf('='); return i < 0 ? [a.replace(/^--/, ''), true] : [a.slice(2, i), a.slice(i + 1)]; }));
const ROOT = resolve(args.root || '.');
const PAGE = ['film/index.html', 'studio.html'].map(p => join(ROOT, p)).find(existsSync);
const FF = process.env.FFMPEG || 'ffmpeg';
const CHROME = args.chrome || process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const VARIANT = args.variant && args.variant !== true ? args.variant : '';
const FRAMES = join(ROOT, args['frames-dir'] || (VARIANT ? `out/frames-${VARIANT}` : 'out/frames'));
const out = (d) => resolve(ROOT, args.out || d);
const nums = s => String(s).split(',').map(Number);
const span = s => String(s).split(':').map(Number);
const pad = i => String(i).padStart(5, '0');
const run = (cmd, a) => new Promise((ok, bad) => { const p = spawn(cmd, a, { stdio: 'inherit' }); p.on('close', c => c ? bad(new Error(`${cmd} exited ${c}`)) : ok()); });

// Validate frozen performances before opening Chrome or spending time on frames.
function checkAudio() {
  if (args['audio-sha256'] && !args.audio) throw new Error('--audio-sha256 requires --audio');
  if (!args.audio) return;
  const audio = resolve(ROOT, String(args.audio));
  if (!existsSync(audio) || !statSync(audio).isFile()) throw new Error(`audio missing: ${audio}`);
  if (args['audio-sha256'] && createHash('sha256').update(readFileSync(audio)).digest('hex') !== args['audio-sha256'])
    throw new Error('frozen audio changed — restore the approved performance; do not regenerate it');
}
checkAudio();
if (!PAGE) { console.error(`no film/index.html or studio.html under ${ROOT}`); process.exit(1); }

// ---------- frame cache stamp ----------
// out/frames*/stamp.json records what the frames were rendered from. Edited sources + old frames = an old film encoded
// under a new name, so --frames refuses stale frames (--fresh wipes them, --keep = "I deleted the changed ranges myself")
// and --encode refuses a cache that is stale or incomplete.
function sourceHash() {
  const h = createHash('sha256'), walk = d => { for (const n of readdirSync(d).sort()) { const f = join(d, n);
    if (statSync(f).isDirectory()) walk(f); else if (/\.(js|mjs|html|css|json)$/.test(n)) h.update(n).update(readFileSync(f)); } };
  for (const d of ['film', 'src']) if (existsSync(join(ROOT, d))) walk(join(ROOT, d));
  if (existsSync(join(ROOT, 'studio.html'))) h.update(readFileSync(join(ROOT, 'studio.html')));
  return h.digest('hex').slice(0, 16);
}
const STAMP = join(FRAMES, 'stamp.json');
const readStamp = () => existsSync(STAMP) ? JSON.parse(readFileSync(STAMP, 'utf8')) : null;
const frameFiles = () => existsSync(FRAMES) ? readdirSync(FRAMES).filter(f => /^f\d{5}\.(jpg|png)$/.test(f)).sort() : [];

// ---------- finishing grades (references/aesthetics.md §7): --grade = pop, --grade=<name>, or a raw ffmpeg -vf chain ----------
const GRADES = {
  pop: 'eq=saturation=1.15:contrast=1.04:gamma=1.02',   // the lyric-MV default (挪威的森林)
  'night-film': "eq=contrast=1.05:saturation=1.06:gamma=0.98,curves=all='0/0.02 0.15/0.12 0.5/0.5 0.85/0.88 1/0.97',colorbalance=rs=-0.02:bs=0.03:rh=0.03:bh=-0.02,noise=alls=3:allf=t",
  paper: "eq=contrast=1.03:saturation=1.04,curves=all='0/0.03 0.5/0.49 1/0.96'",
  watercolor: 'eq=contrast=1.03:saturation=1.10:gamma=1.01,colorbalance=rh=0.02:bh=-0.02',
};
// ---------- encode (no browser) ----------
if (args.encode) {
  const st = readStamp(), files = frameFiles();
  if (!st) { console.error(`no ${STAMP} — render with --frames first`); process.exit(1); }
  if (st.sources !== sourceHash() && !args.keep) { console.error(`frames in ${FRAMES} were rendered from older sources — ./vf frames --fresh (or --keep after deleting the changed ranges and re-rendering them)`); process.exit(4); }
  const ext = st.ext, fps = +(args.fps || st.fps), mine = files.filter(f => f.endsWith(ext));
  if (mine.length !== files.length) { console.error(`${FRAMES} mixes jpg and png frames — clean it`); process.exit(1); }
  const missing = []; for (let i = 0; i < st.count; i++) if (!existsSync(join(FRAMES, `f${pad(i)}.${ext}`))) missing.push(i);
  if (missing.length) { console.error(`${missing.length} of ${st.count} frames missing in ${FRAMES} (first: ${missing[0]}) — run --frames again (it resumes)`); process.exit(1); }
  const o = out('out/film.mp4'), audio = args.audio ? resolve(ROOT, args.audio) : '';
  mkdirSync(dirname(o), { recursive: true });
  console.log(`encoding ${files.length} frames @${fps} → ${o}${audio ? ' + ' + audio : ''}`);
  await run(FF, ['-y', '-loglevel', 'error', '-stats', '-framerate', String(fps), '-i', join(FRAMES, `f%05d.${ext}`),
    // an already-mastered AAC track is copied: a second AAC pass adds another ~0.6 dB of true-peak overshoot
    // length = the frames, not -shortest: with a copied audio track ffmpeg 4.4's -shortest cut the video 2.75 s early
    // (挪威的森林 v6: 2099 of 2165 frames — caught by the frame-by-frame review, not by QA; QA now checks it too)
    ...(audio ? ['-i', audio, '-map', '0:v', '-map', '1:a', ...(/\.(m4a|aac)$/i.test(audio) ? ['-c:a', 'copy'] : ['-c:a', 'aac', '-b:a', '256k'])] : []),
    '-t', (st.count / fps).toFixed(3),
    ...(args.grade ? ['-vf', GRADES[args.grade === true ? 'pop' : args.grade] || String(args.grade)] : []),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', String(args.crf || 16), '-pix_fmt', 'yuv420p', '-x264-params', 'aq-mode=3',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', o]);
  checkAudio();
  console.log('ENCODE_DONE ' + o);
  process.exit(0);
}

// ---------- browser ----------
const GPU = { metal: ['--use-angle=metal'], soft: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'], vulkan: ['--use-angle=vulkan', '--enable-features=Vulkan'] };
const gpu = GPU[args.gpu] || (process.platform === 'darwin' ? GPU.metal : ['--use-gl=angle']);
const browser = await puppeteer.launch({
  executablePath: CHROME, headless: true, protocolTimeout: 300000,
  args: [...(process.platform === 'linux' ? ['--no-sandbox'] : []), '--allow-file-access-from-files', '--ignore-gpu-blocklist', ...gpu,
    '--enable-gpu-rasterization', '--window-size=1920,1080', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'],
});
const url = pathToFileURL(PAGE).href + '?render' + (VARIANT ? '&variant=' + encodeURIComponent(VARIANT) : '');
async function openPage(tag = '') {
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  page.on('console', m => { if (['error', 'warn'].includes(m.type())) console.log(`[page${tag}]`, m.text()); });
  // a script error before window.ready used to surface only as a 120 s waitForFunction timeout (潮汐锁定 pilot): fail at once
  let failLoad; const loadError = new Promise((_, bad) => { failLoad = bad; }); loadError.catch(() => {});
  page.on('pageerror', e => { console.log(`[page error${tag}]`, e.message); failLoad(new Error(`page script error before ready: ${e.message} — run: node --check film/*.js src/**/*.js`)); });
  page.on('requestfailed', r => console.log(`[request failed${tag}]`, r.url().slice(0, 120), r.failure()?.errorText));
  await page.goto(url, { waitUntil: 'load', timeout: 120000 });
  await Promise.race([page.waitForFunction('window.ready === true', { timeout: 120000 }), loadError]);
  failLoad = () => {};   // after ready, page errors are logged (above) but don't abort a long render
  if (args.loop) await page.evaluate(n => { window.LOOP = LOOPS[n]; }, args.loop);
  return page;
}
// top-level const in a classic script is a global binding but not a window property: read either
const meta = page => page.evaluate(() => {
  const g = n => { try { return eval(n); } catch { return window[n]; } };
  return { DUR: window.LOOP ? window.LOOP.len : g('DUR'), FPS: g('FPS'), FORMAT: window.FRAME_FORMAT };
});
const frameOf = async (page, t, type, q) => { const u = await page.evaluate((t, type, q) => window.renderAt(t, type, q), t, type, q); return Buffer.from(u.slice(u.indexOf(',') + 1), 'base64'); };
const save = (f, buf) => { mkdirSync(dirname(f), { recursive: true }); writeFileSync(f + '.tmp', buf); renameSync(f + '.tmp', f); };

// generic contact sheet for pages without their own renderSheet: tiles of renderAt() with a time label
async function sheet(page, ts, cols, w, crop) {
  if (await page.evaluate(() => typeof window.renderSheet === 'function') && !args.generic) {
    const at = args['crop-at'] ? String(args['crop-at']).split(',').map(v => isNaN(+v) ? v : +v) : null;
    return (await page.evaluate((ts, c, w, crop, at) => window.renderSheet(ts, c, w, crop, at), ts, cols, w, crop, at)).url;
  }
  return page.evaluate(async (ts, cols, w, crop) => {
    let s, x, h;
    for (let i = 0; i < ts.length; i++) {
      const img = new Image(); img.src = await window.renderAt(ts[i], 'image/jpeg', .9); await img.decode();
      const [cx, cy, cw, ch] = crop || [0, 0, img.width, img.height];
      if (!s) { h = Math.round(w * ch / cw); s = document.createElement('canvas'); s.width = cols * w; s.height = Math.ceil(ts.length / cols) * h; x = s.getContext('2d'); x.fillStyle = '#222'; x.fillRect(0, 0, s.width, s.height); }
      const X = (i % cols) * w, Y = Math.floor(i / cols) * h;
      x.drawImage(img, cx, cy, cw, ch, X, Y, w, h);
      x.fillStyle = 'rgba(0,0,0,.65)'; x.fillRect(X, Y, 78, 22); x.fillStyle = '#fff'; x.font = '15px Menlo, monospace'; x.fillText(ts[i].toFixed(2) + 's', X + 5, Y + 16);
    }
    return s.toDataURL('image/jpeg', .9);
  }, ts, cols, w, crop);
}

try {
  if (args.sheet || args.strip) {
    const page = await openPage(), m = await meta(page), fps = +(args.fps || m.FPS || 24);
    let ts;
    if (args.strip) { const [a, b] = span(args.strip), step = +(args.step || 6); ts = []; for (let t = a; t <= b + 1e-6; t += 1 / step) ts.push(+t.toFixed(4)); }
    else if (String(args.sheet).startsWith('every:')) { const d = +String(args.sheet).slice(6); ts = []; for (let t = d / 2; t < m.DUR; t += d) ts.push(+t.toFixed(3)); }
    else ts = nums(args.sheet);
    ts = ts.map(t => Math.min(Math.round(t * fps) / fps, m.DUR - 1 / fps));
    const o = out('out/check/sheet.jpg'), u = await sheet(page, ts, +(args.cols || (args.strip ? 6 : 4)), +(args.w || (args.strip ? 320 : 480)), args.crop ? nums(args.crop) : null);
    save(o, Buffer.from(u.slice(u.indexOf(',') + 1), 'base64'));
    console.log(`${o}  (${ts.length} tiles)`);
  } else if (args.stills) {
    const page = await openPage(), o = out('out/stills');
    for (const t of nums(args.stills)) { const f = join(o, `t${t.toFixed(2)}.png`); save(f, await frameOf(page, t, 'image/png')); console.log(f); }
  } else if (args.events) {
    const page = await openPage(), ev = await page.evaluate(() => window.events());
    save(out('audio/events.json'), Buffer.from(JSON.stringify(ev))); console.log('events → ' + out('audio/events.json'));
  } else if (args.subs) {   // film.js keeps SUBS as a top-level const: visible to evaluate in the page's global scope
    const page = await openPage(), rows = await page.evaluate(() => typeof SUBS === 'undefined' ? [] : SUBS.map(r => [r[0], r[1], String(r[2]).replace(/\*\*/g, ''), r[4] || 'bottom']));
    save(out('out/subs.json'), Buffer.from(JSON.stringify(rows))); console.log(`subs → ${out('out/subs.json')} (${rows.length} lines)`);
  } else if (args.clip) {
    const page = await openPage(), m = await meta(page), fps = +(args.fps || m.FPS || 24);
    const [a, b] = typeof args.clip === 'string' ? span(args.clip) : args.range ? span(args.range) : [0, m.DUR];
    const audio = args.audio ? resolve(ROOT, args.audio) : await page.evaluate(() => { try { return PROJECT.audio || ''; } catch { return ''; } }).then(p => p ? resolve(dirname(PAGE), p) : '');
    const o = out('out/check/clip.mp4'); mkdirSync(dirname(o), { recursive: true });
    const ff = spawn(FF, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      ...(audio && existsSync(audio) ? ['-ss', String(a), '-t', String(b - a), '-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', o], { stdio: ['pipe', 'inherit', 'inherit'] });
    let ffDone = false; ff.on('close', c => { ffDone = true; if (c) { console.error(`ffmpeg exited ${c} — clip not written`); process.exitCode = 1; } });
    ff.stdin.on('error', () => {});   // ffmpeg died: the close handler reports why
    const n = Math.round((b - a) * fps), t0 = Date.now();
    for (let i = 0; i < n; i++) {
      if (ffDone) break;
      if (!ff.stdin.write(await frameOf(page, a + i / fps, 'image/jpeg', .93))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % (fps * 2) === 0) console.log(`clip ${i + 1}/${n}  ${((Date.now() - t0) / (i + 1)).toFixed(0)} ms/frame`);
    }
    ff.stdin.end(); if (!ffDone) await new Promise(r => ff.on('close', r));
    if (!process.exitCode) console.log('CLIP_DONE ' + o);
  } else if (args.frames) {
    const probe = await openPage(), m = await meta(probe); await probe.close();
    const fps = +(args.fps || m.FPS || 24), ext = m.FORMAT === 'png' || args.png ? 'png' : 'jpg', type = ext === 'png' ? 'image/png' : 'image/jpeg';
    if (!Number.isFinite(m.DUR) || m.DUR <= 0) { console.error(`page has no valid DUR (${m.DUR}) — unknown --variant=${VARIANT}?`); process.exit(1); }
    const [a, b] = args.range ? span(args.range) : [0, m.DUR];
    mkdirSync(FRAMES, { recursive: true });
    const stamp = { sources: sourceHash(), fps, dur: m.DUR, ext, count: Math.round(m.DUR * fps), variant: VARIANT || null }, old = readStamp(), have = frameFiles();
    const stale = have.length && (!old || ['sources', 'fps', 'dur', 'ext'].some(k => old[k] !== stamp[k]));
    if (stale && args.fresh) { for (const f of have) unlinkSync(join(FRAMES, f)); console.log(`sources changed: wiped ${have.length} stale frames`); }
    else if (stale && !(args.keep && old && old.fps === fps && old.ext === ext)) {
      console.error(`${FRAMES} holds frames from ${old ? 'older sources/settings' : 'an unknown render'} — rerun with --fresh (re-render all) or, after deleting the changed time ranges, --keep`);
      process.exit(4);
    }
    if (args.reuse) {   // clone frames that are identical in another render (APFS clone: no extra disk)
      const [dir, ra, rb] = String(args.reuse).split(':'), src = resolve(ROOT, dir);
      let k = 0; for (let i = Math.round(+ra * fps); i < Math.round(+rb * fps); i++) {
        const s = join(src, `f${pad(i)}.${ext}`), d = join(FRAMES, `f${pad(i)}.${ext}`);
        if (existsSync(s) && !existsSync(d)) { copyFileSync(s, d, constants.COPYFILE_FICLONE); k++; }
      }
      console.log(`reused ${k} frames from ${src}`);
    }
    const first = Math.round(a * fps), last = Math.min(stamp.count, Math.round(b * fps)) - 1;   // same frame count as the stamp
    const todo = []; for (let i = first; i <= last; i++) { const f = join(FRAMES, `f${pad(i)}.${ext}`); if (!existsSync(f) || statSync(f).size < 1000) todo.push(i); }
    const workers = Math.max(1, +(args.workers || Math.min(4, Math.floor(cpus().length / 2))));
    console.log(`${todo.length} frames to render (${last - first + 1 - todo.length} already there), ${workers} workers → ${FRAMES}`);
    let next = 0, done = 0; const t0 = Date.now();
    const opener = async w => {   // a page that misses its ready deadline under load gets two more tries
      for (let k = 1; ; k++) { try { return await openPage('#' + w); } catch (e) { if (k >= 3) throw e; console.log(`[worker ${w}] page open failed (${e.message.slice(0, 60)}), retry ${k}`); } }
    };
    // GPU canvases wear out over a long sequential render: 蚂蚁不堵车 v9 (many full-size offscreens + blur filters per
    // frame) wrote 553 blank frames from frame 1193 on in all four workers at once, while single stills were fine.
    // So: a page is recycled every RECYCLE frames, and a frame whose size collapses below 15 % of the worker's recent
    // median is treated as a failure (blank canvas) and re-rendered on a fresh page.
    const RECYCLE = +(args.recycle || 300);
    await Promise.all(Array.from({ length: Math.min(workers, todo.length) }, async (_, w) => {
      let page = await opener(w), used = 0; const recent = [];
      while (next < todo.length) {
        const i = todo[next++];
        if (used >= RECYCLE) { await page.close().catch(() => {}); page = await opener(w); used = 0; }
        for (let attempt = 1; ; attempt++) {
          try {
            const buf = await frameOf(page, i / fps, type, .95); used++;
            const med = recent.length >= 5 ? [...recent].sort((x, y) => x - y)[recent.length >> 1] : 0;
            if (med && buf.length < .15 * med && attempt < 3) throw new Error(`blank frame? ${buf.length} B vs recent median ${med} B`);
            if (med && buf.length < .15 * med) console.log(`[worker ${w}] frame ${i} is still tiny on a fresh page — kept as a genuinely sparse frame; check it`);
            save(join(FRAMES, `f${pad(i)}.${ext}`), buf); recent.push(buf.length); if (recent.length > 15) recent.shift();
            break;
          } catch (e) {   // a hung, crashed or worn-out tab: reopen it and retry the same frame instead of killing the render
            console.log(`[worker ${w}] frame ${i} failed (${e.message.slice(0, 80)}), attempt ${attempt}`);
            if (attempt >= 3) throw e;
            await page.close().catch(() => {}); page = await opener(w); used = 0;
          }
        }
        if (++done % (fps * 4) === 0 || done === todo.length) {
          const el = (Date.now() - t0) / 1000;
          console.log(`frame ${done}/${todo.length}  ${(el / done * 1000).toFixed(0)} ms/frame  eta ${((todo.length - done) * el / done / 60).toFixed(1)} min`);
        }
      }
    }));
    // second line of defence: a frame whose PNG is much smaller than both neighbours (which agree with each other) lost
    // layers — 蚂蚁不堵车 v9 had ~50 such frames that were too big for the blank test. Re-render them on a fresh page.
    for (let pass = 1; pass <= 2; pass++) {
      const size = i => { const f = join(FRAMES, `f${pad(i)}.${ext}`); return existsSync(f) ? statSync(f).size : 0; };
      const sus = []; for (let i = Math.max(first, 1); i < Math.min(last, stamp.count - 1); i++) {
        const a = size(i - 1), b = size(i), c = size(i + 1);
        if (a && c && Math.abs(a - c) < .2 * Math.max(a, c) && b < .7 * Math.min(a, c)) sus.push(i);
      }
      if (!sus.length) break;
      console.log(`suspect frames (smaller than both neighbours) pass ${pass}: ${sus.length} — ${sus.slice(0, 12).join(',')}${sus.length > 12 ? '…' : ''} → re-render on a fresh page`);
      let page = await opener('S');
      for (const [k, i] of sus.entries()) {
        if (k && k % RECYCLE === 0) { await page.close().catch(() => {}); page = await opener('S'); }
        save(join(FRAMES, `f${pad(i)}.${ext}`), await frameOf(page, i / fps, type, .95));
      }
      await page.close().catch(() => {});
    }
    writeFileSync(STAMP, JSON.stringify(stamp));
    console.log(`FRAMES_DONE ${todo.length} in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  } else {
    console.log('nothing to do — see the usage notes at the top of render.mjs');
  }
} finally { await browser.close(); }
