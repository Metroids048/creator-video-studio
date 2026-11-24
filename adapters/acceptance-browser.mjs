import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(new URL('../runtime/vibe/package.json', import.meta.url));
const browser = await require('puppeteer-core').launch({
  executablePath: process.env.CHROME_PATH,
  headless: true,
  args: ['--autoplay-policy=no-user-gesture-required'],
});
const [port, out] = process.argv.slice(2);
const origin = `http://127.0.0.1:${port}`;
const cases = [
  ['unsent', '/deliveries/unsent-v0002/video.mp4'],
  ['focus', '/deliveries/focus-v0001/video.mp4'],
  ['last-desk', '/deliveries/last-desk-v0001/video.mp4'],
];
try {
  const results = [];
  for (const [id, file] of cases) {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(origin + '/.studio/review/player.html', {waitUntil: 'load'});
    const playback = page.evaluate(async source => {
      const video = document.querySelector('video');
      const spans = [];
      video.src = URL.createObjectURL(await (await fetch(source)).blob());
      await video.play();
      await new Promise((resolve, reject) => {
        video.addEventListener('ended', resolve, {once: true});
        video.addEventListener('error', reject, {once: true});
        video.addEventListener('timeupdate', () => spans.push(video.currentTime));
      });
      const quality = video.getVideoPlaybackQuality();
      return {duration: video.duration, ended: video.ended, currentTime: video.currentTime,
        width: video.videoWidth, height: video.videoHeight, decodedFrames: quality.totalVideoFrames,
        droppedFrames: quality.droppedVideoFrames, checkpoints: spans.length, seeking: video.seeking};
    }, file).then(result => ({result}), error => ({error: error.message}));
    await page.waitForFunction(() => document.querySelector('video').currentTime >= 3, {timeout: 15000});
    await page.screenshot({path: path.join(out, id + '-playing.jpg'), type: 'jpeg', quality: 84});
    const {result, error} = await playback;
    if (error) throw Error(`${id}: ${error}`);
    if (!result.ended || result.decodedFrames < 60 || result.checkpoints < 10 || errors.length) {
      throw new Error(JSON.stringify({id, result, errors}));
    }
    await page.close();
    results.push({id, ...result, errors});
  }
  for (const [id, file] of [['code', 'unsent/shots/02-typing/film/index.html'], ['native', 'focus/native/index.html']]) {
    const page = await browser.newPage();
    const errors = [];
    await page.setRequestInterception(true);
    page.on('request', r => new URL(r.url()).origin === origin || r.url().startsWith('data:') ? r.continue() : r.abort());
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) errors.push(r.url()); });
    await page.goto(origin + '/.studio/review/unpacked/' + file, {waitUntil: 'networkidle0'});
    const state = await page.evaluate(() => ({
      canvas: document.querySelector('canvas')?.width,
      timeline: Object.keys(window.__timelines ?? {}),
      media: [...document.querySelectorAll('video,audio')].map(e => ({source: e.getAttribute('src'), state: e.readyState})),
    }));
    if (errors.length || (id === 'code' && !state.canvas) || (id === 'native' && (!state.timeline.length || state.media.some(m => m.state < 2)))) {
      throw Error(JSON.stringify({id, state, errors}));
    }
    await page.screenshot({path: path.join(out, id + '-editable.jpg'), type: 'jpeg', quality: 84});
    results.push({id, state, errors});
    await page.close();
  }
  await writeFile(path.join(out, 'browser.json'), JSON.stringify(results, null, 2));
} finally {
  await browser.close();
}
