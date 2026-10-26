#!/usr/bin/env python3
"""Render the Tropix synthesis engines into multisampled instruments (source "tropix": original synthesis).

    python3 -I tools/build_engines.py [instrument ...]

The engines run offline, so the plugin plays them as samples with no extra CPU on the MPC.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logdrum import VARIATIONS, log_drum  # noqa: E402
from organ import organ_note  # noqa: E402
from pan import VOICINGS, pan_note  # noqa: E402
from perc_model import ipu, melodica, timbale  # noqa: E402
from synths import LOOP_S, VOICES, mtof as smtof, snap  # noqa: E402
from build_horns import files, layer  # noqa: E402
from prep import LIB, build_instrument, folder_zones, write_credits  # noqa: E402
from tine import tine_note  # noqa: E402

OUT = os.path.join(LIB, "library")


def stereo(x):
    x = np.asarray(x, dtype=np.float32)
    return np.stack([x, x], axis=1)


def zones(fn, roots, vels):
    """Render fn(root, vel) for every root and velocity layer; layers spread evenly over 1-127."""
    n = len(vels)
    out = []
    for r in roots:
        for i, v in enumerate(vels):
            lo, hi = 1 + round(127 * i / n), round(127 * (i + 1) / n)
            out.append(dict(audio=stereo(fn(r, v)), root=r, vel=i + 1, lovel=1 if i == 0 else lo, hivel=hi))
    return out


ONE = dict(fade_s=0.3, floor_db=-60.0, norm="rms", rms_db=-17.0, mono=True)
LOOP = dict(loop=True, loop_region=(0.35, 0.95), loop_xfade=0.25, norm="rms", rms_db=-17.0, mono=True)


def pan_roll(m, vel, voicing="tenor"):
    """A steady two-stick roll that loops exactly: strokes fall on a fixed sample grid and repeat an 8-stroke
    cycle (each stroke its own slight level, timing and tone), so after the first ring-in the sound is periodic.
    Returns (audio, (loop_start, loop_end))."""
    P = 3392                              # stroke spacing in samples: 13 strokes a second
    cyc = 8
    rng = np.random.default_rng(m)
    jit = rng.integers(-60, 60, cyc)      # each stroke of the cycle a little early or late (<1.4 ms)
    lev = rng.uniform(-0.07, 0.07, cyc)
    strokes = [pan_note(m, float(np.clip(vel + lev[k], 0.1, 1)), voicing, rng=np.random.default_rng(m * 13 + k),
                        secs=1.2) for k in range(cyc)]
    total = 44 * P
    buf = np.zeros(total + len(strokes[0]))
    for k in range(44):
        i = k * P + int(jit[k % cyc]) + 60
        x = strokes[k % cyc] * 0.55
        buf[i:i + len(x)] += x
    return buf[:total], (24 * P, 40 * P)


def roll_zones(roots, vels):
    out = []
    n = len(vels)
    for r in roots:
        for i, v in enumerate(vels):
            x, lp = pan_roll(r, v)
            lo, hi = 1 + round(127 * i / n), round(127 * (i + 1) / n)
            out.append(dict(audio=stereo(x), root=r, vel=i + 1, lovel=1 if i == 0 else lo, hivel=hi, loop_points=lp))
    return out


def synth_loop_zones(fn, roots, vels):
    """Looped synth voices: rendered so they repeat exactly from 1 s to 1 s + LOOP_S, with the oscillators' small
    snap-to-loop pitch error corrected by each zone's tune."""
    n = len(vels)
    out = []
    for r in roots:
        tune = -round(1200 * np.log2(float(snap(smtof(r))) / smtof(r)))
        for i, v in enumerate(vels):
            lo, hi = 1 + round(127 * i / n), round(127 * (i + 1) / n)
            out.append(dict(audio=stereo(fn(r, v)), root=r, vel=i + 1, lovel=1 if i == 0 else lo, hivel=hi,
                            loop_points=(SR, SR + int(LOOP_S * SR)), tune=tune))
    return out


def kit_zones(sounds, vels):
    """sounds: (key, fn(vel) -> mono audio). One key per sound, velocity layers spread over 1-127."""
    n = len(vels)
    out = []
    for key, fn in sounds:
        for i, v in enumerate(vels):
            lo, hi = 1 + round(127 * i / n), round(127 * (i + 1) / n)
            out.append(dict(audio=stereo(fn(v)), root=key, vel=i + 1, lovel=1 if i == 0 else lo, hivel=hi))
    return out


TIMBALES = [(36, lambda v: timbale("open", "hembra", v)), (37, lambda v: timbale("rim", "hembra", v)),
            (38, lambda v: timbale("muted", "hembra", v)), (39, lambda v: timbale("open", "macho", v)),
            (40, lambda v: timbale("rim", "macho", v)), (41, lambda v: timbale("muted", "macho", v)),
            (42, lambda v: timbale("paila", "macho", v)), (43, lambda v: timbale("paila", "hembra", v))]
