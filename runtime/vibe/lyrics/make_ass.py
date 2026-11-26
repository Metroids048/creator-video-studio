"""make_ass.py <lyrics.js|karaoke.js> <out.ass> <clip_seconds> --style=style.json [--until=S] [--pos=540,1190]
                [--breaks=lyric-breaks.txt] [--res=1080x1920]   (overrides: --font= --size= --maxw= --fill= --base= --outline=)

Karaoke lyrics for the vertical (1080×1920) layout: every character sweeps base→fill over the line's sung time
(opts.sing), the same timing the in-film karaoke uses.
Lettering comes from the film's style (style.json, written by kit/lyrics/style.py): font, measured size, colours,
outline. The size is set by GLYPH HEIGHT (≈60 px since the user's 2026-10-24 "字幕太大了"), converted with the font's
measured libass metrics — never guess from the font size (fonts differ by 30 %). Rows are ≤70 % of the screen width
(756 px), centred on x=540 like the title, so the right edge stays clear of Douyin's icon column (x>960); a longer
forced row is scaled down to fit. The block hangs from a fixed top (\an8 at y=1190) so the first row never jumps.
Long lines wrap at a word-ish boundary (after 的/你…, before 未/不/是…). The heuristic cannot parse meaning
("心中是否有 / 我未曾到过的地方啊"), so a breaks file wins: lyric-breaks.txt next to the lyrics source (or --breaks=), one
lyric per line with "/" at the break. Don't put "/" in LY itself — the in-film karaoke would draw it.
Timing: the first line is already on screen at frame 0 (the thumbnail carries a lyric; the fill waits for the singer);
lines that butt switch words with no fade (fading out then in left 2–5 empty frames); --until=S ends the lyrics
before an end card so the screen has one read.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python -I leaves the script dir off sys.path
from glyphs import fit  # noqa: E402

argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if len(argv) < 3:
    sys.exit(__doc__)
src, out, dur = Path(argv[0]).read_text(encoding='utf-8'), argv[1], float(argv[2])
m = re.search(r'const\s+LY\s*=\s*\[(.*?)\n\];', src, re.S)
if not m:
    sys.exit('no `const LY = [ … ];` block found')
row_re = re.compile(r"""\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')\s*(?:,\s*(\{[^}]*\}))?\s*\]""")
rows = []
for a, b, q, o in row_re.findall(m[1]):
    txt = json.loads(q) if q[0] == '"' else q[1:-1].replace("\\'", "'")
    s = re.search(r'sing:\s*([\d.]+)', o or '')
    rows.append((a, b, txt, s[1] if s else str(min((float(b) - float(a)) * .85, len(txt) * .3))))
expected = len(re.findall(r'^\s*\[', m[1], re.M))
if len(rows) != expected:
    sys.exit(f'parsed {len(rows)} of {expected} LY rows — fix the odd row (format: [a, b, "text", {{ sing: s }}])')
rx, ry = opt.get('res', '1080x1920').split('x')
px, py = opt.get('pos', '540,1190').split(',')
STY = json.loads(Path(opt['style']).read_text(encoding='utf-8')) if opt.get('style') else None
if not STY:
    print('WARN no --style: falling back to Ma Shan Zheng at the measured 60 px glyph height', file=sys.stderr)
    STY = {'family': 'Ma Shan Zheng', 'file': str(Path(__file__).resolve().parent.parent / 'fonts/MaShanZheng-Regular.ttf'),
           'ass': {'lyric': 94, 'adv': 71.0, 'maxw': 756}, 'stroke': 5, 'shadow': 3,
           'colors': {'base': '#F6EEE2', 'fill': '#F4B63A', 'outline': '#121A30'}}


def ass_col(hexrgb):   # '#RRGGBB' → ASS &H00BBGGRR
    h = hexrgb.lstrip('#')
    return f'&H00{h[4:6]}{h[2:4]}{h[0:2]}'.upper()


