#!/usr/bin/env python3
"""Render listening demos for the Tropix log drum engine.

    python3 -I tools/logdrum_demo.py [outdir]

  logdrum_variations   each variation plays the same 2-bar riff over a light shaker
  logdrum_amapiano     an original 8-bar amapiano groove (113 BPM, F minor): kick, shaker, rim, keys stabs and
                       the log drum line, with glides; bars 1-4 use "classic", bars 5-8 "talking"
All parts are original and synthesized here (the drums and keys are simple stand-ins, not Tropix instruments).
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logdrum import SR, VARIATIONS, log_drum, mtof  # noqa: E402
from pan_demo import finish, place  # noqa: E402

BPM = 113
S16 = 60 / BPM / 4  # one sixteenth note, seconds

# Log drum riff: (16th step within 2 bars, MIDI note, velocity, glide from previous note?)
RIFF = [
    (0, 41, 0.95, False), (3, 41, 0.6, False), (6, 53, 0.75, True), (10, 48, 0.8, False), (14, 46, 0.7, False),
    (16, 37, 0.95, False), (19, 37, 0.6, False), (22, 44, 0.75, False), (25, 49, 0.7, True), (28, 48, 0.8, False),
    (30, 46, 0.65, True),
]
CHORDS = [[53, 56, 60, 63, 67], [49, 53, 56, 60, 63], [46, 49, 53, 56, 60], [48, 52, 55, 58, 61]]  # Fm9 Dbmaj9 Bbm9 C7b9


def kick(rng):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 48 * 2 ** (2.5 * np.exp(-t / 0.03))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)
    return np.stack([x, x], 1) * 0.55


def shaker(vel, rng):
    n = int(0.07 * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n) * (1 - np.exp(-t / 0.004)) * np.exp(-t / 0.018)
    x = sosfilt(butter(2, [5000, 11000], "band", fs=SR, output="sos"), x)
    pan = rng.uniform(-0.2, 0.3)
    return np.stack([x * (1 - pan), x * (1 + pan)], 1) * 0.12 * vel


def rim(rng):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1700 * t) * 0.6 + np.sin(2 * np.pi * 820 * t)) * np.exp(-t / 0.018)
    x += rng.normal(0, 0.4, n) * np.exp(-t / 0.006)
    x = sosfilt(butter(2, 400, "high", fs=SR, output="sos"), x)
    return np.stack([x * 0.8, x], 1) * 0.10


def keys_stab(chord, rng, secs=0.7):
    """Soft electric-keys stand-in: sine + octave partial with a quick bell attack and gentle tremolo."""
    n = int(secs * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for m in chord:
        f = mtof(m) * 2 ** (rng.normal(0, 2) / 1200)
        env = np.exp(-t / 0.35)
        x += (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08)) * env
    x *= 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)
    x[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    return np.stack([x * 0.9, x], 1) * 0.045


def ld(m, vel, var, prev):
    x = log_drum(m, vel, var, glide_from=prev)
    return np.stack([x, x], 1) * 0.75


def play_riff(buf, t0, var, bars=2):
    prev = None
    for step, m, vel, glide in RIFF:
        if step >= bars * 16:
            break
        place(buf, ld(m, vel, var, prev if glide else None), t0 + step * S16)
        prev = m


def variations():
    rng = np.random.default_rng(1)
    names = list(VARIATIONS)
    seg = 32 * S16 + 0.9
    buf = np.zeros((int(SR * (len(names) * seg + 3)), 2))
    for i, var in enumerate(names):
        t0 = i * seg
        for s in range(32):
            place(buf, shaker(0.9 if s % 4 == 2 else 0.5, rng), t0 + s * S16)
        play_riff(buf, t0, var)
    return finish(buf)


def groove():
    rng = np.random.default_rng(2)
    bars = 8
    buf = np.zeros((int(SR * (bars * 16 * S16 + 3)), 2))
    for bar in range(bars):
        t0 = bar * 16 * S16
        for beat in range(4):
            place(buf, kick(rng) * (1.0 if beat == 0 else 0.8), t0 + beat * 4 * S16)
        for s in range(16):
            acc = 1.0 if s % 4 == 2 else (0.7 if s % 2 else 0.45)
            place(buf, shaker(acc, rng), t0 + s * S16 + (0.012 if s % 2 else 0))
        for s in (4, 12):
            place(buf, rim(rng), t0 + s * S16)
        for s in (11,):
            place(buf, rim(rng) * 0.6, t0 + s * S16)
        chord = CHORDS[bar % 2]  # riff is 2 bars: Fm9 then Dbmaj9
        for s in (2, 6, 10, 13):
            place(buf, keys_stab(chord, rng), t0 + s * S16)
    for half in range(bars // 2):
        var = "classic" if half < 2 else "talking"
        play_riff(buf, half * 32 * S16, var)
    return finish(buf)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "docs", "demos")
    os.makedirs(out, exist_ok=True)
    for name, fn in (("logdrum_variations", variations), ("logdrum_amapiano", groove)):
        x = fn()
        sf.write(os.path.join(out, name + ".wav"), x, SR, subtype="PCM_16")
        print(f"{name}: {len(x) / SR:.1f}s")
