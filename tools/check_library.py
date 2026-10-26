#!/usr/bin/env python3
"""Check prepared instruments by playing them through the offline sampler.

    python3 -I tools/check_library.py [instrument ...]

Per instrument:
  tuning   every zone played at its root with its tune applied, measured with YIN and from the spectrum (cents;
           the smaller deviation counts; worst case reported)
  loops    held 7 s notes: the largest jump in the 20 ms level envelope after the loop starts (dB), which catches
           a click or a level bump at the loop point
  layers   the RMS of each velocity layer at a mid note, which must rise from soft to loud
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio import pitch_of, rms_env  # noqa: E402
from prep import measured_cents  # noqa: E402
from sampler import LIB, SR, keymap, note  # noqa: E402


def check(inst):
    k = keymap(inst)
    worst, bad = 0.0, []
    for z in k["zones"]:
        vel = (z["lovel"] + z["hivel"]) / 2 / 127
        y = note(inst, z["root"], vel, 1.2)
        f = pitch_of(y, SR, guess_midi=z["root"])
        c_spec = measured_cents(y.astype(np.float32), z["root"])
        if f is None:
            c = c_spec
        else:
            # YIN is thrown by strongly asymmetric waveforms, the spectral peak by inharmonic partials: a zone is
            # in tune if either method says so
            c = min(1200 * np.log2(f / (440 * 2 ** ((z["root"] - 69) / 12))), c_spec, key=abs)
        worst = max(worst, abs(c))
        if abs(c) > 8:
            bad.append((z["root"], z["lovel"], round(c, 1)))
    loop_jump = None
    if k["loop"]:
        jumps = []
        for z in k["zones"]:
            vel = (z["lovel"] + z["hivel"]) / 2 / 127
            y = note(inst, z["root"], vel, 7.0, release=0.0)[:int(6.9 * SR)].mean(axis=1)
            e = 20 * np.log10(rms_env(y, SR, 20)[::int(0.02 * SR)] + 1e-9)
            st = int(z["loop_start"] / SR / 0.02)
            d = np.abs(np.diff(e[st:]))
            jumps.append((float(d.max()), z["root"], z["lovel"]))
        loop_jump = max(jumps)
    roots = sorted({z["root"] for z in k["zones"]})
    mid = roots[len(roots) // 2]
    lv = sorted({(z["lovel"], z["hivel"]) for z in k["zones"]})
    levels = []
    for lo, hi in lv:
        y = note(inst, mid, (lo + hi) / 2 / 127, 0.8)
        levels.append(round(20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9), 1))
    print(f"{inst:16s} tuning worst {worst:4.1f}c" + (f" off: {bad}" if bad else "")
          + (f" | loop worst jump {loop_jump[0]:.1f} dB (root {loop_jump[1]}, vel {loop_jump[2]})" if loop_jump else "")
          + f" | layer RMS {levels}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(d for d in os.listdir(LIB) if os.path.exists(os.path.join(LIB, d, "keymap.json")))
    for n in names:
        check(n)
