#!/usr/bin/env python3
"""Measure every preset through the real engine and write tools/preset_trim.json: an output trim per preset so the
presets play at a similar loudness (a loud 400 ms stretch of a test phrase at TARGET_DB), without letting a
preset's peaks rise past PEAK_DB.

    python3 tools/balance.py            (needs gcc and the packed instruments in engine/)"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MPC = os.environ.get("MPC_VST", os.path.join(REPO, "..", "mpc-vst-plugins"))
TARGET_DB, PEAK_DB, LO, HI = -21.0, -1.5, -9.0, 9.0


def main():
    env = dict(os.environ, TROPIX_NO_TRIM="1")
    subprocess.run([sys.executable, os.path.join(HERE, "tropix_params.py")], check=True, env=env)
    sys.path.insert(0, HERE)
    import presets
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "render_test")
        subprocess.run(["gcc", "-O2", "-I" + os.path.join(MPC, "wrapper"), "-I" + os.path.join(REPO, "src"),
                        os.path.join(HERE, "render_test.c"), "-lm", "-lpthread", "-o", exe], check=True)
        subprocess.run([exe, os.path.join(REPO, "engine"), tmp], check=True, stdout=subprocess.DEVNULL)
        trims = {}
        for i, p in enumerate(presets.PRESETS):
            a, _ = sf.read(os.path.join(tmp, "%03d.wav" % (i + 1)))
            m = a.mean(1)
            w = 17640
            st = [10 * np.log10(np.mean(m[k:k + w] ** 2) + 1e-12) for k in range(0, len(m) - w, w // 4)]
            loud = np.percentile(st, 90)
            peak = 20 * np.log10(np.abs(a).max() + 1e-9)
            t = min(TARGET_DB - loud, PEAK_DB - peak)
            trims[p["name"]] = round(float(np.clip(t, LO, HI)), 1)
            print("%-22s loud %6.1f  peak %5.1f  trim %+5.1f" % (p["name"], loud, peak, trims[p["name"]]))
    json.dump(trims, open(os.path.join(HERE, "preset_trim.json"), "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "tropix_params.py")], check=True)


if __name__ == "__main__":
    main()
