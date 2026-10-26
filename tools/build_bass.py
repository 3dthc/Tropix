#!/usr/bin/env python3
"""Build the Tropix bass guitar multisamples (Karoryfer, CC0).

    python3 -I tools/build_bass.py [instrument ...]

  flat_bass     Swagbass: flatwound strings on the neck pickup, the round thump of reggae, dub and kompa
                (p / f / fff)
  finger_bass   Growlybass: a roundwound Squier Jazz Bass, brighter and punchier for Afrobeat and soca (p / f / ff)
  finger_bass_short   Growlybass staccato notes, for tight, muted lines
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_horns import files, layer  # noqa: E402
from prep import LIB, build_instrument, folder_zones, write_credits  # noqa: E402

RAW = os.path.join(LIB, "raw")
OUT = os.path.join(LIB, "library")
NOTE = r"^([a-g]b?\d)_"
BASS = dict(fade_s=0.3, floor_db=-55.0, norm="rms", rms_db=-17.0, mono=True, even_keys=6.0)

BUILDS = {
    "flat_bass": ("BASS", "karoryfer_swag",
                  lambda: folder_zones(files(RAW, "Swagbass", "notes", "*_rr1.wav"), NOTE,
                                       layer(r"_(p|f|fff)_rr", ["p", "f", "fff"]), max_len=3.0, fine_tune=True),
                  BASS),
    "finger_bass": ("BASS", "karoryfer_growly",
                    lambda: folder_zones(files(RAW, "Growlybass", "sustain", "*_rr1.wav"), NOTE,
                                         layer(r"_(p|f|ff)_rr", ["p", "f", "ff"]), max_len=3.0, fine_tune=True),
                    BASS),
    "finger_bass_short": ("BASS", "karoryfer_growly",
                          lambda: folder_zones(files(RAW, "Growlybass", "staccato", "*_rr1.wav"), NOTE,
                                               lambda p: 0, max_len=0.6, fine_tune=True),
                          dict(BASS, fade_s=0.06)),
}


if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDS)
    for name in names:
        cat, src, zf, kw = BUILDS[name]
        k = build_instrument(name, cat, src, zf(), OUT, **kw)
        roots = sorted({z["root"] for z in k["zones"]})
        print(f"{name:18s} zones={len(k['zones']):3d} layers={len({z['lovel'] for z in k['zones']})} "
              f"roots={roots[0]}-{roots[-1]} ({len(roots)}) {k['total_bytes'] / 1e6:5.1f} MB")
    write_credits(OUT)
