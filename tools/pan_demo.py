#!/usr/bin/env python3
"""Render listening demos for the Tropix steel pan engine.

    python3 -I tools/pan_demo.py [outdir]

Writes, per voicing, a scale with soft/medium/hard strikes, plus a short original calypso arrangement for the full
steel band (tenor melody, double-second strums, cello comping, bass line) and a tenor roll. The phrase is original,
written for this demo.
"""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pan import SR, VOICINGS, pan_note, stereo_place  # noqa: E402

_cache = {}


def note(m, vel, voicing, seed=0):
    key = (m, round(vel, 2), voicing, seed)
    if key not in _cache:
        rng = np.random.default_rng((m * 131 + sum(map(ord, voicing)) + 7919 * seed) & 0xFFFFFFFF)
        v = VOICINGS[voicing]
        _cache[key] = stereo_place(pan_note(m, vel, voicing, rng=rng), m, v["lo"], v["hi"], rng=rng)
    return _cache[key]


def place(buf, x, t):
    i = int(t * SR)
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[: j - i]


def reverb(x, secs=1.4, wet=0.18, predelay=0.012, seed=3):
    """Small hall: decorrelated exponentially decaying noise IR per channel, low-passed as it decays."""
    from scipy.signal import fftconvolve, butter, sosfilt
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    out = np.zeros((len(x) + n - 1, 2))
    for c in range(2):
        ir = rng.normal(0, 1, n) * np.exp(-np.log(1000) / secs * t)
        ir = sosfilt(butter(1, 5500, "low", fs=SR, output="sos"), ir)
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])[:n]
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, c] = fftconvolve(x[:, c], ir)[: len(out)]
    dry = np.zeros_like(out)
    dry[: len(x)] = x
    return dry + wet * out


def finish(x, peak_db=-1.0):
    x = reverb(x)
    # trim trailing silence
    a = np.max(np.abs(x), axis=1)
    last = np.nonzero(a > 1e-4)[0]
    x = x[: (last[-1] + int(0.05 * SR)) if len(last) else len(x)]
    return x * (10 ** (peak_db / 20) / max(1e-9, np.max(np.abs(x))))


def scale_demo(voicing):
    v = VOICINGS[voicing]
    major = [0, 2, 4, 5, 7, 9, 11, 12]
    root = v["lo"] + ((60 - v["lo"]) % 12) if v["lo"] <= 60 else v["lo"] + ((72 - v["lo"]) % 12)
    root = max(v["lo"], min(root, v["hi"] - 12))
    step = 0.30 if voicing != "bass" else 0.45
    buf = np.zeros((int(SR * 30), 2))
    t = 0.0
    for vel in (0.35, 0.65, 0.95):
        seq = [root + s for s in major] + [root + s for s in reversed(major[:-1])]
        for m in seq:
            place(buf, note(m, vel, voicing), t)
            t += step
        t += 0.8
    return finish(buf[: int((t + 3) * SR)])


