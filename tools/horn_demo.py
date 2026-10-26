#!/usr/bin/env python3
"""Render listening demos for the Tropix horns, played from the prepared library through tools/sampler.py.

    python3 -I tools/horn_demo.py [outdir]

  horns_kompa_tenor_sax     tenor sax lead, kompa feel, 120 BPM in B-flat (scoops, vibrato, a fall at the end)
  horns_trumpet_solo        open trumpet lead, 96 BPM in F, then the same idea on harmon-muted trumpet
  horns_afrobeat_section    trumpet and tenor sax in octaves with trombone, 110 BPM in D minor
  horns_soca_stabs          trumpets and trombones in chord stabs, 156 BPM in A, with a fall to finish
Every melody and riff is original, written for these demos. Drums and bass are simple stand-ins for context.
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logdrum_demo import kick, rim, shaker  # noqa: E402
from pan_demo import finish, place  # noqa: E402
from sampler import SR, doit, fall, note, scoop, vibrato  # noqa: E402

RNG = np.random.default_rng(11)


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def bass(m, dur, vel=0.8):
    """Round electric-bass stand-in: sine plus a filtered saw, plucky envelope."""
    n = int((dur + 0.08) * SR)
    t = np.arange(n) / SR
    f = mtof(m)
    saw = 2 * ((f * t) % 1) - 1
    x = np.sin(2 * np.pi * f * t) + 0.35 * sosfilt(butter(2, 500, "low", fs=SR, output="sos"), saw)
    env = np.exp(-t / 0.6) * (t < dur) + np.exp(-t / 0.6) * np.exp(-(t - dur) / 0.02) * (t >= dur)
    x *= env * vel * 0.32
    return np.stack([x, x], 1)


def cowbell():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = (np.sign(np.sin(2 * np.pi * 562 * t)) + np.sign(np.sin(2 * np.pi * 845 * t))) * np.exp(-t / 0.06)
    x = sosfilt(butter(2, [500, 3500], "band", fs=SR, output="sos"), x)
    return np.stack([x * 0.7, x], 1) * 0.05


def horn(buf, t0, inst, m, vel, dur, voice_spread=True, **kw):
    """Place one horn note with a player's small timing and tuning differences."""
    dt = RNG.normal(0, 0.006) if voice_spread else 0.0
    c = RNG.normal(0, 3.0) if voice_spread else 0.0
    place(buf, note(inst, m, vel, dur, cents=c, **kw), max(0.0, t0 + dt))


def sax_line(buf, t0, b, line, base_vel=0.75, stab="tenor_sax_stab", sus="tenor_sax", vib="tenor_sax_vib",
             transpose=0):
    """line: (beat, midi, beats, flags) with flags in {'s' scoop, 'v' vibrato, 'x' stab, 'f' fall, 'a' accent}."""
    for beat, m, beats, flags in line:
        m += transpose
        vel = base_vel + (0.15 if "a" in flags else 0) + RNG.uniform(-0.05, 0.05)
        dur = beats * b * 0.92
        bends = []
        if "s" in flags:
            bends.append(scoop(-1.2, 0.08))
        if "x" in flags:
            horn(buf, t0 + beat * b, stab, m, vel, min(dur, 0.35), release=0.05)
            continue
        inst = vib if ("v" in flags and vib) else sus
        if "v" in flags and not vib:
            bends.append(vibrato(0.2, 5.3, 16))
        fade = None
        if "f" in flags:
            at = max(0.25, dur - 0.35)
            bends.append(fall(at, -7, 0.4))
            fade = (at, 0.45)
            dur += 0.4
        horn(buf, t0 + beat * b, inst, m, vel, dur, bends=bends, fade_with_fall=fade, release=0.14)


