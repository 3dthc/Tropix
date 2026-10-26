#!/usr/bin/env python3
"""Build the Tropix steel guitars from the Black And Green recordings (Karoryfer, CC0).

    python3 -I tools/build_steels.py [instrument ...]

A steel guitar is played with a bar instead of fretting fingers and usually swelled in with a volume pedal, so you
hear no pick attack, a long even sustain, and glides between notes. Each recorded note is reshaped to match:
  * the pick attack is replaced by a short swell (the plugin's attack and glide controls take it further);
  * the natural guitar decay is partly flattened, as a player riding the volume pedal does, then looped;
  * the bright neck-pickup tone gets a gentle high cut, like a steel's thick tone.

  pedal_steel   from the Gretsch: the juju and highlife pedal steel
  lap_steel     from the Hofner, rounder and woodier: the Hawaiian lap steel
"""
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_guitars import BG, BG_NOTE  # noqa: E402
from build_horns import every, files, layer  # noqa: E402
from prep import LIB, SR, build_instrument, folder_zones, trim_start, write_credits  # noqa: E402

OUT = os.path.join(LIB, "library")


def steelify(x, swell_ms=70.0, flatten=0.7, cutoff=4500.0):
    x = trim_start(x)
    m = x.mean(axis=1)
    # level envelope (60 ms), smoothed; divide part of the decay out so the note sustains like a pedalled steel
    n = int(0.06 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(n) / n, "same")) + 1e-6
    ref = np.percentile(env[: int(0.4 * SR)], 90)
    gain = np.clip((ref / env) ** flatten, 1.0, 6.0)
    gain[: int(0.15 * SR)] = 1.0
    gain = np.convolve(gain, np.ones(n) / n, "same")
    y = x * gain[:, None]
    # remove the pick: start a little in, swell up
    a = int(0.018 * SR)
    y = y[a:]
    s = int(swell_ms / 1000 * SR)
    y[:s] *= (np.sin(np.linspace(0, np.pi / 2, s)) ** 2)[:, None]
    y = sosfilt(butter(2, cutoff, "low", fs=SR, output="sos"), y, axis=0)
    return y.astype(np.float32)


def steel_zones(guitar):
    zs = folder_zones(every(files(BG, guitar, "ord", "*_rr1.wav"), note_re=BG_NOTE), BG_NOTE,
                      layer(r"_(p|mf|f)_rr", ["mf", "f"]), max_len=6.0, fine_tune=True)
    for z in zs:
        z["audio"] = steelify(z["audio"], cutoff=4500.0 if guitar == "green" else 3800.0)
    return zs


KW = dict(loop=True, loop_region=(0.35, 0.9), loop_xfade=0.3, loop_mode="pitch", norm="rms", rms_db=-17.0,
          mono=True, trim=False, even_keys=6.0)

BUILDS = {
    "pedal_steel": ("GUITARS", "karoryfer_bg", lambda: steel_zones("green"), KW),
    "lap_steel": ("GUITARS", "karoryfer_bg", lambda: steel_zones("black"), KW),
}


if __name__ == "__main__":
    for name in (sys.argv[1:] or list(BUILDS)):
        cat, src, zf, kw = BUILDS[name]
        k = build_instrument(name, cat, src, zf(), OUT, **kw)
        loops = [z["loop_score"] for z in k["zones"]]
        print(f"{name:12s} zones={len(k['zones']):3d} {k['total_bytes'] / 1e6:5.1f} MB loop min {min(loops):.2f}")
    write_credits(OUT)
