#!/usr/bin/env python3
"""Measure rendered steel pan notes: tuning (cents), octave and twelfth level relative to the fundamental
(early window, 30-500 ms, which is what the ear judges the timbre on), decay time to -40 dB, and peak level.

    python3 -I tools/pan_check.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pan import SR, VOICINGS, mtof, pan_note  # noqa: E402


def peak(x, f, t0, t1, win=0.03):
    seg = x[int(t0 * SR):int(t1 * SR)]
    seg = seg * np.hanning(len(seg))
    N = 1 << 20
    X = np.abs(np.fft.rfft(seg, N))
    fr = np.fft.rfftfreq(N, 1 / SR)
    band = (fr > f * (1 - win)) & (fr < f * (1 + win))
    if not band.any():
        return f, -200.0
    i = np.argmax(X * band)
    return fr[i], 20 * np.log10(X[i] + 1e-12)


def report(vels=(0.35, 0.7, 1.0)):
    rows = []
    for v, d in VOICINGS.items():
        for m in (d["lo"], (d["lo"] + d["hi"]) // 2, d["hi"]):
            for vel in vels:
                x = pan_note(m, vel, v)
                f0 = mtof(m)
                f1, _ = peak(x, f0, 0.25, 1.25)
                _, a1 = peak(x, f0, 0.03, 0.5)
                _, a2 = peak(x, 2 * f0, 0.03, 0.5)
                _, a3 = peak(x, 3 * f0, 0.03, 0.5)
                r = np.sqrt(np.convolve(x ** 2, np.ones(882) / 882, "same"))
                end = np.nonzero(r > r.max() * 0.01)[0][-1] / SR
                rows.append((v, m, vel, 1200 * np.log2(f1 / f0), a2 - a1, a3 - a1, end, np.abs(x).max()))
    print(f"{'voicing':14s} note vel   tune   octave  twelfth  -40dB   peak")
    for v, m, vel, c, o, tw, e, p in rows:
        print(f"{v:14s} {m:4d} {vel:.2f} {c:+5.1f}c {o:+6.1f}dB {tw:+6.1f}dB {e:5.2f}s {p:5.2f}")
    return rows


if __name__ == "__main__":
    report()