IPU = [(36, lambda v: ipu("heel", v)), (37, lambda v: ipu("tip", v)), (38, lambda v: ipu("slap", v))]
HARM = os.path.join(LIB, "raw", "VCSL", "Aerophones", "Free Aerophones", "Harmonica-Hohner-Super64", "Sustains")
KIT = dict(kit=True, fade_s=0.1, floor_db=-55.0, norm="rms", rms_db=-17.0, mono=True)

SR = 44100
BUILDS = {
    "tine_piano": ("KEYS", lambda: zones(lambda r, v: tine_note(r, v), range(28, 98, 3), [0.3, 0.55, 0.8, 1.0]),
                   dict(ONE, max_len=4.5)),
    **{reg: ("KEYS", lambda reg=reg: zones(lambda r, v: organ_note(r, v, reg, secs=3.0), range(36, 97, 3), [0.8]),
             LOOP) for reg in ("organ_bubble", "organ_perc", "organ_full")},
    **{f"pan_{vo}": ("PAN", lambda vo=vo: zones(lambda r, v: pan_note(r, v, vo),
                                                 range(VOICINGS[vo]["lo"], VOICINGS[vo]["hi"] + 1, 2),
                                                 [0.35, 0.65, 0.95]),
                     dict(ONE, max_len=4.0)) for vo in VOICINGS},
    "pan_roll": ("PAN", lambda: roll_zones(range(62, 91, 2), [0.45, 0.8]),
                 dict(LOOP, trim=False, max_len=4.0, floor_db=-120.0)),
    "timbales": ("PERCUSSION", lambda: kit_zones(TIMBALES, [0.4, 0.7, 1.0]), dict(KIT, max_len=1.2)),
    "ipu": ("PERCUSSION", lambda: kit_zones(IPU, [0.4, 0.7, 1.0]), dict(KIT, max_len=1.0)),
    "melodica": ("HORNS", lambda: zones(lambda r, v: melodica(r, v), range(53, 90, 3), [0.5, 0.9]),
                 dict(LOOP, loop_region=(0.3, 0.95))),
    **{name: ("SYNTH", (lambda fn=fn, lo=lo, hi=hi: synth_loop_zones(fn, range(lo, hi + 1, 3), [0.5, 0.95]))
              if looped else (lambda fn=fn, lo=lo, hi=hi: zones(lambda r, v: fn(r, v), range(lo, hi + 1, 3), [0.5, 0.95])),
              dict(LOOP, trim=False, max_len=1.0 + LOOP_S + 0.1, floor_db=-120.0) if looped else dict(ONE, max_len=2.5))
       for name, (fn, looped), (lo, hi) in ((n, VOICES[n], r) for n, r in (
           ("soca_lead", (48, 96)), ("soca_brass", (43, 91)), ("afro_pluck", (48, 96)),
           ("piano_pluck", (48, 100)), ("island_pad", (36, 84)), ("sub_bass", (24, 60))))},
    **{f"logdrum_{va}": ("BASS", lambda va=va: zones(lambda r, v: log_drum(r, v, va), range(28, 66, 2),
                                                      [0.45, 0.75, 1.0]),
                         dict(ONE, max_len=2.5)) for va in VARIATIONS},
}


# sampled reeds (VCSL, CC0) sit here with the melodica so all the free-reed sounds build together
SAMPLED = {
    "harmonica": ("HORNS", "vcsl",
                  lambda: folder_zones(files(HARM, "Normal", "*.wav") + files(HARM, "Accented", "*.wav"),
                                       r"_([A-G]#?\d)\.wav$", lambda p: 1 if "Accented" in p else 0, max_len=3.5,
                                       fine_tune=True),
                  dict(LOOP, loop_mode="pitch", loop_xfade=0.3, loop_region=(0.3, 0.92))),
    "harmonica_vib": ("HORNS", "vcsl",
                      lambda: folder_zones(files(HARM, "Vib", "*.wav"), r"_([A-G]#?\d)\.wav$", lambda p: 0,
                                           max_len=3.5, fine_tune=True),
                      dict(LOOP, loop_mode="pitch", loop_xfade=0.3, loop_region=(0.3, 0.92))),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDS) + list(SAMPLED)
    for name in names:
        if name in SAMPLED:
            cat, src, zf, kw = SAMPLED[name]
        else:
            (cat, zf, kw), src = BUILDS[name], "tropix"
        k = build_instrument(name, cat, src, zf(), OUT, **kw)
        roots = sorted({z["root"] for z in k["zones"]})
        loops = [z["loop_score"] for z in k["zones"] if "loop_score" in z]
        print(f"{name:20s} zones={len(k['zones']):3d} roots={roots[0]}-{roots[-1]} ({len(roots)}) "
              f"{k['total_bytes'] / 1e6:5.1f} MB" + (f" loop min {min(loops):.2f}" if loops else ""))
    write_credits(OUT)
