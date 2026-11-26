"""glyphs.py — make sure text can actually be drawn in a font before it is burnt into a video.

Ma Shan Zheng (the brush font) has ~7000 glyphs: '·', '・' and rarer hanzi are missing and render as tofu boxes (the
first cover draft showed 一颗冻住的心 □ 一盏灯). fit(text, font) swaps known punctuation for drawable lookalikes and
returns (text, missing_chars); callers stop or warn on missing chars. Needs fontTools (doctor.sh checks it).
"""
from functools import lru_cache
from pathlib import Path

SWAP = {'·': '•', '・': '•', '‧': '•', '～': '~', '–': '—'}
BRUSH = Path(__file__).resolve().parent.parent / 'fonts/MaShanZheng-Regular.ttf'


@lru_cache(maxsize=8)
def _cmap(font):
    from fontTools.ttLib import TTFont
    return set(TTFont(str(font), fontNumber=0).getBestCmap())


def fit(text, font=BRUSH):
    try:
        cmap = _cmap(str(font))
    except ImportError:
        return text, set()          # no fontTools: cannot check (doctor.sh reports it)
    out = ''.join(SWAP.get(c, c) if ord(c) not in cmap and SWAP.get(c) and ord(SWAP[c]) in cmap else c for c in text)
    return out, {c for c in out if not c.isspace() and ord(c) not in cmap}
