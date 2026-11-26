"""review.py <film.mp4> [--out=DIR] [--fps=6] [--secs=4] [--from=A] [--to=B] [--vertical]

Cuts the film into timecoded motion sheets for the subjective frame-by-frame review (the step that found the 11
defects in 挪威的森林 v5 that every metric had passed). Each sheet = SECS seconds at FPS frames/s, 6 per row.
Writes DIR/sheet_###_A-B.jpg plus DIR/REVIEW_TASK.md — the brief for a fresh reviewer subagent (see
references/review.md). Hand the sheets to reviewers in batches of ≤8 so their context stays clean.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

FF = os.environ.get('FFMPEG') or 'ffmpeg'
KIT = Path(__file__).resolve().parent.parent
argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if not argv:
    sys.exit(__doc__)
film = Path(argv[0]).resolve()
out = Path(opt.get('out') or film.parent / f'review-{film.stem}').resolve()
out.mkdir(parents=True, exist_ok=True)
fps, secs = int(opt.get('fps', 6)), float(opt.get('secs', 4))
info = subprocess.run([FF, '-hide_banner', '-i', str(film)], capture_output=True, text=True).stderr
m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', info)
dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
a0, a1 = float(opt.get('from', 0)), min(dur, float(opt.get('to', dur)))
w = 240 if opt.get('vertical') else 320
FONT = next((f'fontfile={p}:' for p in ('/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial Unicode.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') if Path(p).exists()), '')
n, rows, sheets = int(fps * secs), -(-int(fps * secs) // 6), []
t = a0
while t < a1 - .05:
    b = min(a1, t + secs)
    f = out / f'sheet_{len(sheets):03d}_{t:06.2f}-{b:06.2f}.jpg'
    # burn the film's own clock (pts + the seek offset) so a reviewer can name the exact moment
    vf = (f"fps={fps},scale={w}:-1,drawtext={FONT}text='%{{pts\\:hms\\:{t:.3f}}}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile=6x{rows}")
    r = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t:.3f}', '-t', f'{b - t:.3f}', '-i', str(film),
                        '-vf', vf, '-frames:v', '1', str(f)], capture_output=True, text=True)
    if r.returncode:   # no drawtext in this ffmpeg build: same sheet without the burnt-in clock, file name still carries the span
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t:.3f}', '-t', f'{b - t:.3f}', '-i', str(film),
                        '-vf', f'fps={fps},scale={w}:-1,tile=6x{rows}', '-frames:v', '1', str(f)], check=True)
    sheets.append(f)
    t = b

task = (KIT.parent / 'references/review.md').read_text().split('<!-- REVIEWER BRIEF -->')[1].strip()
(out / 'REVIEW_TASK.md').write_text(task.replace('{FILM}', str(film)).replace('{DIR}', str(out)).replace('{FPS}', str(fps))
                                    .replace('{SECS}', f'{secs:g}') + '\n\nSheets:\n' + '\n'.join(f'- {s}' for s in sheets) + '\n')
print(f'REVIEW_SHEETS {len(sheets)} → {out}  (brief: {out}/REVIEW_TASK.md)')
