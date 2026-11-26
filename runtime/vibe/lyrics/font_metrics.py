"""font_metrics.py [font.ttf …] — measure how big a font REALLY draws, so sizes are set by glyph height, not font size.

For each font (default: every .ttf in kit/fonts) renders the same CJK sample with libass (vertical ASS lyrics) and with
ffmpeg drawtext (titles, covers; ≈ browser canvas px), measures the ink bbox with PIL and prints / writes:
  family      the name to put in ASS / CSS (from the font's name table)
  assH, assAdv  libass glyph height and per-character advance as a fraction of the ASS font size (+6 px style spacing)
  pxH         drawtext/canvas glyph height as a fraction of the px size
Ma Shan Zheng measured 0.64 / 0.68 / 0.88 on 2026-10-24: guessing from the font size made the "big" title bigger than
the lyrics twice. Results go to kit/styles/_metrics.json; styles/*.json read them (see kit/styles/README.md).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image

KIT = Path(__file__).resolve().parent.parent
FF = os.environ.get('FFMPEG') or 'ffmpeg'
SAMPLE = '国风雪夜心'          # five full-height CJK glyphs, no ascender/descender tricks
fonts = [Path(a) for a in sys.argv[1:]] or sorted((KIT / 'fonts').glob('*.ttf'))


def family(f):
    names = TTFont(str(f), fontNumber=0)['name']
    return names.getDebugName(1) or f.stem


def bbox(png):
    im = Image.open(png).convert('L').point(lambda v: 255 if v > 60 else 0)
    return im.getbbox()


out = {}
tmp = Path(tempfile.mkdtemp())
for f in fonts:
    fam = family(f)
    ass = tmp / 'm.ass'
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{fam},100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,6,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.00,K,,0,0,0,,{{\\an5\\pos(540,960)}}{SAMPLE}
""", encoding='utf-8')
    a_png, d_png = tmp / 'a.png', tmp / 'd.png'
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=1080x1920',
                    '-vf', f'ass={ass}:fontsdir={f.parent}', '-frames:v', '1', str(a_png)], check=True)
    (tmp / 's.txt').write_text(SAMPLE, encoding='utf-8')
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=1080x400',
                    '-vf', f"drawtext=fontfile={f}:textfile={tmp / 's.txt'}:fontsize=100:x=40:y=100:fontcolor=white",
                    '-frames:v', '1', str(d_png)], check=True)
    ab, db = bbox(a_png), bbox(d_png)
    if not ab or not db:
        print(f'{f.name}: nothing rendered — is "{fam}" the family libass sees?')
        continue
    n = len(SAMPLE)
    out[f.name] = {'family': fam, 'assH': round((ab[3] - ab[1]) / 100, 3),
                   'assAdv': round((ab[2] - ab[0] - 6 * (n - 1)) / n / 100, 3), 'pxH': round((db[3] - db[1]) / 100, 3)}
    print(f"{f.name:34s} {fam:24s} assH {out[f.name]['assH']:.2f}  assAdv {out[f.name]['assAdv']:.2f}  pxH {out[f.name]['pxH']:.2f}")

dst = KIT / 'styles/_metrics.json'
dst.parent.mkdir(exist_ok=True)
old = json.loads(dst.read_text()) if dst.exists() else {}
old.update(out)
dst.write_text(json.dumps(old, ensure_ascii=False, indent=1))
print(f'METRICS_DONE {len(out)} fonts → {dst}')