def kompa():
    bpm = 120
    b = 60 / bpm
    bars = 8
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    roots = [46, 51, 53, 46, 46, 51, 53, 46]  # Bb Eb F Bb
    for bar in range(bars):
        t0 = bar * 4 * b
        r = roots[bar] - 12 if roots[bar] - 12 >= 28 else roots[bar]
        for beat in (0, 2):
            place(buf, kick(RNG) * 0.7, t0 + beat * b)
        for e in range(8):
            place(buf, shaker(0.9 if e % 2 else 0.5, RNG), t0 + e * b / 2)
        for beat in (0, 1, 2, 3):
            place(buf, cowbell() * (1.0 if beat in (1, 3) else 0.6), t0 + beat * b + b / 2)
        for pos, iv, d in ((0, 0, 1.2), (1.5, 7, 0.4), (2.5, 0, 0.4), (3, 12, 0.4), (3.5, 7, 0.4)):
            place(buf, bass(r + iv, d * b), t0 + pos * b)
    line = [
        # bar 1 (Bb)
        (0, 65, 1.5, "s"), (1.5, 62, 0.5, ""), (2, 63, 0.5, ""), (2.5, 65, 0.5, ""), (3, 67, 1, "v"),
        # bar 2 (Eb)
        (4, 70, 2, "sv"), (6, 67, 0.5, ""), (6.5, 65, 0.5, ""), (7, 63, 1, ""),
        # bar 3 (F)
        (8, 65, 0.5, "xa"), (8.5, 65, 0.5, "x"), (9, 69, 1, ""), (10, 72, 1, "s"), (11, 69, 0.5, ""), (11.5, 65, 0.5, ""),
        # bar 4 (Bb)
        (12, 74, 3, "sva"),
        # bar 5 (Bb)
        (16, 70, 0.5, ""), (16.5, 72, 0.5, ""), (17, 74, 1, ""), (18, 72, 0.5, ""), (18.5, 70, 0.5, ""), (19, 67, 1, "v"),
        # bar 6 (Eb)
        (20, 67, 1.5, "v"), (21.5, 70, 0.5, ""), (22, 75, 1, "sa"), (23, 74, 0.5, ""), (23.5, 72, 0.5, ""),
        # bar 7 (F)
        (24, 72, 1, ""), (25, 69, 0.5, ""), (25.5, 65, 0.5, ""), (26, 67, 0.5, "x"), (26.5, 69, 0.5, "x"), (27, 72, 1, "s"),
        # bar 8 (Bb)
        (28, 70, 3, "vf"),
    ]
    sax_line(buf, 0, b, line, base_vel=0.72)
    return finish(buf)


def trumpet_solo():
    bpm = 96
    b = 60 / bpm
    bars = 8
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    roots = [50, 46, 41, 48] * 2  # Dm Bb F C
    for bar in range(bars):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * (0.6 if beat % 2 == 0 else 0.0), t0 + beat * b)
            place(buf, rim(RNG) * (0.8 if beat == 3 else 0.0), t0 + beat * b)
        for e in range(16):
            place(buf, shaker(0.6 if e % 4 == 2 else 0.3, RNG), t0 + e * b / 4)
        r = roots[bar] - 12 if roots[bar] - 12 >= 28 else roots[bar]
        for pos, d in ((0, 1.4), (1.75, 0.3), (2.5, 1.0)):
            place(buf, bass(r, d * b, 0.7), t0 + pos * b)
    open_line = [
        (0, 69, 1.5, "s"), (1.5, 67, 0.5, ""), (2, 65, 1, ""), (3, 62, 1, ""),
        (4, 65, 0.5, ""), (4.5, 67, 0.5, ""), (5, 70, 2, "sv"), (7, 69, 1, ""),
        (8, 72, 1.5, "a"), (9.5, 69, 0.5, ""), (10, 65, 1, ""), (11, 67, 0.5, "x"), (11.5, 69, 0.5, "x"),
        (12, 67, 3, "v"),
    ]
    sax_line(buf, 0, b, open_line, base_vel=0.7, stab="trumpet_stab", sus="trumpet", vib="trumpet_vib")
    harmon_line = [(beat + 16, m, d, f.replace("v", "")) for beat, m, d, f in open_line[:-1]] + [(28, 65, 3, "f")]
    sax_line(buf, 0, b, harmon_line, base_vel=0.75, stab="trumpet_harmon", sus="trumpet_harmon", vib=None)
    return finish(buf)


