// Existing native time APIs, isolated per-shot files; called only by production code_segment.
import {createRequire} from 'node:module';
import {readFile, stat} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve, extname, sep} from 'node:path';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {fileURLToPath} from 'node:url';

export function frameTimes(shot) {
  if (!Number.isInteger(shot.frames) || shot.frames <= 0 || ![24,25,30].includes(shot.fps)) throw Error('invalid shot clock');
  return Array.from({length: shot.frames}, (_, i) => i / shot.fps);
}

export function captureViewport(shot, project = {}) {
  if (shot.engine !== 'opuscar') return {width:shot.width,height:shot.height};
  const canvas = project.canvas || {width:1920,height:1080};
  if (![[1920,1080],[1280,720],[1080,1920],[720,1280]].some(([w,h]) =>
      canvas.width === w && canvas.height === h)) throw Error('unsupported native canvas');
  return {width:canvas.width,height:canvas.height};
}

export async function render(root, output, packages, firstFrame, frameCount) {
  root = resolve(root);
  const shot = JSON.parse(await readFile(resolve(root, 'shot.json'), 'utf8'));
  let times = frameTimes(shot);
  if (firstFrame !== undefined || frameCount !== undefined) {
    const start = Number(firstFrame), count = Number(frameCount);
    if (!Number.isInteger(start) || !Number.isInteger(count) || start < 0 || count < 1 ||
        start + count > times.length) throw Error('invalid diagnostic frame range');
    times = times.slice(start, start + count);
  }
  if (!['art','lanshu','opuscar'].includes(shot.engine)) throw Error('unknown native HTML engine');
  const puppeteer = createRequire(resolve(packages))('puppeteer-core');
  const mime = {'.html':'text/html', '.js':'text/javascript', '.json':'application/json', '.css':'text/css', '.woff':'font/woff', '.woff2':'font/woff2', '.ttf':'font/ttf', '.png':'image/png', '.jpg':'image/jpeg', '.svg':'image/svg+xml'};
  const server = createServer(async (req, res) => {
    try {
      let pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      if (pathname === '/favicon.ico') { res.writeHead(204); res.end(); return; }
      if (shot.engine === 'opuscar' && /^\/(core|node_modules)\//.test(pathname)) pathname = '/engine' + pathname;
      const path = resolve(root, '.' + pathname);
      if (!path.startsWith(root + sep) || !(await stat(path)).isFile()) throw Error('outside native project');
      res.writeHead(200, {'Content-Type': mime[extname(path)] || 'application/octet-stream'});
      res.end(await readFile(path));
    } catch { res.writeHead(404); res.end(); }
  });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser, encoder, finished;
  const errors = [];
  let canvasCapture = false;
  try {
    browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH, headless: true,
      args: ['--use-angle=metal', '--ignore-gpu-blocklist']});
    const page = await browser.newPage();
    const project = shot.engine === 'opuscar' ? JSON.parse(await readFile(resolve(root, 'engine/project.json'), 'utf8')) : {};
    const viewport = captureViewport(shot, project);
    await page.setViewport({...viewport, deviceScaleFactor:1});
    await page.setRequestInterception(true);
    page.on('request', request => {
      const url = new URL(request.url());
      if (['data:', 'blob:'].includes(url.protocol) || url.origin === origin) request.continue();
      else { errors.push('external dependency ' + url.origin); request.abort(); }
    });
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if(m.type() === 'error') errors.push(m.text()); });
    page.on('response', r => { if(r.status() >= 400 && new URL(r.url()).pathname !== '/favicon.ico') errors.push(`${r.status()} ${r.url()}`); });
    if (shot.engine === 'art') {
      const spec = JSON.parse(await readFile(resolve(root, 'effective-spec.json'), 'utf8'));
      await page.evaluateOnNewDocument(data => { window.CLIP_SPEC = data; }, spec);
      await page.goto(origin + '/engine/clip.html?render=1', {waitUntil:'load'});
      await page.waitForFunction(() => window.__ready === true || !!window.__bootFailed);
      const failure = await page.evaluate(() => window.__bootFailed || null);
      if (failure) throw Error(String(failure));
    } else if (shot.engine === 'opuscar') {
      const spec = JSON.parse(await readFile(resolve(root, 'scene.json'), 'utf8'));
      await page.goto(origin + '/engine/' + spec.entry, {waitUntil:'load'});
      await page.waitForFunction(() => window.READY === true && typeof window.render === 'function');
      const duration = await page.evaluate(() => window.DUR);
      if (!(duration > 0) || Math.abs(duration * shot.fps - shot.frames) > .51) throw Error('native duration differs from bound shot');
      canvasCapture = spec.capture === 'canvas';
      if (canvasCapture && !await page.evaluate(({width,height}) => {
        const canvases = [...document.querySelectorAll('canvas')];
        const rect = canvases[0]?.getBoundingClientRect();
        return canvases.length === 1 && canvases[0].width === width && canvases[0].height === height &&
          rect.x === 0 && rect.y === 0 && rect.width === width && rect.height === height;
      }, viewport)) throw Error('canvas capture requires one full-frame native canvas');
    } else {
      await page.goto(origin + '/engine/index.html', {waitUntil:'load'});
      await page.waitForFunction(() => !!window.__timelines?.main || !!window.__hf?.buildReady);
      await page.evaluate(async () => { await Promise.all(Object.values(window.__hf?.buildReady || {})); });
    }
    await page.evaluate(async () => { await document.fonts.ready; });
    encoder = spawn(process.env.FFMPEG, ['-nostdin','-y','-v','error','-f','image2pipe','-framerate',String(shot.fps),'-c:v','png','-i','-',
      '-an','-vf',`scale=${shot.width}:${shot.height}`,'-c:v','libx264','-preset','slow','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',output], {stdio:['pipe','ignore','inherit']});
    finished = once(encoder, 'close');
    // Keep early spawn/pipe failures observed while Chromium is taking a frame.
    finished.catch(() => {});
    encoder.stdin.on('error', e => errors.push(e.message));
    for (const t of times) {
      await page.evaluate(async ({t, engine}) => {
        if (engine === 'art') { await window.prepare(t); window.renderFrame(t); }
        else if (engine === 'opuscar') await window.render(t);
        else { window.__timelines?.main?.pause().seek(t, false); window.dispatchEvent(new CustomEvent('hf-seek',{detail:{time:t}})); }
      }, {t, engine:shot.engine});
      if(errors.length) throw Error([...new Set(errors)].join('\n'));
      // Explicit canvas-only projects can export the same lossless pixels
      // without waiting for the browser compositor on every video frame.
      const frame = canvasCapture ? Buffer.from(await page.evaluate(() =>
        document.querySelector('canvas').toDataURL('image/png').split(',')[1]), 'base64') :
        await page.screenshot({type:'png'});
      if(encoder.stdin.destroyed) throw Error('FFmpeg input closed');
      if(!encoder.stdin.write(frame)) await Promise.race([
        once(encoder.stdin, 'drain'), finished.then(() => { throw Error('FFmpeg stopped before all frames'); })]);
    }
    encoder.stdin.end();
    if ((await finished)[0] !== 0) throw Error('FFmpeg failed');
    if(errors.length) throw Error([...new Set(errors)].join('\n'));
  } finally {
    if(encoder && encoder.exitCode === null) { encoder.kill(); await finished.catch(() => {}); }
    if(browser) await browser.close();
    server.closeAllConnections?.(); await new Promise(ok => server.close(ok));
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await render(...process.argv.slice(2));
}
