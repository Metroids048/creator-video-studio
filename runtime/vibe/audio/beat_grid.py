#!/usr/bin/env python3
"""beat_grid.py <audio> [--from=S] [--to=S] [--lrc=file.lrc] — tempo, beat phase, and where each lyric line sits on the grid.

Needs ffmpeg and numpy (python3 -m venv .venv && .venv/bin/pip install numpy). Prints the BPM (the fast pulse; halve it
for a ballad feel in PROJECT.bpm), the time of a beat near --from, and for each LRC line its beat index, so you can
pick a clip start on a bar line and put PROJECT.offset on the grid.
"""
import os, re, subprocess, sys
import numpy as np

args = dict(a.lstrip('-').split('=', 1) if '=' in a else (a, True) for a in sys.argv[2:])
src, t0, t1 = sys.argv[1], float(args.get('from', 0)), float(args.get('to', 0)) or None
sr, hop, win = 22050, 128, 2048
cmd = [os.environ.get('FFMPEG') or 'ffmpeg', '-v', 'error', '-ss', str(t0)] + (['-t', str(t1 - t0)] if t1 else []) + ['-i', src, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-']
x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)

# spectral-flux onset envelope
fr = np.lib.stride_tricks.sliding_window_view(x, win)[::hop]
S = np.log1p(np.abs(np.fft.rfft(fr * np.hanning(win), axis=1)))
flux = np.maximum(0, np.diff(S, axis=0)).sum(1)
flux = np.maximum(flux - np.convolve(flux, np.ones(64) / 64, 'same'), 0)
fps = sr / hop

# tempo: autocorrelation peak (interpolated lag) between 70 and 170 BPM
ac = np.correlate(flux, flux, 'full')[len(flux) - 1:]
def score(bpm):
    lag = fps * 60 / bpm; l = int(lag); f = lag - l
    return ac[l] * (1 - f) + ac[l + 1] * f
bpm = max(np.arange(70, 170, .05), key=score)
B = 60 / bpm

# phase: the offset whose comb of beats collects the most onset energy
def comb(p):
    idx = (np.arange(p, len(flux) / fps, B) * fps).astype(int)
    return flux[idx[idx < len(flux)]].sum()
phase = max(np.arange(0, B, .005), key=comb)
first = t0 + phase + (hop + win / 2) / sr   # flux frame k describes the window centred (hop + win/2) samples later

# refine: snap each predicted beat to the strongest onset within ±B/4, then least-squares fit time = first + k·B
lat = (hop + .78 * win) / sr   # flux peak → audible onset, calibrated on click tracks (0.300 + k·0.5 s, 1.130 + k·0.4286 s)
ks, ts_ = [], []
for k in range(int((len(flux) / fps - phase) / B)):
    c = int((phase + k * B) * fps); w = int(B / 4 * fps)
    lo, hi = max(0, c - w), min(len(flux), c + w + 1)
    if hi - lo < 3: continue
    j = lo + int(np.argmax(flux[lo:hi]))
    if flux[j] > np.median(flux) * 4:
        ks.append(k); ts_.append(j / fps)
if len(ks) >= 8:
    B, ph = np.polyfit(ks, ts_, 1)
    bpm, first = 60 / B, t0 + ph + lat
print(f'bpm {bpm:.2f}  (half-time {bpm / 2:.3f})   beat {B:.4f} s   a beat at {first:.3f} s')

if 'lrc' in args:
    for line in open(args['lrc'], encoding='utf-8'):
        m = re.match(r'\[(\d+):(\d+(?:\.\d+)?)\](.*)', line.strip())
        if not m: continue
        t = int(m[1]) * 60 + float(m[2])
        print(f'{t:8.2f}  beat {(t - first) / B:7.2f}  {m[3]}')
