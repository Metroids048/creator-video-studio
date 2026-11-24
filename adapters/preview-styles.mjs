import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';

const require = createRequire(new URL('../runtime/vibe/package.json', import.meta.url));
const puppeteer = require('puppeteer-core');
const [out, port] = process.argv.slice(2);
const {compiled} = JSON.parse(await readFile(resolve(out, 'compile.json'), 'utf8'));
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH,
  headless: true,
  args: ['--use-angle=metal', '--ignore-gpu-blocklist'],
});
const results = [];
try {
  for (const style of compiled) {
    const page = await browser.newPage();
    const errors = [], samples = [];
    try {
      await page.setViewport({width: 1920, height: 1080, deviceScaleFactor: .5});
      await page.setRequestInterception(true);
      page.on('request', request => {
        const url = new URL(request.url());
        if (['data:', 'blob:'].includes(url.protocol) || url.origin === `http://127.0.0.1:${port}`) request.continue();
        else {
          errors.push('依赖外部请求 ' + url.origin);
          request.abort();
        }
      });
      page.on('pageerror', error => errors.push(error.message));
      page.on('response', r => { if (r.status() >= 400 && new URL(r.url()).pathname !== '/favicon.ico') errors.push(`${r.status()} ${new URL(r.url()).pathname}`); });
      await page.goto(`http://127.0.0.1:${port}/${style}/index.html`, {waitUntil: 'load'});
      await page.waitForFunction(() => !!window.__timelines?.main || !!window.__hf?.buildReady, {timeout: 7000});
      await page.evaluate(async () => {
        await Promise.all(Object.values(window.__hf?.buildReady || {}));
        await document.fonts.ready;
      });
      for (const at of [1.2, 7, 17, 28]) {
        await page.evaluate(t => {
          window.__timelines?.main?.pause().seek(t, false);
          window.dispatchEvent(new CustomEvent('hf-seek', {detail: {time: t}}));
        }, at);
        const file = `preview-${at}.jpg`;
        const frame = await page.screenshot({type: 'jpeg', quality: 86, path: resolve(out, style, file)});
        samples.push({at, file, sha256: createHash('sha256').update(frame).digest('hex')});
      }
      if (new Set(samples.map(s => s.sha256)).size < 2) errors.push('各时间点没有可观察的帧变化');
    } catch (error) {
      errors.push(error.message);
    } finally {
      await page.close();
    }
    results.push({style, samples, errors: [...new Set(errors)]});
    console.log(style, samples.length, errors[0] || 'OK');
  }
} finally {
  await browser.close();
  await writeFile(resolve(out, 'preview.json'), JSON.stringify(results, null, 2));
}