def afrobeat():
    bpm = 110
    b = 60 / bpm
    bars = 8
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    for bar in range(bars):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * (0.75 if beat in (0, 2) else 0.0), t0 + beat * b)
        for e in range(16):
            place(buf, shaker(0.8 if e % 2 else 0.4, RNG), t0 + e * b / 4 + (0.01 if e % 2 else 0))
        for pos in (1, 3):
            place(buf, rim(RNG), t0 + pos * b)
        for pos, m, d in ((0, 38, 0.5), (0.75, 38, 0.25), (1.5, 45, 0.5), (2.5, 43, 0.5), (3, 41, 0.5), (3.5, 36, 0.4)):
            place(buf, bass(m, d * b, 0.75), t0 + pos * b)
    riff = [
        (0, 74, 0.5, "xa"), (0.5, 74, 0.5, "x"), (1.5, 72, 0.5, ""), (2, 69, 1, "s"), (3, 67, 0.5, ""), (3.5, 69, 0.5, "x"),
        (4, 72, 1.5, "sa"), (5.5, 69, 0.5, ""), (6, 67, 0.5, "x"), (6.5, 65, 0.5, "x"), (7, 62, 1, ""),
    ]
    for rep in range(4):
        if rep == 0:
            continue  # the band plays one riff-length alone first
        off = [(beat + rep * 8, m, d, f) for beat, m, d, f in riff]
        sax_line(buf, 0, b, off, 0.78, stab="trumpet_stab", sus="trumpet", vib="trumpet_vib")
        sax_line(buf, 0, b, off, 0.8, transpose=-12)  # tenor sax an octave below
        # trombone: long tones under the riff, a stab and a fall at the end of each riff
        tb = [(rep * 8, 50, 2, "a"), (rep * 8 + 2, 48, 1.5, ""), (rep * 8 + 4, 53, 1.5, "s"),
              (rep * 8 + 6, 52, 0.5, "x"), (rep * 8 + 7, 50, 1, "f" if rep == 3 else "")]
        sax_line(buf, 0, b, tb, 0.7, stab="trombone_stab", sus="trombone", vib=None)
    return finish(buf)


def soca():
    bpm = 156
    b = 60 / bpm
    bars = 8
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    chords = {  # (trumpets, trombones)
        "A": ([73, 76, 81], [45, 57, 64]), "D": ([74, 78, 81], [50, 57, 62]),
        "E": ([71, 76, 80], [52, 59, 64]), "F#m": ([73, 78, 81], [54, 57, 61]),
    }
    prog = ["A", "D", "E", "A", "F#m", "D", "E", "A"]
    for bar, ch in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * 0.8, t0 + beat * b)
            place(buf, shaker(0.9, RNG), t0 + beat * b + b / 2)
            place(buf, shaker(0.4, RNG), t0 + beat * b)
        place(buf, rim(RNG) * 1.2, t0 + 1 * b)
        place(buf, rim(RNG) * 1.2, t0 + 3 * b)
        root = chords[ch][1][0] - 12
        for pos in (0, 0.75, 1.5, 2, 2.75, 3.5):
            place(buf, bass(root + (7 if pos in (1.5, 3.5) else 0), 0.3 * b, 0.8), t0 + pos * b)
        tp, tb = chords[ch]
        hits = [(0.5, 0.4, "x"), (1.5, 0.4, "x"), (2.5, 0.4, "x"), (3, 0.9, "")] if bar % 2 == 0 else \
               [(0, 0.4, "x"), (0.75, 0.4, "x"), (1.5, 0.4, "x"), (2.5, 1.2, "s")]
        last = bar == len(prog) - 1
        for k, (pos, d, f) in enumerate(hits):
            if last and k == len(hits) - 1:
                f, d = "f", 2.0
            for m in tp:
                sax_line(buf, t0, b, [(pos, m, d, f + "a")], 0.82, stab="trumpet_stab", sus="trumpet", vib=None)
            for m in tb:
                sax_line(buf, t0, b, [(pos, m, d, f)], 0.8, stab="trombone_stab", sus="trombone", vib=None)
    return finish(buf)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "docs", "demos")
    os.makedirs(out, exist_ok=True)
    jobs = {"horns_kompa_tenor_sax": kompa, "horns_trumpet_solo": trumpet_solo,
            "horns_afrobeat_section": afrobeat, "horns_soca_stabs": soca}
    for name in (sys.argv[2:] or jobs):
        x = jobs[name]()
        sf.write(os.path.join(out, name + ".wav"), x, SR, subtype="PCM_16")
        print(f"{name}: {len(x) / SR:.1f}s")
