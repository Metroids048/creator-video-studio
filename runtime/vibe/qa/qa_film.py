"""qa_film.py <film.mp4> [--out=DIR] [--seams=t1,t2] [--profile=short|mv] [--expect=SECONDS] [--vertical] [--silent-ok]

Hard QA gate for a finished film. Measures, then rules: PASS / WARN / FAIL with reasons, written to DIR/qa.json
together with the file's sha256 (package.py refuses files whose QA is missing, stale or FAIL).
Also writes what a reviewer needs to LOOK at and does not replace looking:
  overview.jpg (1 fps), seamNN_T.jpg (8 fps around every cut — detected if --seams not given),
  spectrum.png (spectrogram), loudness.txt (short-term LUFS per second).
caption_sync (knowledge shorts): reads <film dir>/subs.json (or --subs=FILE; ./vf build writes it) and checks every
  subtitle line: within 2 s of its onset the picture ABOVE the subtitle band must visibly change (topic-and-hook.md §3).
Defaults to DIR = <film dir>/qa-<film name>.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FF = os.environ.get('FFMPEG') or 'ffmpeg'
argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if not argv:
    sys.exit(__doc__)
film = Path(argv[0]).resolve()
out = Path(opt.get('out') or film.parent / f'qa-{film.stem}').resolve()
out.mkdir(parents=True, exist_ok=True)
profile = opt.get('profile', 'short')


# motion calibration (2026-10-24, mean abs frame difference at 8 fps, 480 px, per-second median): Opus 5.5 references
# 李尺泾 星月夜 16.3 · veally 原子弹 16.0 · XML 雨爱 11.7 · Je11y 8.9 · Immanuelle 坠 1.6 (calm space); ours: 挪威 3.5,
# 同步-萤火 1.3, 光在路上 0.27 (45 % of seconds still).
STILL = 0.25   # below this a second counts as still
CALM = 1.0     # a film whose median second moves less than this reads as a slideshow


def ff(args):
    return subprocess.run([FF, '-hide_banner', *args], capture_output=True, text=True).stderr


r, fail, warn = {}, [], []
info = ff(['-i', str(film)])
r['file'] = str(film)
r['sha256'] = hashlib.sha256(film.read_bytes()).hexdigest()
m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', info)
dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
r['duration'] = round(dur, 2)
v = re.search(r'Video: .*?(\d{3,5})x(\d{3,5}).*?([\d.]+) fps', info)
r['video'] = f'{v[1]}x{v[2]} @{v[3]}fps' if v else None
fps_v = float(v[3]) if v else 30.0
r['audio'] = bool(re.search(r'Stream #.*Audio', info))

# ---- integrity ----
dec = ff(['-i', str(film), '-map', '0:v:0', '-f', 'null', '-'])
r['decode_errors'] = len(re.findall(r'(?im)^\[.*?(error|corrupt|invalid).*$', dec))
nframes = re.findall(r'frame=\s*(\d+)', dec)
if v and nframes:   # the picture must last as long as the file: a short video track = frozen/black tail on the phone
    vdur = int(nframes[-1]) / float(v[3])
    r['video_duration'] = round(vdur, 2)
    if dur - vdur > .2:
        fail.append(f'video track ends at {vdur:.2f}s but the file runs {dur:.2f}s — encode lost {dur - vdur:.2f}s of picture')
if r['decode_errors']:
    fail.append(f"{r['decode_errors']} decode errors")
if not v:
    fail.append('no video stream')
elif opt.get('vertical') and (v[1], v[2]) != ('1080', '1920'):
    fail.append(f'vertical deliverable is {v[1]}x{v[2]}, expected 1080x1920')
if 'expect' in opt and abs(dur - float(opt['expect'])) > .25:
    fail.append(f"duration {dur:.2f}s, expected {opt['expect']}s")

# ---- sound ----
if not r['audio']:
    (warn if opt.get('silent-ok') else fail).append('no audio stream')
else:
    loud = ff(['-i', str(film), '-af', 'ebur128=peak=true', '-f', 'null', '-'])   # framelog=verbose prints nothing at the default log level
    num = lambda x: -120.0 if 'inf' in x else float(x)
    r['lufs'] = num(re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', loud)[-1])
    r['true_peak'] = num(re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', loud)[-1])
    if r['lufs'] < -60:
        fail.append('audio track is silent')
    lo, hi = (-16, -12) if profile == 'short' else (-16, -7)
    if not lo <= r['lufs'] <= hi:
        warn.append(f"loudness {r['lufs']} LUFS outside {lo}…{hi} (run audio/master.sh)")
    if r['true_peak'] > -.3:
        fail.append(f"true peak {r['true_peak']} dBTP > −0.3: clips after platform re-encode")
    elif r['true_peak'] > -1:
        warn.append(f"true peak {r['true_peak']} dBTP (aim ≤ −1)")
    st = {}
    for t, s in re.findall(r't:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+|-inf)', loud):   # momentary (400 ms): S's 3 s window hides gaps
        st.setdefault(int(float(t)), []).append(-120.0 if s == '-inf' else float(s))
    curve = {sec: round(max(x), 1) for sec, x in st.items()}
    (out / 'loudness.txt').write_text('\n'.join(f'{sec:4d}s {x:6.1f} LUFS(M max)' for sec, x in sorted(curve.items())) + '\n')
    gaps = [sec for sec, x in sorted(curve.items()) if 2 <= sec <= dur - 3 and x < -45]
    if not curve:
        warn.append('no per-second loudness parsed (ebur128 output format?) — silence check skipped')
    if gaps:
        warn.append(f'near-silent seconds mid-film: {gaps[:12]}')
    ff(['-y', '-i', str(film), '-lavfi', 'showspectrumpic=s=1280x360:legend=1', str(out / 'spectrum.png')])

# ---- picture ----
bd = ff(['-i', str(film), '-vf', 'blackdetect=d=0.12:pix_th=0.04', '-an', '-f', 'null', '-'])
r['black'] = [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bd)]
for a, b in r['black']:
    head, tail = a < .05, a > dur - 2.5   # tail: an end card on black / the closing fade
    if head and b > .6:
        warn.append(f'opens on {b:.2f}s of black — frame 1 is the feed thumbnail')
    if (head and b > 1.5) or (tail and b - a > 1.5) or (not head and not tail and b - a > .4):
        fail.append(f'black {a:.2f}–{b:.2f}s ({b - a:.2f}s)')
fz = ff(['-i', str(film), '-vf', 'freezedetect=n=0.001:d=2.0', '-an', '-f', 'null', '-'])
starts = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', fz)]
ends = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', fz)] + [dur]
r['freeze'] = [(a, round(b, 2)) for a, b in zip(starts, ends)]
for a, b in r['freeze']:
    warn.append(f'picture frozen {a:.2f}–{b:.2f}s (intentional hold? a scrolling viewer leaves)')
stt = ff(['-i', str(film), '-vf', 'fps=4,signalstats,metadata=print', '-an', '-f', 'null', '-'])
Y = [float(x) for x in re.findall(r'signalstats.YAVG=([\d.]+)', stt)]
S = [float(x) for x in re.findall(r'signalstats.SATAVG=([\d.]+)', stt)]
r['luma_per_sec'] = [round(sum(Y[i:i + 4]) / len(Y[i:i + 4]), 1) for i in range(0, len(Y), 4)]
r['sat_per_sec'] = [round(sum(S[i:i + 4]) / len(S[i:i + 4]), 1) for i in range(0, len(S), 4)]
if Y and Y[0] < 16:
    warn.append(f'first frame luma {Y[0]:.0f}/255 — near black thumbnail')
r['luma_jumps'] = [round(i / 4, 2) for i in range(1, len(Y)) if abs(Y[i] - Y[i - 1]) > 45]
if r['luma_jumps']:
    warn.append(f"brightness jumps >45 at {r['luma_jumps'][:10]} — flash on purpose? check the seam strips")
# brightness arc: where is the brightest second? (aesthetics.md §3 — the climax should be the brightest / most contrasted
# moment, around 62–80 % of the film). Reported, not judged: a deliberate dark climax is legitimate.
lps = r['luma_per_sec']
if lps:
    pk = max(range(len(lps)), key=lambda i: lps[i])
    fk = max(range(len(Y)), key=lambda i: Y[i])   # brightest 4 fps sample: a 0.3 s flash vanishes in the per-second mean
    r['luma_peak'] = {'t': pk, 'pct': round(100 * pk / max(1, len(lps)), 1), 'peak': lps[pk], 'median': sorted(lps)[len(lps) // 2],
                      'frame_t': round(fk / 4, 2), 'frame_peak': round(Y[fk], 1)}
# motion per second (mean abs frame difference at 8 fps, 0–255): a "static" second is one where almost nothing moves.
# Douyin knowledge originals measure ~4 mean difference with < 25 % static seconds (xiazhuo123456789/vibe-knowledge-video).
md = ff(['-i', str(film), '-vf', 'fps=8,scale=480:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print', '-an', '-f', 'null', '-'])
M = [float(x) for x in re.findall(r'signalstats.YAVG=([\d.]+)', md)]
if M:
    mps = [sum(M[i:i + 8]) / len(M[i:i + 8]) for i in range(0, len(M), 8)]
    r['motion_per_sec'] = [round(x, 2) for x in mps]
    r['motion_mean'] = round(sum(M) / len(M), 2)
    still = [i for i, x in enumerate(mps) if x < STILL]
    r['static_seconds_pct'] = round(100 * len(still) / len(mps), 1)
    r['motion_median'] = round(sorted(mps)[len(mps) // 2], 2)
    if r['motion_median'] < CALM:
        warn.append(f"motion median {r['motion_median']} — calmer than every Opus reference (calm space film 1.6, character / fly-through 9–16, 挪威 3.5): is anything moving?")
    if r['static_seconds_pct'] > 25:
        warn.append(f"{r['static_seconds_pct']}% of seconds nearly still (motion < {STILL}) at {still[:12]} — keep the picture alive: subject acting, particles, light (not a looping breathe)")
# caption_sync (topic-and-hook.md §3, 许先森: "字幕换了画面不动超过 2 秒，观众一定走"): for each bottom subtitle line,
# motion of the picture above the subtitle band (top 84 %: the line's own fade-in does not count) in the 2 s after its
# onset vs the 1.5 s before. A line passes when the busiest 0.5 s after it clearly beats the time before, or the picture
# is busy anyway. Centre-mode lines put text mid-frame (it would count itself): listed, not judged.
# Calibration 2026-10-27: 光在路上 (slideshow, 46 % still seconds) 9 % · 潮汐锁定 v4 70 % · 蚂蚁不堵车 v13 93 %. A small local
# change right after a big move (潮汐 8.9 s: a label pops in after the zoom) can still warn: look at the strip, then decide.
SYNC_GAIN, SYNC_ADD, SYNC_BUSY = 1.4, .4, 4.0
subs_f = Path(opt['subs']) if 'subs' in opt else film.parent / 'subs.json'
if subs_f.is_file() and not opt.get('vertical') and profile == 'short':
    mc = ff(['-i', str(film), '-vf', 'fps=8,crop=iw:ih*0.84:0:0,scale=480:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print', '-an', '-f', 'null', '-'])
    MC = [float(x) for x in re.findall(r'signalstats.YAVG=([\d.]+)', mc)]
    win = lambda a, b: MC[max(0, int(a * 8)):max(0, int(b * 8))]
    rows, bad = [], []
    for a, b, text, mode in json.loads(subs_f.read_text()):
        if a < .3 or a > dur - 1:   # the opening line is the frame-0 check; a line in the last second has no 2 s
            continue
        pre = win(a - 1.5, a - .1)
        after = [sum(w) / len(w) for k in range(0, 13) if (w := win(a + k / 8, a + k / 8 + .5))]
        if not pre or not after:
            continue
        before, peak = sum(pre) / len(pre), max(after)
        ok = None if mode == 'center' else peak >= max(SYNC_GAIN * before, before + SYNC_ADD) or peak >= SYNC_BUSY
        rows.append({'t': a, 'text': text[:24], 'before': round(before, 2), 'after_peak': round(peak, 2), 'ok': ok})
        if ok is False:
            bad.append(f'{a:.1f}s「{text[:12]}」')
    r['caption_sync'] = rows
    judged = [x for x in rows if x['ok'] is not None]
    r['caption_sync_pct'] = round(100 * sum(x['ok'] for x in judged) / len(judged), 1) if judged else None
    if bad:
        warn.append(f'caption_sync: {len(bad)}/{len(judged)} subtitle lines with no picture change within 2 s: {bad[:8]} — make the picture act out the line (topic-and-hook.md §3)')
elif profile == 'short' and not opt.get('vertical'):
    r['caption_sync'] = None
    warn.append(f'caption_sync not checked: no {subs_f.name} (./vf subs, or --subs=FILE)')
# single-frame anomalies (蚂蚁不堵车 v9: every ~10th frame lost whole layers — ring, paper, leaves — after the GPU wore
# out; luma barely moved on a white-paper film so nothing above caught it): edge density at full frame rate, a frame
# that differs from BOTH neighbours by a lot while the neighbours agree with each other is a glitch, not a cut.
fe = ff(['-i', str(film), '-vf', 'scale=480:-2,edgedetect=low=0.08:high=0.2,signalstats,metadata=print', '-an', '-f', 'null', '-'])
EF = [float(x) for x in re.findall(r'signalstats.YAVG=([\d.]+)', fe)]
# calibrated 2026-10-24: at 0.35 zero hits on 潮汐锁定 / 同步-萤火 / 光在路上 / 蚂蚁 v8, 46 hits on the broken v9;
# 0.15–0.35 also catches milder losses but also designed one-frame flashes (萤火 27.13) → WARN, look at those frames
glitch, soft = [], []
for i in range(1, len(EF) - 1):
    a, b, c = EF[i - 1], EF[i], EF[i + 1]
    ref = max(a, c, .5)
    if abs(a - c) < .15 * ref:
        dev = abs(b - (a + c) / 2) / ref
        (glitch if dev > .35 else soft if dev > .15 else []).append(round(i / fps_v, 3))
r['glitch_frames'], r['glitch_suspects'] = glitch, soft
if soft:
    warn.append(f'{len(soft)} frame(s) unlike both neighbours (milder) at {soft[:12]} — a designed one-frame flash, or lost layers? extract and look')
if glitch:
    fail.append(f'{len(glitch)} single-frame glitches (a frame unlike both neighbours: missing layers / blank) at {glitch[:12]} — delete those frames and re-render with --keep')
# first frame = the feed thumbnail: is it much emptier than the film? (edge density, 1 sample/s)
ed = ff(['-i', str(film), '-vf', 'fps=1,scale=480:-2,edgedetect=low=0.08:high=0.2,signalstats,metadata=print', '-an', '-f', 'null', '-'])
E = [float(x) for x in re.findall(r'signalstats.YAVG=([\d.]+)', ed)]
e0 = re.findall(r'signalstats.YAVG=([\d.]+)', ff(['-i', str(film), '-frames:v', '1', '-vf', 'scale=480:-2,edgedetect=low=0.08:high=0.2,signalstats,metadata=print', '-an', '-f', 'null', '-']))
if len(E) > 3 and e0:
    med, first = sorted(E)[len(E) // 2], float(e0[0])
    r['first_frame_detail'] = [round(first, 2), round(med, 2)]
    if med > 0 and first < .4 * med:
        warn.append(f'first frame has {first:.1f} edge detail vs film median {med:.1f} — frame 1 is the thumbnail: open on a full, readable picture')
sc = ff(['-i', str(film), '-vf', "select='gt(scene,0.32)',showinfo", '-an', '-f', 'null', '-'])
r['scene_cuts'] = [round(float(x), 2) for x in re.findall(r'pts_time:([\d.]+)', sc)]
cpm = len(r['scene_cuts']) / max(dur / 60, .1)
r['cuts_per_min'] = round(cpm, 1)

# ---- what to look at ----
cols = 10 if dur <= 100 else 15
ff(['-y', '-i', str(film), '-vf', f'fps=1,scale=320:-1,tile={cols}x{-(-int(dur) // cols)}', '-frames:v', '1', str(out / 'overview.jpg')])
seams = [float(x) for x in str(opt['seams']).split(',')] if 'seams' in opt else r['scene_cuts']
for i, s in enumerate(seams[:40]):
    ff(['-y', '-ss', f'{max(0, s - .5):.3f}', '-t', '1.0', '-i', str(film), '-vf', 'fps=8,scale=320:-1,tile=8x1', '-frames:v', '1', str(out / f'seam{i:02d}_{s:.2f}.jpg')])

r['verdict'] = 'FAIL' if fail else 'WARN' if warn else 'PASS'
r['options'] = {k: v for k, v in opt.items() if k != 'out'}   # package.py checks the gate was run with the right checks
r['fail'], r['warn'] = fail, warn
r['not_checked'] = ['human listening (an agent cannot hear: say so in the delivery)', 'subjective picture review (review.py + reviewer)']
(out / 'qa.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
print(json.dumps({k: r[k] for k in ('duration', 'video', 'lufs', 'true_peak', 'cuts_per_min', 'motion_median', 'static_seconds_pct', 'caption_sync_pct', 'luma_peak') if k in r}, ensure_ascii=False))
for x in fail:
    print('FAIL ', x)
for x in warn:
    print('WARN ', x)
print(f"QA_{r['verdict']}  {out}/qa.json  (look at overview.jpg, seam*.jpg, spectrum.png)")
sys.exit(1 if fail else 0)
