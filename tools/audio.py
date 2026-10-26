"""Shared audio analysis helpers for preparing Tropix sample sets."""
import re

import numpy as np

NOTE_RE = re.compile(r"(?<![A-Za-z])([A-G])(#|b)?(-?\d)(?=[_\-\. ]|$)")
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def name_to_midi(name):
    """'A#2' -> 46 (C4 = 60). Returns None if no note name is found."""
    m = NOTE_RE.search(name)
    if not m:
        return None
    n = NAMES[m.group(1)] + {"#": 1, "b": -1, None: 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + n


def midi_name(m):
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][int(m) % 12] + str(int(m) // 12 - 1)


def mono(x):
    return x.mean(axis=1) if x.ndim == 2 else x


def yin(x, sr, fmin=40.0, fmax=2000.0, thresh=0.12):
    """YIN fundamental estimate of a (mostly) stationary frame. Returns Hz or None."""
    x = x - x.mean()
    tau_min = int(sr / fmax)
    tau_max = min(int(sr / fmin), len(x) // 2)
    if tau_max <= tau_min + 2:
        return None
    w = len(x) - tau_max
    # difference function via FFT autocorrelation
    xs = x[: w + tau_max]
    n = 1 << int(np.ceil(np.log2(2 * len(xs))))
    X = np.fft.rfft(xs, n)
    acf = np.fft.irfft(X * np.conj(X), n)[: tau_max + 1]
    cs = np.concatenate([[0.0], np.cumsum(xs ** 2)])
    e0 = cs[w]
    et = cs[np.arange(tau_max + 1) + w] - cs[np.arange(tau_max + 1)]
    d = e0 + et - 2 * acf
    d[0] = 0
    cmnd = d[1:] * np.arange(1, tau_max + 1) / np.maximum(np.cumsum(d[1:]), 1e-12)
    cmnd = np.concatenate([[1.0], cmnd])
    cand = np.nonzero(cmnd[tau_min:] < thresh)[0]
    if len(cand):
        t = cand[0] + tau_min
        while t + 1 <= tau_max and cmnd[t + 1] < cmnd[t]:
            t += 1
    else:
        t = int(np.argmin(cmnd[tau_min:]) + tau_min)
        if cmnd[t] > 0.35:
            return None
    # parabolic interpolation
    if 1 <= t < tau_max:
        a, b, c = cmnd[t - 1], cmnd[t], cmnd[t + 1]
        den = a - 2 * b + c
        t = t + (0.5 * (a - c) / den if den != 0 else 0)
    return sr / t


def rms_env(x, sr, win_ms=10):
    n = max(1, int(sr * win_ms / 1000))
    return np.sqrt(np.convolve(x ** 2, np.ones(n) / n, "same"))


def pitch_of(x, sr, guess_midi=None):
    """Median YIN pitch over the steady part of a note (between 25% and 75% of its loud span)."""
    x = mono(x)
    env = rms_env(x, sr)
    loud = np.nonzero(env > env.max() * 0.25)[0]
    if len(loud) < sr * 0.05:
        loud = np.nonzero(env > env.max() * 0.1)[0]
    a, b = loud[0], loud[-1]
    a, b = a + (b - a) // 4, b - (b - a) // 4
    fmin, fmax = 30.0, 2500.0
    if guess_midi is not None:
        g = 440 * 2 ** ((guess_midi - 69) / 12)
        fmin, fmax = g / 1.6, g * 1.6
    frame = int(sr * 0.06)
    est = []
    for s in range(a, max(a + 1, b - frame), frame // 2):
        f = yin(x[s:s + frame], sr, fmin, fmax)
        if f:
            est.append(f)
    if not est:
        return None
    return float(np.median(est))


def cents(f, m):
    return 1200 * np.log2(f / (440 * 2 ** ((m - 69) / 12)))
