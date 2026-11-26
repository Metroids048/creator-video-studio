"""gate.py <film_dir> [--stage=plan|build|ship] — check plan/media/review records.

Plan completeness, source records, current QA and unresolved 必须/应修 remain blocking.
Shot sizes, static-camera share, repeated effects/transitions and long framings are
WARN diagnostics only: their suitability requires content review, not numeric rules.
GATE_PASS confirms these records, never viewer approval or distribution quality.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from findings import open_blocking  # noqa: E402

argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if not argv:
    sys.exit(__doc__)
root = Path(argv[0]).resolve()
stage = opt.get('stage', 'plan')
kind = 'knowledge-short' if (root / 'film').is_dir() else 'lyric-mv'
results = []


def check(name, ok, why=''):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + why}")


def table(md, header_hint):
    """First markdown table whose header contains header_hint → (header cells, data rows as cell lists)."""
    lines = md.splitlines()
    for i, l in enumerate(lines):
        if l.startswith('|') and header_hint in l and i + 1 < len(lines) and re.match(r'^\|[\s\-|:]+\|$', lines[i + 1]):
            cells = lambda r: [c.strip() for c in r.strip().strip('|').split('|')]
            out = []
            for r in lines[i + 2:]:
                if not r.startswith('|'):
                    break
                out.append(cells(r))
            return cells(l), out
    return [], []


def col(head, rows, *names):
    """Values of the first column whose header contains any of names ('' where missing)."""
    j = next((k for k, h in enumerate(head) if any(n in h for n in names)), None)
    return [] if j is None else [r[j] if j < len(r) else '' for r in rows]


BLANK = ('', '…', '-', '例：')
TEMPLATE = Path(__file__).resolve().parent.parent / 'templates' / kind


def unfilled(cell, tmpl_cell):
    return cell in BLANK or cell.startswith('例：') or (tmpl_cell is not None and cell == tmpl_cell)


def warn(name, issue):
    if issue:
        print(f"WARN  {name}  — {issue}; inspect information/action changes in context")


def shot_grammar(label, sizes, moves, fxs=None, outs=None):
    """Locate possible repetition; these proxies never establish a content defect."""
    norm = lambda v: re.sub(r'[\s（）()，,。]', '', v)[:4]
    run3 = lambda vs: next((f'{vs[i]}×3 at rows {i + 1}-{i + 3}' for i in range(len(vs) - 2) if vs[i] and norm(vs[i]) == norm(vs[i + 1]) == norm(vs[i + 2])), '')
    if sizes:
        r = run3(sizes)
        warn(f'{label}: repeated shot size', r)
    if moves:
        static = sum(1 for m in moves if re.search(r'固定|静止|不动|static', m))
        warn(f'{label}: static-camera share', f'{static}/{len(moves)} static' if static > .4 * len(moves) else '')
    if fxs:
        rep = next((f'"{fxs[i]}" rows {i + 1}-{i + 2}' for i in range(len(fxs) - 1) if fxs[i] and fxs[i] not in BLANK and norm(fxs[i]) == norm(fxs[i + 1])), '')
        warn(f'{label}: repeated effect', rep)
    if outs:
        r = run3(outs)
        warn(f'{label}: repeated transition', r)


# ---- plan ----
st = (root / 'FILM_STATUS.md').read_text(encoding='utf-8') if (root / 'FILM_STATUS.md').exists() else ''
ref_line = next((l for l in st.splitlines() if '0 参考' in l), '')
check('refs looked at (FILM_STATUS 0)', ref_line.startswith('- [x]') or '无' in ref_line.split('：')[-1][:6],
      'download and READ the references (kit/ref/acquire.sh, or the standing library evidence/refs-opus55-all-*), then tick line 0')
brief = (root / 'BRIEF.md').read_text(encoding='utf-8') if (root / 'BRIEF.md').exists() else ''
tmpl = (TEMPLATE / 'BRIEF.md').read_text(encoding='utf-8') if (TEMPLATE / 'BRIEF.md').exists() else ''
_, b = table(brief, '项')
tb = {r[0]: (r[1] if len(r) > 1 else '') for r in table(tmpl, '项')[1]}
empty = [re.sub(r'\*', '', r[0])[:16] for r in b if len(r) >= 2 and unfilled(r[1], tb.get(r[0]))]
check('BRIEF.md filled (no template text / 例： left)', bool(b) and not empty, f'unfilled: {", ".join(empty[:6])}' if b else 'no BRIEF table')
check('taste profile present (品味档案)', '品味档案' in brief, 'BRIEF is from an old template: add the 品味档案 rows from kit/templates/*/BRIEF.md')
check('lettering style chosen (style.json)', (root / 'style.json').exists(), 'run ./vf style <preset> (./vf specimen to compare)')
if kind == 'lyric-mv':
    sb = (root / 'STORYBOARD.md').read_text(encoding='utf-8') if (root / 'STORYBOARD.md').exists() else ''
    head, shots = table(sb, 'Clip time')
    holes = [f"{r[0]}:{head[i] if i < len(head) else i}" for r in shots for i, c in enumerate(r) if c in BLANK]
    check('STORYBOARD: shots listed', len(shots) >= 3, f'{len(shots)} shot rows')
    check('STORYBOARD: every column filled in every shot', bool(shots) and not holes, f'empty cells {holes[:8]}')
    acts = ' '.join(col(head, shots, '主动作'))
    check('STORYBOARD: action intentions recorded (not verified)', bool(acts.strip()), 'record the visible action/reaction and its change')
    shot_grammar('STORYBOARD', col(head, shots, '景别'), col(head, shots, '镜头运动'), col(head, shots, '特效'), col(head, shots, 'In'))
    if not col(head, shots, '景别'):
        check('STORYBOARD has a 景别 column', False, 'old template: add the 景别 column (kit/templates/lyric-mv/STORYBOARD.md)')
else:
    head, ch = table(brief, '时间')
    holes = [f"{r[0]}:{head[i] if i < len(head) else i}" for r in ch for i, c in enumerate(r) if c in BLANK]
    check('BRIEF chapter table: ≥3 chapters, every cell filled', len(ch) >= 3 and not holes, f'{len(ch)} chapters, empty {holes[:8]}')
    shot_grammar('chapters', col(head, ch, '景别'), col(head, ch, '镜头运动'), None, col(head, ch, '转场'))
    # Long framings locate intervals to inspect; a quiet/continuous demonstration may be valid.
    long = []
    for r, mv in zip(ch, col(head, ch, '镜头运动') or [''] * len(ch)):
        m = re.match(r'^\s*([\d.]+)\s*[–\-~]\s*([\d.]+)', r[1] if len(r) > 1 else '')
        if m:
            span = float(m.group(2)) - float(m.group(1))
            if span > 6.5 and mv.count('→') + 1 < -(-span // 6):
                long.append(f"{r[0]}: {span:.0f}s, {mv.count('→') + 1} framing(s)")
    warn('chapters: long framing', '; '.join(long[:4]))
    src = (root / 'SOURCES.md').read_text(encoding='utf-8') if (root / 'SOURCES.md').exists() else ''
    links = len(set(re.findall(r'https?://[^\s|)>]+', src)))
    check('SOURCES.md: ≥5 sourced facts (links; aim for 8–10)', links >= 5, f'{links} links — research first, delete facts with no reliable source')

# ---- build ----
if stage in ('build', 'ship'):
    mp4s = sorted((root / 'out').glob('*.mp4'), key=lambda p: p.stat().st_mtime) if (root / 'out').exists() else []
    named = root / 'out' / str(opt['lead']) if 'lead' in opt else None   # --lead=<file in out/>; default: the newest film
    lead = named if named and named.exists() else next((p for p in reversed(mp4s) if 'vsrc' not in p.stem), None)
    check('lead film rendered', lead is not None, 'no mp4 in out/')
    if lead:
        q = lead.parent / f'qa-{lead.stem}' / 'qa.json'
        qa = json.loads(q.read_text()) if q.exists() else None
        check(f'QA of {lead.name} exists and is current', bool(qa) and qa['sha256'] == hashlib.sha256(lead.read_bytes()).hexdigest(), f'./vf qa out/{lead.name}')
        check(f'QA verdict not FAIL', bool(qa) and qa['verdict'] != 'FAIL', '; '.join(qa['fail']) if qa else '')
        if stage == 'ship':
            f = lead.parent / f'review-{lead.stem}' / 'FINDINGS.md'
            fs = list((root / 'out').glob('review-*/FINDINGS.md'))
            ok = f.exists() or bool(fs)
            check('frame-by-frame review done (FINDINGS.md)', ok, './vf review; read the sheets and record concrete timecoded findings')
            open_rows = [r for p in ([f] if f.exists() else fs) for r in open_blocking(p)]
            check('no 必须 / 应修 left unfixed (不修 only for 可选)', ok and not open_rows, f'{len(open_rows)} open, e.g. {open_rows[0][2][:80]}' if open_rows else '')

print(f"GATE_{'PASS' if all(results) else 'FAIL'}  {stage}  ({sum(results)}/{len(results)})")
sys.exit(0 if all(results) else 1)