def calypso():
    """An original 8-bar calypso in F at 112 BPM: I - IV - V7 - I, twice."""
    bpm = 112
    b = 60 / bpm
    bars = 8
    buf = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    F, Bb, C = 53, 58, 48
    prog = [("F", [65, 69, 72]), ("Bb", [65, 70, 74]), ("C7", [64, 67, 70]), ("F", [65, 69, 72])] * 2
    roots = {"F": F, "Bb": Bb, "C7": C}
    rng = np.random.default_rng(7)

    # bass: root on 1, fifth on the "and" of 2, approach note on 4
    for bar, (name, _) in enumerate(prog):
        r = roots[name]
        t0 = bar * 4 * b
        place(buf, 0.9 * note(r - 12 if r - 12 >= 33 else r, 0.8, "bass"), t0)
        place(buf, 0.75 * note(r - 5 if r - 5 >= 33 else r + 7, 0.6, "bass"), t0 + 1.5 * b)
        nxt = roots[prog[(bar + 1) % len(prog)][0]]
        place(buf, 0.7 * note(min(53, max(33, nxt - 13)), 0.55, "bass"), t0 + 3 * b)

    # cello: off-beat comping (the classic calypso "chk") on the and of each beat
    for bar, (name, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):
            for k, m in enumerate(ch[:2]):
                mm = m - 12
                place(buf, 0.45 * note(mm, 0.45 + 0.1 * (beat % 2), "cello", seed=beat), t0 + (beat + 0.5) * b + 0.006 * k)

    # double second: quick strummed chord on 1 and 3
    for bar, (name, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in (0, 2):
            for k, m in enumerate(ch):
                place(buf, 0.42 * note(m - 12 + 12 * (m - 12 < 54), 0.55, "double_second", seed=k), t0 + beat * b + 0.012 * k)

    # tenor melody (original), eighth-note grid positions within each bar
    mel = [
        [(0, 77), (1, 76), (1.5, 77), (2.5, 72), (3.5, 74)],
        [(0, 74), (0.5, 72), (1.5, 70), (2, 74), (3, 77), (3.5, 79)],
        [(0, 79), (1, 76), (1.5, 72), (2.5, 74), (3, 76), (3.5, 79)],
        [(0, 77), (1.5, 81), (2, 79), (3, 77)],
        [(0, 81), (0.5, 79), (1, 77), (1.5, 76), (2, 77), (3, 72)],
        [(0, 74), (0.5, 77), (1.5, 82), (2.5, 81), (3, 79)],
        [(0, 79), (0.5, 81), (1, 79), (1.5, 76), (2, 72), (3, 76), (3.5, 79)],
        [(0, 77), (1, 72), (1.5, 69), (2, 65)],
    ]
    for bar, notes in enumerate(mel):
        t0 = bar * 4 * b
        for pos, m in notes:
            vel = 0.8 if pos in (0, 2) else 0.62
            vel += rng.uniform(-0.06, 0.06)
            swing = 0.06 * b if (pos * 2) % 2 == 1 else 0.0
            place(buf, 0.85 * note(m, round(vel, 2), "tenor"), t0 + pos * b + swing)
    # last bar: tenor holds the final F with a roll
    end = bars * 4 * b
    roll(buf, [77, 81], end - 2 * b, 2.6, 0.5)
    return finish(buf)


def roll(buf, notes, t0, secs, vel, rate=13.0):
    """Two-stick tremolo: alternating strikes, slight timing and level jitter, swell then fade."""
    rng = np.random.default_rng(int(t0 * 1000))
    t = 0.0
    k = 0
    while t < secs:
        shape = np.sin(np.pi * min(1.0, t / secs)) ** 0.6
        v = np.clip(vel * (0.55 + 0.45 * shape) + rng.uniform(-0.05, 0.05), 0.1, 1)
        for m in notes:
            place(buf, 0.55 * note(m, round(v, 2), "tenor", seed=k % 4), t0 + t + rng.uniform(0, 0.004))
        t += 1 / rate + rng.normal(0, 0.004)
        k += 1


def roll_demo():
    buf = np.zeros((int(SR * 14), 2))
    roll(buf, [72, 76], 0.2, 2.5, 0.45)
    roll(buf, [74, 77], 3.2, 2.5, 0.6)
    roll(buf, [76, 79, 84], 6.2, 3.5, 0.75)
    return finish(buf[: int(SR * 12)])


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "docs", "demos")
    os.makedirs(out, exist_ok=True)
    jobs = [(f"pan_scale_{v}", lambda v=v: scale_demo(v)) for v in VOICINGS]
    jobs += [("pan_roll_tenor", roll_demo), ("pan_calypso_band", calypso)]
    for name, fn in jobs:
        x = fn()
        p = os.path.join(out, name + ".wav")
        sf.write(p, x, SR, subtype="PCM_16")
        print(f"{name}: {len(x) / SR:.1f}s")
