import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { applyOperations, initialTimeline, duration } from '../runtime/editor/lib/edit/timeline.mjs';

// This branch imports only the pure native timeline engine. In particular it
// must not load the old environment/provider module or prepare media caches.
const planning = process.argv[2] === '--plan';
const sourceRoot = path.resolve(process.argv[planning ? 3 : 2]);
const brief = JSON.parse(planning ? readFileSync(0, 'utf8') : await fs.readFile(path.join(process.argv[3], 'brief.json'), 'utf8'));
function editorTimeline(assets) {
  const primary = assets[brief.primary];
  if (primary?.kind !== 'video') throw Error('主剪辑素材必须是视频');
  const operations = brief.operations.map(op => {
    if (op.type === 'insert' && op.out == null) return {...op, out: assets[op.assetId]?.frames};
    if (op.type === 'audio_add' && op.end == null) return {...op, end: op.start + assets[op.assetId]?.frames};
    return op;
  });
  return applyOperations(initialTimeline(primary), operations, assets);
}

if (planning) {
  const assets = {};
  for (const item of brief.inputs) {
    if (!['image', 'audio', 'video'].includes(item.kind)) continue;
    const result = spawnSync(process.env.HYPERFRAMES_FFPROBE_PATH,
      ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', path.resolve(sourceRoot, item.path)],
      {encoding: 'utf8', timeout: 30000, maxBuffer: 4 * 1024 * 1024});
    if (result.error || result.status) throw result.error ?? Error('无法读取媒体元数据：' + item.id);
    const info = JSON.parse(result.stdout);
    const video = info.streams.find(s => s.codec_type === 'video' && s.disposition?.attached_pic !== 1);
    const audio = info.streams.find(s => s.codec_type === 'audio');
    const still = item.kind === 'image';
    if (still && (!Number.isSafeInteger(item.frames) || item.frames < 1 || item.frames > 3600)) {
      throw Error('静帧素材需提供有效的帧数');
    }
    if ((item.kind === 'audio' && (!audio || video)) || (item.kind !== 'audio' && !video)) {
      throw Error('媒体类型与声明不符：' + item.id);
    }
    const seconds = Number(info.format.duration);
    if (!still && (!Number.isFinite(seconds) || seconds <= 0 || seconds > 600.1)) throw Error('素材时长必须不超过 10 分钟');
    const rotation = Number(video?.tags?.rotate || video?.side_data_list?.find(s => s.rotation !== undefined)?.rotation || 0);
    const sideways = Math.abs(rotation) % 180 === 90;
    let width = video ? (sideways ? video.height : video.width) : 0;
    let height = video ? (sideways ? video.width : video.height) : 0;
    if (still) { width = Math.ceil(width / 2) * 2; height = Math.ceil(height / 2) * 2; }
    if (video) {
      const factor = Math.min(1, 1920 / width, 1920 / height, 1080 / Math.min(width, height));
      width = Math.max(64, Math.floor(width * factor / 2) * 2);
      height = Math.max(64, Math.floor(height * factor / 2) * 2);
    }
    assets[item.id] = {id: item.id, kind: video ? 'video' : 'audio', status: 'ready',
      frames: still ? item.frames : Math.floor(seconds * 30 + 0.00001), width, height, hasAudio: !still && !!audio};
  }
  const timeline = editorTimeline(assets);
  console.log(JSON.stringify({valid: true, frames: duration(timeline), output: timeline.output,
    clips: timeline.clips.length, captions: timeline.captions.length, audio: timeline.audio.length,
    check: 'native_operations_with_source_metadata', media_prepared: false,
    limits: 'Source metadata frame bounds; normalization and rendering must revalidate the actual prepared media.'}));
} else {
const { prepareAsset, composeRevision, renderRevision, hashFile, ffmpeg } = await import('../runtime/editor/lib/edit/media.mjs');

// The pinned producer's experimental drawElementImage path is incompatible
// with this Chrome. Preserve the native timeline and use ordinary capture.
process.env.PRODUCER_EXPERIMENTAL_FAST_CAPTURE = 'false';
process.env.PRODUCER_FORCE_SCREENSHOT = 'true';
const [project, out] = process.argv.slice(2);
const signal = new AbortController().signal;
const native = path.join(out, 'native');
const inputDir = path.join(out, 'prepared');
const assetDir = id => path.join(inputDir, id);
const assets = {};

function transcode(...args) {
  const result = spawnSync(ffmpeg, ['-nostdin', '-v', 'error', '-y', ...args], {stdio: 'inherit'});
  if (result.error || result.status) throw result.error ?? Error('FFmpeg 转换素材失败');
}

for (const item of brief.inputs) {
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(item.id) || assets[item.id]) throw Error('无效或重复素材 ID');
  const source = path.resolve(project, item.path);
  if (!source.startsWith(project + path.sep) || await hashFile(source) !== item.sha256) throw Error('源素材校验失败');
  if (!['image', 'audio', 'video'].includes(item.kind)) continue;
  const dir = assetDir(item.id);
  await fs.mkdir(dir, {recursive: true});
  let original = 'original' + path.extname(source);
  if (item.kind === 'image') {
    if (!Number.isInteger(item.frames) || item.frames < 1 || item.frames > 3600) throw Error('静帧素材需提供有效的帧数');
    original = 'still.mp4';
    transcode('-loop', '1', '-i', source, '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2,setsar=1,fps=30',
      '-frames:v', String(item.frames), '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path.join(dir, original));
  } else await fs.copyFile(source, path.join(dir, original));
  assets[item.id] = await prepareAsset(dir, {id: item.id, original, source: item.id}, signal);
}
const timeline = editorTimeline(assets);
await composeRevision(native, timeline, assets, assetDir, signal);
await renderRevision(native, timeline, signal, line => process.stdout.write(line + '\n'));
await fs.copyFile(path.join(native, 'video.mp4'), path.join(out, 'video.mp4'));
await fs.copyFile(path.join(native, 'subtitles.srt'), path.join(out, 'subtitles.srt'));
await fs.rm(path.join(native, 'video.mp4'));
await fs.rm(inputDir, {recursive: true});
}
