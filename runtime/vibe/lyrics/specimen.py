"""specimen.py [out.jpg] [--text=歌词] [--title=歌名] — every lettering preset on one sheet, at its real target size.

Each row: a 1080-wide strip like the vertical layout, title (drawtext) above one karaoke lyric (libass, half sung),
on a dark ground, rendered by the same renderers and the same style.py numbers the films use. Show it to the user
when choosing a style; Read it yourself after adding a font or changing kit/styles/_targets.json.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from style import presets, resolve  # noqa: E402

FF = os.environ.get('FFMPEG') or 'ffmpeg'
argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
out = Path(argv[0] if argv else 'specimen.jpg').resolve()
text, title = opt.get('text', '让我将你心儿摘下'), opt.get('title', '挪威的森林')
tmp = Path(tempfile.mkdtemp())
LABEL = next((p for p in ('/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial Unicode.ttf') if Path(p).exists()), None)
col = lambda h: '&H00' + h[5:7] + h[3:5] + h[1:3]
rows = []
for name in presets():
    st = resolve(name)
    c = st['colors']
    n = len(text)
    ass = tmp / f'{name}.ass'
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 300

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{st['family']},{st['ass']['lyric']},{col(c['fill'])},{col(c['base'])},{col(c['outline'])},&H96000000,0,0,0,0,100,100,6,0,1,{st['stroke']},{st['shadow']},5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,K,,0,0,0,,{{\\an8\\pos(540,150)}}""" + ''.join(f'{{\\k{40 if i < n // 2 else 900}}}{ch}' for i, ch in enumerate(text)) + '\n',
                   encoding='utf-8')
    (tmp / f'{name}.t').write_text(title, encoding='utf-8')
    (tmp / f'{name}.l').write_text(f"{name}  ·  {st['family']}", encoding='utf-8')
    label = f",drawtext=fontfile={LABEL}:textfile={tmp / f'{name}.l'}:fontsize=22:fontcolor=0x9AA3B5:x=24:y=16" if LABEL else ''
    png = tmp / f'{name}.png'
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=0x1B1E2B:s=1080x300:d=1', '-ss', '0.8',
                    '-vf', f"drawtext=fontfile={st['file']}:textfile={tmp / f'{name}.t'}:fontsize={st['drawtext']['vTitle']}"
                           f":fontcolor=0x{c['title'][1:]}:x=(w-text_w)/2:y=56{label},ass={ass}:fontsdir={Path(st['file']).parent}",
                    '-frames:v', '1', str(png)], check=True)
    rows.append(png)
inputs = sum((['-i', str(p)] for p in rows), [])
subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', *inputs, '-filter_complex', f'vstack=inputs={len(rows)}', str(out)], check=True)
print(f'SPECIMEN_DONE {out}  ({len(rows)} presets; lyric ≈ target glyph height, half sung)')
