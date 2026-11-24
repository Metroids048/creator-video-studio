import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { setTimeout as wait } from 'node:timers/promises';

const require = createRequire(new URL('../runtime/vibe/package.json', import.meta.url));
const puppeteer = require('puppeteer-core');
const source = fileURLToPath(new URL('../examples/source/capture-page.html', import.meta.url));
const out = resolve(process.argv[2] || 'examples/media/focus');
await mkdir(out, {recursive: true});
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
});
try {
  const page = await browser.newPage();
  await page.setViewport({width: 960, height: 540});
  await page.goto(pathToFileURL(source).href);
  await page.screenshot({path: resolve(out, 'before.png')});
  const recording = await page.screencast({path: resolve(out, 'screen.webm'), fps: 30});
  const started = Date.now();
  const actions = [];
  try {
    await wait(1700);
    for (const [selector, expected, delay] of [
      ['#start', '专注中', 4800],
      ['#pause', '已暂停', 2400],
    ]) {
      const at = Date.now() - started;
      await page.click(selector);
      const observed = await page.$eval('#status', element => element.textContent);
      if (!observed.startsWith(expected)) throw Error(`Click ${selector} produced ${observed}`);
      actions.push({selector, atMs: at, observed});
      await wait(delay);
    }
  } finally {
    await recording.stop();
  }
  await page.screenshot({path: resolve(out, 'paused.png')});
  await writeFile(resolve(out, 'capture.json'), JSON.stringify({width: 960, height: 540, actions}, null, 2));
} finally {
  await browser.close();
}
