"""synth.py — code-synthesised score on the film's own timeline. Extracted from 同步·萤火 score.py.

    import sys; sys.path.insert(0, KIT + '/audio'); from synth import *
    s = Score(dur)                        # stereo 48 kHz buffer
    s.place(glass(hz(81)), t=3.2, gain=.2, pan=-.3)
    s.pad([(0, 12, [38, 45, 50, 57], .06)])
    s.finish('audio/score.wav')           # reverb + soft clip + peak headroom; master.sh does loudness

Voices: glass (bells/sparkles/fireflies), tick (clock, wood, clicks), thump (heart, impact), swell (riser into a cut),
noise_bed (wind, room tone). Every event should come from window.events() so picture and sound share one clock.
"""
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
_rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def smooth(a, b, x):
    x = np.clip((np.asarray(x) - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def _band(sig, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), sig)


def glass(f, dur=1.8, decay=.55, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + .35 * bright * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t / (decay * .4))
         + .12 * bright * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t / (decay * .2)))
    return s * env(n, .004, decay)


def tick(f=1800, dur=.08, decay=.012):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) * .6 + _band(_rng.standard_normal(n), f * .7, f * 1.4) * .5) * np.exp(-t / decay)


def thump(f0=58, dur=.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + .6 * np.exp(-t / .03))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / .004) * np.exp(-t / .09)


def swell(dur, notes=(86, 90, 93)):
    n = int(dur * SR)
    t = np.arange(n) / SR
    shimmer = sum(np.sin(2 * np.pi * hz(m) * t) for m in notes) / len(notes)
    return (_band(_rng.standard_normal(n), 300, 5000) * .25 + shimmer * .6) * (t / dur) ** 2.4


def noise_bed(dur, lo=120, hi=900):
    n = int(dur * SR)
    return _band(_rng.standard_normal(n), lo, hi) * (.6 + .4 * np.sin(2 * np.pi * .05 * np.arange(n) / SR))


def grouped(times, window=.03):
    """Merge near-simultaneous events into (start, count) — loud chords instead of a hundred clicks."""
    out = []
    for t in sorted(times):
        if out and t - out[-1][0] < window:
            out[-1][1] += 1
        else:
            out.append([t, 1])
    return out


class Score:
    def __init__(self, dur):
        self.dur, self.n = dur, int(dur * SR)
        self.dry = np.zeros((2, self.n))
        self.t = np.arange(self.n) / SR

    def place(self, sig, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= self.n or i + len(sig) <= 0:
            return
        s = sig[max(0, -i): self.n - i] if i < 0 else sig[: self.n - i]
        i = max(0, i)
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.dry[0, i:i + len(s)] += s * gain * left
        self.dry[1, i:i + len(s)] += s * gain * right

    def pad(self, chords, cutoff=1400):
        """chords: [(start, end, [midi…], level)] — a warm bed that follows the chapters."""
        p = np.zeros(self.n)
        for a, b, notes, level in chords:
            i0, i1 = int(a * SR), min(self.n, int(b * SR))
            t = self.t[i0:i1]
            e = smooth(a, a + 1.6, t) * (1 - smooth(b - .8, b, t))
            s = np.zeros_like(t)
            for j, m in enumerate(notes):
                f = hz(m)
                s += (np.sin(2 * np.pi * f * t + j) + .5 * np.sin(2 * np.pi * f * 2.0004 * t + 2 * j)) * (1 + .08 * np.sin(2 * np.pi * .07 * t + j * 1.7))
            p[i0:i1] += s / (len(notes) * 1.5) * e * level * 2.4
        p = sosfilt(butter(2, cutoff, 'low', fs=SR, output='sos'), p)
        p = sosfilt(butter(2, 75, 'high', fs=SR, output='sos'), p)
        self.dry += np.vstack([p, np.roll(p, 240)])

    def finish(self, path, reverb=2.8, wet=.45, fade=(.3, .6)):
        ir_n = int(reverb * SR)
        ir_t = np.arange(ir_n) / SR
        ir = np.vstack([_rng.standard_normal(ir_n), _rng.standard_normal(ir_n)]) * np.exp(-ir_t / (reverb / 3.7))
        ir = sosfilt(butter(1, 5000, 'low', fs=SR, output='sos'), ir)
        ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
        w = np.vstack([fftconvolve(self.dry[c], ir[c])[:self.n] for c in range(2)])
        mix = self.dry * .75 + w * wet
        mix *= smooth(0, fade[0], self.t) * (1 - smooth(self.dur - fade[1], self.dur, self.t))
        mix = np.tanh(mix * 1.4) / 1.4
        peak = np.abs(mix).max()
        if peak > 0:
            mix /= peak / .89
        with wave.open(str(path), 'wb') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(SR)
            f.writeframes((mix.T * 32767).astype('<i2').tobytes())
        print(f'{path}  {self.dur:.2f} s  (now run master.sh for loudness)')
