"""package.py <film_dir> --main=<mp4>[,<label>] [--also=<mp4>[,<label>];…] [--cover=<img>] [--listened="谁/何时听过"]
                  [--review=<FINDINGS.md>] [--skip-review="why"] [--note="审片范围/WARN 的人工判断"]

Builds <film_dir>/发布包/ from FINAL files only:
  · every mp4 must have <its dir>/qa-<stem>/qa.json whose sha256 matches the file and verdict ≠ FAIL
    (re-encoded after QA? → QA again; that is the point);
  · the lead file needs a frame-by-frame review: --review=<FINDINGS.md> (default <its dir>/review-<stem>/FINDINGS.md)
    with no 必须 or 应修 row whose 状态 isn't 已修 (qa/findings.py); --skip-review="why" is the only way round it and
    is written into MANIFEST;
  · an existing 发布包/ is moved to out/_superseded/发布包-<time>/ — never mixed with the new version;
  · writes MANIFEST.md (what each file is, specs, loudness, QA verdict and warnings, review findings status,
    honest listening status) and copies 发布方案.md from the film dir (template from the kit if missing).
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'qa'))
from findings import open_blocking  # noqa: E402
argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if not argv or 'main' not in opt:
    sys.exit(__doc__)
root = Path(argv[0]).resolve()
items = [('主推', opt['main'])] + [('附', x) for x in str(opt.get('also', '')).split(';') if x]
rows, problems = [], []
for role, spec in items:
    path, _, label = spec.partition(',')
    f = (root / path).resolve() if not Path(path).is_absolute() else Path(path)
    qa = f.parent / f'qa-{f.stem}' / 'qa.json'
    if not f.exists():
        problems.append(f'{f}: missing')
        continue
    if not qa.exists():
        problems.append(f'{f.name}: no QA — run ./vf qa {path}')
        continue
    q = json.loads(qa.read_text())
    if q['sha256'] != hashlib.sha256(f.read_bytes()).hexdigest():
        problems.append(f'{f.name}: QA is for an older file — run ./vf qa {path} again')
        continue
    o = q.get('options', {})
    if 'vertical' in f.stem and not o.get('vertical'):
        problems.append(f'{f.name}: QA ran without --vertical — run ./vf qa {path} --vertical')
        continue
    if o.get('silent-ok'):
        problems.append(f'{f.name}: QA ran with --silent-ok — a release needs sound')
        continue
    if q['verdict'] == 'FAIL':
        problems.append(f"{f.name}: QA FAIL — {'; '.join(q['fail'])}")
        continue
    review = f.parent / f'review-{f.stem}' / 'FINDINGS.md'
    rows.append((role, f, label or f.stem, q, review))
lead_review = None
if rows and not opt.get('skip-review'):
    f0 = rows[0][1]
    lead_review = Path(opt['review']) if opt.get('review') else f0.parent / f'review-{f0.stem}' / 'FINDINGS.md'
    if not lead_review.is_absolute():
        lead_review = root / lead_review
    if not lead_review.exists():
        problems.append(f'{f0.name}: no frame-by-frame review ({lead_review}) — ./vf review, reviewer subagents, FINDINGS.md')
    else:
        open_rows = open_blocking(lead_review)
        if open_rows:
            problems.append(f'{lead_review.name}: {len(open_rows)} 必须/应修 row(s) not 已修 (不修 is only for 可选), e.g. {open_rows[0][2][:90]}')
if problems:
    print('PACKAGE_REFUSED')
    print('\n'.join('  ' + p for p in problems))
    sys.exit(1)

cover = None
if opt.get('cover'):
    cover = Path(opt['cover']) if Path(opt['cover']).is_absolute() else root / opt['cover']
    if not cover.exists():
        sys.exit(f'PACKAGE_REFUSED\n  cover not found: {cover}')
dst = root / '发布包'
if dst.exists() and any(dst.iterdir()):
    old = root / 'out/_superseded' / f'发布包-{time.strftime("%Y%m%d-%H%M%S")}'
    old.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dst), str(old))
    print(f'previous 发布包 → {old}')
dst.mkdir(parents=True, exist_ok=True)
lines = [f'# 发布包 · {root.name}', '', f'生成时间：{time.strftime("%Y-%m-%d %H:%M")}', '',
         '| 文件 | 规格 | 响度 | QA | 主观逐帧审 |', '|---|---|---|---|---|']
for k, (role, f, label, q, review) in enumerate(rows, 1):
    name = f'{k}-{role}-{label}{f.suffix}'
    shutil.copy2(f, dst / name)
    rev = ('已审：' + str(lead_review) if role == '主推' and lead_review else '已审，见 FINDINGS' if review.exists()
           else f"跳过：{opt['skip-review']}" if role == '主推' and opt.get('skip-review') else '**未做**')
    lines.append(f"| {name} | {q['video']} · {q['duration']}s | {q.get('lufs', '—')} LUFS / {q.get('true_peak', '—')} dBTP | {q['verdict']} | {rev} |")
lines += ['', '## QA 警告（需人判断是否有意为之）']
for role, f, label, q, review in rows:
    for w in q['warn']:
        lines.append(f'- {label}：{w}')
if opt.get('note'):
    lines += ['', '## 说明', str(opt['note'])]
lines += ['', '## 未验证', f"- 人耳听审：{opt.get('listened') or '未进行（Agent 听不到声音；频谱与响度只是代理指标）'}",
          '- 平台实测：未发布，流量表现未知']
if cover:
    shutil.copy2(cover, dst / ('封面' + cover.suffix))
    lines.insert(4, f'封面：封面{cover.suffix}')
plan = root / '发布方案.md'
if not plan.exists():
    shutil.copy2(KIT / 'templates/发布方案.md', plan)
    print('发布方案.md copied from the template — fill it in')
shutil.copy2(plan, dst / '发布方案.md')
(dst / 'MANIFEST.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'PACKAGE_DONE {dst}  ({len(rows)} films)')
