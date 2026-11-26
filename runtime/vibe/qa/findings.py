"""findings.py — one reading of a FINDINGS.md table, shared by package.py and gate.py.

Severity has three tiers (2026-10-24, after 蚂蚁不堵车 shipped with 19 known flaws filed as 建议):
  必须  broken / pulls the viewer out (jump, wrong physics, unreadable text, black first frame …)
  应修  a concrete content/readability/continuity defect explaining what the viewer
        would misunderstand or miss (see current references/review.md). Numeric
        framing/style preferences alone do not establish such a defect.
  可选  taste; may ship with a reason
必须 and 应修 block delivery until their 状态 starts with 已修. 「不修＋原因」 is accepted only for 可选; for 应修 only the
user can waive it (状态 = 用户接受：…).
"""
import re
from pathlib import Path

BLOCKING = ('必须', '应修')


def rows(path):
    """[(severity, status, raw line)] for every table row that has a 严重度 column."""
    out, head = [], None
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.startswith('|'):
            head = None
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if any('严重度' in c for c in cells):
            head = cells
            continue
        if head is None or re.match(r'^[\s\-:|]+$', line.replace('|', '')):
            continue
        get = lambda name: next((cells[i] for i, h in enumerate(head) if name in h and i < len(cells)), '')
        out.append((get('严重度'), get('状态') or '待修', line))
    return out


def open_blocking(path):
    """Rows still blocking delivery: severity 必须/应修 and status not 已修 / 用户接受."""
    return [r for r in rows(path) if any(b in r[0] for b in BLOCKING) and not re.match(r'^\s*(已修|用户接受)', r[1])]
