"""cover.py <film.mp4> <out.png> --style=style.json --t=SECONDS --title=片名 [--sub=歌手/副标题] [--tagline=一句钩子]
               [--tagline2=小字] [--crop=W:H:X:Y] [--y=500]

3:4 cover (1080×1440) for 抖音 / 小红书, the 挪威的森林 v4 layout. Use the clean picture: for a lyric MV pass the
vertical source (*-vsrc.mp4, no in-film title) with --crop=1600:966:160:0 so the in-film lyric band is cut off.
Layout: the frame at --t blurred as the backdrop; the frame
itself as a band framed by thin gold rules; big brush-font title + subtitle on top; a gold hook line and a small line
under the picture. Pick --t from the review sheets: the signature moment, characters large, faces readable.
Text is drawn from files (no quoting problems) in the film's style font at measured glyph heights (style.json).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lyrics'))
from glyphs import fit  # noqa: E402

FF = os.environ.get('FFMPEG') or 'ffmpeg'
argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
STY = json.loads(Path(opt['style']).read_text(encoding='utf-8')) if opt.get('style') else None
FONT = STY['file'] if STY else Path(__file__).resolve().parent.parent / 'fonts/MaShanZheng-Regular.ttf'
SZ = STY['drawtext'] if STY else {'cover_title': 138, 'cover_sub': 46, 'cover_tagline': 60, 'cover_tagline2': 32}
COL = STY['colors'] if STY else {'title': '#F6E7C8', 'artist': '#CFE0FF', 'fill': '#F4B63A', 'base': '#E2E8F0'}
hx = lambda c: '0x' + c.lstrip('#')
if len(argv) < 2 or 't' not in opt or 'title' not in opt:
    sys.exit(__doc__)
src, dst = argv
y = int(opt.get('y', 500))
tmp = Path(tempfile.mkdtemp())
crop = f"crop={opt['crop']}," if opt.get('crop') else ''
band_h = 608 if not opt.get('crop') else round(1080 * int(opt['crop'].split(':')[1]) / int(opt['crop'].split(':')[0]) / 2) * 2


def text(key, size, color, ty, shadow=6):
    if not opt.get(key):
        return ''
    txt, missing = fit(str(opt[key]), FONT)
    if missing:
        sys.exit(f'--{key}: the style font has no glyph for {"".join(sorted(missing))} — reword it')
    (tmp / f'{key}.txt').write_text(txt, encoding='utf-8')
    return (f",drawtext=fontfile={FONT}:expansion=none:textfile={tmp / f'{key}.txt'}:fontsize={size}:fontcolor={color}"
            f":shadowcolor=black@0.75:shadowx=0:shadowy={shadow}:x=(w-text_w)/2:y={ty}")


below = y + band_h
graph = (f"[0:v]split[a][b];"
         f"[a]scale=-2:1440,crop=1080:1440,boxblur=40:3,eq=brightness=-0.28:saturation=1.1[bg];"
         f"[b]{crop}scale=1080:-2[fg];"
         f"[bg][fg]overlay=0:{y},"
         f"drawbox=x=0:y={y - 5}:w=1080:h=3:color=0xE9C886@0.7:t=fill,drawbox=x=0:y={below + 2}:w=1080:h=3:color=0xE9C886@0.7:t=fill"
         + text('title', SZ['cover_title'], hx(COL['title']), 120, 8) + text('sub', SZ['cover_sub'], hx(COL['artist']), 120 + round(SZ['cover_title'] * 1.3))
         + text('tagline', SZ['cover_tagline'], hx(COL['fill']), below + 60) + text('tagline2', SZ['cover_tagline2'], hx(COL['base']), below + 60 + round(SZ['cover_tagline'] * 1.6), 4)
         + '[v]')
r = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(opt['t']), '-i', src, '-frames:v', '1',
                    '-filter_complex', graph, '-map', '[v]', dst])
if r.returncode:
    sys.exit(r.returncode)
print(f'COVER_DONE {dst}  (frame {opt["t"]}s, 1080x1440) — Read it before packaging')
