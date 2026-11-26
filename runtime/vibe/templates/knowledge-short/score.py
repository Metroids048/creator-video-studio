"""score.py — DEMO score for the demo film. Reads audio/events.json (./vf events) → audio/score.wav.
Then: ./vf master   (loudness to −14 LUFS → audio/score.m4a)
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.environ['KIT'], 'audio'))
from synth import Score, glass, hz, swell  # noqa: E402

ROOT = Path(__file__).parent
EV = json.loads((ROOT / 'audio/events.json').read_text())
T, DUR = EV['T'], EV['DUR']
s = Score(DUR)

# every zero crossing of the oscillator rings one glass note, quieter as the energy drains (the knowledge, audible)
for k, c in enumerate(EV['cross']):
    s.place(glass(hz(81 if k % 2 else 76), 2.0, .6), c['t'], .28 * (.25 + .75 * c['e']), (-.3 if k % 2 else .3))

s.pad([(0.3, T['bloom'] + .4, [38, 45, 50, 57], .05), (T['bloom'] - .2, DUR, [38, 45, 50, 54, 57, 64], .08)])
s.place(swell(1.4), T['bloom'] - 1.4, .1)
for j, m in enumerate([62, 66, 69, 74]):
    s.place(glass(hz(m), 3.0, 1.2), T['bloom'] + .5 + j * .07, .06, (j - 1.5) * .2)

s.finish(ROOT / 'audio/score.wav')
