"""compare.py <our.mp4> <ref.mp4|ref-id> [more refs…] [--n=6] [--out=out/check/compare.jpg]

Side by side with the references — the user's bar is "能和抖音爆款并排比". Samples n frames at the same relative
positions (5 %, 20 %, … 95 %) of our film and of each reference, scales them to one height, and stacks one row per
film: ours on top. A ref-id is looked up in the standing library evidence/refs-opus55-all-*/douyin-<id>.mp4.
Read the sheet and ask, row by row: is ours as full, as lit, as composed, is the type as small and as good?
"""
import os
import subprocess
import sys
from pathlib import Path

argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if len(argv) < 2:
    sys.exit(__doc__)
FF = os.environ.get('FFMPEG', 'ffmpeg')
FP = str(Path(FF).with_name('ffprobe')) if Path(FF).with_name('ffprobe').exists() else 'ffprobe'
FONT = next(iter(sorted((Path(__file__).resolve().parent.parent / 'fonts').glob('LXGWWenKai*.ttf'))), None)
PROJECT = Path(os.environ.get('VF_PROJECT_ROOT', Path(__file__).resolve().parents[4]))


def resolve(x):
    p = Path(x)
    if p.exists():
        return p
    hits = sorted(PROJECT.glob(f'evidence/refs-*/douyin-{x}.mp4'))
    if not hits:
        sys.exit(f'reference not found: {x} (path or id in evidence/refs-*/)')
    return hits[-1]


def dur(p):
    return float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)], capture_output=True, text=True).stdout.strip() or 0)


n = int(opt.get('n', 6))
H = 300
films = [resolve(argv[0])] + [resolve(x) for x in argv[1:]]
out = Path(opt.get('out', 'out/check/compare.jpg'))
out.parent.mkdir(parents=True, exist_ok=True)
rows = []
tmp = out.parent / '_cmp'
tmp.mkdir(exist_ok=True)
for k, f in enumerate(films):
    d = dur(f)
    tiles = []
    for i in range(n):
        t = d * (.05 + .9 * i / max(1, n - 1))
        o = tmp / f'{k}_{i}.png'
        subprocess.run([FF, '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', str(f), '-frames:v', '1', '-vf', f'scale=-2:{H},pad=ceil(iw/2)*2:{H}', str(o)], check=True)
        tiles.append(o)
    row = tmp / f'row{k}.png'
    label = ('OURS  ' if k == 0 else 'REF  ') + f.stem[-24:]
    inputs = sum([['-i', str(x)] for x in tiles], [])
    subprocess.run([FF, '-v', 'error', '-y', *inputs, '-filter_complex',
                    ''.join(f'[{i}:v]' for i in range(n)) + f'hstack=inputs={n},drawbox=x=0:y=0:w=330:h=34:color=black@0.7:t=fill,'
                    f"drawtext=fontfile='{FONT}':text='{label}':x=8:y=8:fontsize=20:fontcolor=white", str(row)], check=True)
    rows.append(row)
# rows can differ in width (16:9 vs 9:16): pad every row to the widest before stacking
widths = [int(subprocess.run([FP, '-v', 'error', '-show_entries', 'stream=width', '-of', 'csv=p=0', str(r)], capture_output=True, text=True).stdout.strip()) for r in rows]
W = max(widths)
inputs = sum([['-i', str(r)] for r in rows], [])
pads = ''.join(f'[{i}:v]pad={W}:{H}:0:0:color=#202020[p{i}];' for i in range(len(rows)))
subprocess.run([FF, '-v', 'error', '-y', *inputs, '-filter_complex', pads + ''.join(f'[p{i}]' for i in range(len(rows))) + f'vstack=inputs={len(rows)}', '-q:v', '3', str(out)], check=True)
for x in tmp.iterdir():
    x.unlink()
tmp.rmdir()
print(f'COMPARE {out}  ({len(films)} rows × {n})')
