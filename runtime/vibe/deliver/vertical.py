"""vertical.py <in.mp4> <out.mp4> --style=style.json [--crop=W:H:X:Y] [--y=440] [--title=title.png | --title-text=歌名
                [--sub-text=歌手]] [--ass=lyrics.ass] [--fonts=DIR] [--dim=-0.42] [--lines]

1080×1920 Douyin layout from a 16:9 film. Reading order top→bottom: title → picture → big karaoke lyrics.
  · backdrop: the film itself, shrunk, heavily blurred, darkened, desaturated and averaged over ~0.4 s, so cuts and
    flashes in the film don't flash the whole phone screen and a character never smears into a big orange blob
    (2026-10-24 review of 挪威的森林 v5); a dark gradient behind the title keeps it readable over bright snow;
  · the film (optionally cropped — e.g. cut off the in-film lyric band) at --y (default 440), full width;
  · --title-text: title + artist in the film's style font (style.json from kit/lyrics/style.py), measured glyph
    heights ≈44 / 30 px, a little dimmed, the block at y≥250 — smaller than the ≈60 px lyrics, which stay the first
    read (a big static title stole it twice). --title = a PNG instead;
  · --ass: karaoke lyrics from make_ass.py --style (top-anchored at (540, 1190), rows ≤70 % of the width);
  · a dark gradient over the bottom (y>1120: the lyric zone and Douyin's caption block; an end card's bright blur
    once turned it into a grey fog brighter than the picture): Douyin's caption text sits there and needs a calm dark ground;
  · --lines: 4 px gold rules framing the picture.
Safe zones: Douyin's caption block covers y>1500 and its icon column x>960 from y≈900 down — nothing important there.
For a knowledge short whose picture has detail at the edges, render a vertical-native composition instead.
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
T_SIZE, A_SIZE = (STY['drawtext']['vTitle'], STY['drawtext']['vArtist']) if STY else (51, 34)
T_COL, A_COL = ((STY['colors']['title'], STY['colors']['artist']) if STY else ('#F6E7C8', '#CFE0FF'))
if len(argv) < 2:
    sys.exit(__doc__)
src, dst = argv
crop, y = opt.get('crop'), int(opt.get('y', 440))
cw, ch = (map(int, crop.split(':')[:2]) if crop else (1920, 1080))
fh = round(1080 * ch / cw / 2) * 2
tmp = Path(tempfile.mkdtemp())

chain = ['[0:v]split[a][b]',
         # backdrop: work at quarter size (cheap, and the blur is stronger per pixel), smooth over 9 frames
         f'[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=18:2,'
         f'eq=brightness={opt.get("dim", -0.42)}:saturation=0.65,tmix=frames=9,scale=1080:1920,setsar=1[bg0]',
         # dark gradient behind the title block (top 600 px, opaque → clear)
         "color=c=black:s=1080x600,format=rgba,geq=r=0:g=0:b=0:a='190*pow(1-Y/H\\,1.6)'[grad]",
         "color=c=black:s=1080x800,format=rgba,geq=r=0:g=0:b=0:a='min(235\\,20+330*Y/H)'[gradb]",
         '[bg0][grad]overlay=0:0:shortest=1[bg1]',
         '[bg1][gradb]overlay=0:1120:shortest=1[bg]',
         f'[b]{"crop=" + crop + "," if crop else ""}scale=1080:-2[fg]',
         f'[bg][fg]overlay=0:{y}[v1]']
last = 'v1'
if opt.get('lines'):
    chain.append(f'[v1]drawbox=x=0:y={y - 6}:w=1080:h=4:color=0xE9C886@0.8:t=fill,drawbox=x=0:y={y + fh + 2}:w=1080:h=4:color=0xE9C886@0.8:t=fill[v2]')
    last = 'v2'
inputs = ['-i', src]
if opt.get('title'):
    inputs += ['-loop', '1', '-i', opt['title']]
    chain += ['[1:v]format=rgba[tt]', f'[{last}][tt]overlay=0:70:shortest=1[v3]']
    last = 'v3'
if opt.get('title-text'):   # textfile= sidesteps drawtext's quoting of ' and : in titles
    files = {}
    for key in ('title-text', 'sub-text'):
        txt, missing = fit(str(opt.get(key, '')), FONT)
        if missing:
            sys.exit(f'--{key}: the style font has no glyph for {"".join(sorted(missing))} — reword it')
        files[key] = tmp / f'{key}.txt'
        files[key].write_text(txt, encoding='utf-8')
    dt = f"drawtext=fontfile={FONT}:expansion=none:shadowcolor=black@0.8:shadowx=0:shadowy=4:x=(w-text_w)/2"
    title_y = max(250, y - 190)   # below Douyin's top bar (推荐/关注 tabs and search sit in y<230)
    sub = f",{dt}:textfile={files['sub-text']}:fontsize={A_SIZE}:fontcolor=0x{A_COL.lstrip('#')}@0.9:y={title_y + round(T_SIZE * 1.25)}" if opt.get('sub-text') else ''
    chain.append(f"[{last}]{dt}:textfile={files['title-text']}:fontsize={T_SIZE}:fontcolor=0x{T_COL.lstrip('#')}@0.9:y={title_y}{sub}[vt]")
    last = 'vt'
if opt.get('ass'):
    fonts = f":fontsdir={opt['fonts']}" if opt.get('fonts') else ''
    chain.append(f"[{last}]ass={opt['ass']}{fonts}[v4]")
    last = 'v4'
chain.append(f'[{last}]setsar=1[v]')
cmd = [FF, '-hide_banner', '-loglevel', 'error', '-stats', '-y', *inputs, '-filter_complex', ';'.join(chain),
       '-map', '[v]', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
       '-c:a', 'copy', '-movflags', '+faststart', dst]
r = subprocess.run(cmd)
if r.returncode:
    sys.exit(r.returncode)
print(f'VERTICAL_DONE {dst}  (picture 1080x{fh} at y={y}–{y + fh})')