font = opt.get('font', STY['family'])
size = int(opt.get('size', STY['ass']['lyric']))
maxw = int(opt.get('maxw', STY['ass']['maxw']))
adv = STY['ass']['adv'] * size / STY['ass']['lyric']   # measured advance per character for this font
per_row = max(2, int(maxw / adv))
bf = Path(opt['breaks']) if opt.get('breaks') else Path(argv[0]).with_name('lyric-breaks.txt')
FORCED = {l.strip().replace('/', ''): l.strip() for l in bf.read_text(encoding='utf-8').splitlines() if '/' in l} if bf.exists() else {}
until = min(dur, float(opt.get('until', dur)))
END_OK = set('你他她它的了着是在中里上下地得吗呢啊吧心时处候们去来过说')   # good last char of a row
START_OK = set('未不是在那这为何让看从总还也都就只可能会把被和与像')  # good first char of a row (no pronouns: 为我/爱我 stay together)


def breaks(txt):
    """Row breaks for txt: explicit '/' wins; else per row ≤ per_row chars, cut near the middle at a word-ish boundary."""
    txt = FORCED.get(txt, txt)
    if '/' in txt:
        parts = txt.split('/')
        return ''.join(parts), {sum(len(p) for p in parts[:i]) for i in range(1, len(parts))}
    n = len(txt)
    rows_n = -(-n // per_row)
    cuts = set()
    for k in range(1, rows_n):
        ideal = n * k / rows_n
        cand = [c for c in range(max(1, int(ideal) - 2), min(n - 1, int(ideal) + 2) + 1)
                if c - (max(cuts) if cuts else 0) <= per_row and n - c <= per_row * (rows_n - k)]
        score = lambda c: abs(c - ideal) - 1.5 * (txt[c - 1] in END_OK) - 1.5 * (txt[c] in START_OK)
        cuts.add(min(cand, key=score) if cand else round(ideal))
    return txt, cuts


def ts(x):
    x = max(0.0, x)
    return f'{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}'


head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {rx}
PlayResY: {ry}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{font},{size},{opt.get('fill', ass_col(STY['colors']['fill']))},{opt.get('base', ass_col(STY['colors']['base']))},{opt.get('outline', ass_col(STY['colors']['outline']))},&H96000000,0,0,0,0,100,100,6,0,1,{STY['stroke']},{STY['shadow']},5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
shown = sorted((float(a), float(b), t, float(s)) for a, b, t, s in rows if float(a) < until - .3)
lines, gaps = [], set()
for k, (a, b, txt, sing) in enumerate(shown):
    if 'font' not in opt:   # glyph check against the style's own font file
        txt, missing = fit(txt, STY['file'])
        gaps |= missing
    txt, cuts = breaks(txt)
    nxt = shown[k + 1][0] if k + 1 < len(shown) else None
    joined_next = nxt is None or nxt - b < 1.0           # bridge short gaps; hold the last line to the end (or --until)
    end = (nxt - .05) if nxt is not None and joined_next else (until if nxt is None else b)   # = next line's start: no overlap
    end = min(end, until)
    joined_prev = k > 0 and shown[k - 1][1] + 1.0 > a
    start = 0.0 if k == 0 and a < 6 else a - .05         # first line pre-shown from frame 0
    lead = max(0, round((a - start) * 100))              # unsung pause before the fill starts
    per = max(1, round(sing * 100 / max(1, len(txt))))
    edges = [0, *sorted(cuts), len(txt)]
    widest = max(edges[i + 1] - edges[i] for i in range(len(edges) - 1))
    fit_scale = min(100, int(100 * maxw / (widest * adv)))   # a forced long row shrinks instead of reaching the icons
    fill = (f'{{\\fscx{fit_scale}\\fscy{fit_scale}}}' if fit_scale < 100 else '') + (f'{{\\k{lead}}}' if lead else '') + ''.join(('\\N' if i in cuts else '') + f'{{\\kf{per}}}{c}' for i, c in enumerate(txt))
    fin = 0 if joined_prev or start == 0 else 120
    fout = 0 if (joined_next and nxt is not None) else 160
    lines.append(f'Dialogue: 0,{ts(start)},{ts(end)},K,,0,0,0,,{{\\an8\\pos({px},{py})\\fad({fin},{fout})}}{fill}')
Path(out).write_text(head + '\n'.join(lines) + '\n', encoding='utf-8')
if gaps:   # libass falls back to another font for these: a visibly different glyph mid-line
    print(f'WARN {font} lacks {"".join(sorted(gaps))} — those characters render in a fallback font')
print(f'ASS_DONE {len(lines)} lines → {out}')
