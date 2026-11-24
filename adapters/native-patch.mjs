import fs from 'node:fs/promises';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import { applyOperations, migrateTimeline, validateTimeline } from '../runtime/editor/lib/edit/timeline.mjs';

const [mode, native, patchFile, out] = process.argv.slice(2);
const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const base = await read(path.join(native, 'timeline.json'));
const assets = Object.fromEntries((await read(path.join(native, 'manifest.json'))).map(a => [a.id, a]));
const patch = await read(patchFile);
const timeline = applyOperations(base, patch.operations, assets);
const sections = ['clips', 'audio', 'captions', 'overlays', 'transitions', 'output'];
const singleSection = {caption: 'captions', audio: 'audio', overlay: 'overlays',
  clip_crop: 'clips', clip_volume: 'clips', output: 'output'};
const impacted = new Set(patch.operations.flatMap(({type}) => {
  const direct = singleSection[type] || singleSection[type.split('_')[0]];
  return direct ? [direct] : sections.filter(key => key !== 'output');
}));
const baseline = migrateTimeline(base);
const changed = sections.filter(key => impacted.has(key) && !isDeepStrictEqual(timeline[key], baseline[key]));
if (changed.some(key => patch.locked.includes(key))) throw Error('候选时间线改变了锁定轨道');
for (const key of sections) {
  if (!impacted.has(key)) timeline[key] = base[key] ?? baseline[key];
}
validateTimeline(timeline, assets);
if (mode === 'plan') {
  console.log(JSON.stringify({changed, timeline}));
} else if (mode === 'render') {
  process.env.PRODUCER_EXPERIMENTAL_FAST_CAPTURE = 'false';
  process.env.PRODUCER_FORCE_SCREENSHOT = 'true';
  const {composeRevision, renderRevision, hashFile} = await import('../runtime/editor/lib/edit/media.mjs');
  const signal = new AbortController().signal;
  const prepared = path.join(out, 'prepared-native');
  const assetDir = id => path.join(prepared, id);
  const used = new Set([...timeline.clips, ...timeline.audio, ...timeline.overlays].map(c => c.assetId));
  for (const id of used) {
    const a = assets[id];
    await fs.mkdir(assetDir(id), {recursive:true});
    for (const name of new Set([a.work, a.proxy].filter(Boolean))) {
      if (!/^[\w.-]+$/.test(name) || name === '.' || name === '..') throw Error('原生素材文件名无效');
      const file = name === a.work ? id + path.extname(name) : id + '-proxy.mp4';
      const source = path.join(native, 'assets', file);
      if (!a.fileHashes?.[name] || await hashFile(source) !== a.fileHashes[name]) {
        throw Error('原生素材校验失败: ' + id);
      }
      await fs.copyFile(source, path.join(assetDir(id), name));
    }
  }
  const dest = path.join(out, 'native');
  await composeRevision(dest, timeline, assets, assetDir, signal);
  await renderRevision(dest, timeline, signal, line => process.stdout.write(line + '\n'));
  await fs.rename(path.join(dest, 'video.mp4'), path.join(out, 'video.mp4'));
  await fs.copyFile(path.join(dest, 'subtitles.srt'), path.join(out, 'subtitles.srt'));
  await fs.rm(prepared, {recursive:true});
} else {
  throw Error('未知原生补丁模式');
}
