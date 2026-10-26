#!/usr/bin/env python3
"""Build the Tropix guitar multisamples.

    python3 -I tools/build_guitars.py [instrument ...]

  gretsch, gretsch_mute   Karoryfer "Black And Green Guitars": green Gretsch Anniversary hollow-body, played open
                          (p / mf / f) and palm-muted. Bright and round: kompa chorus lines, highlife.
  hofner, hofner_mute     the black Höfner Club from the same library: woodier, for reggae skank and palm-wine
                          electric lines.
  slack_key               Meta Open Sound steel-string acoustic (three velocity layers) for Hawaiian slack-key.
  palm_wine               Meta Open Sound nylon guitar (finger, then pick) for palm-wine and highlife acoustic.
All CC0. Notes are taken every whole tone (a guitar stretches a semitone either way cleanly), one round robin.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_horns import every, files, layer  # noqa: E402
from prep import LIB, build_instrument, folder_zones, note_to_midi, write_credits  # noqa: E402

RAW = os.path.join(LIB, "raw")
OUT = os.path.join(LIB, "library")
BG = os.path.join(RAW, "BlackAndGreen", "Samples")
META = os.path.join(RAW, "Meta", "systems", "instruments")
BG_NOTE = r"_([a-g]b?\d)_"
META_NOTE = r"_([A-G]s?\d)_\d+\.ogg$"
OPEN = {"LowE": 40, "A": 45, "D": 50, "G": 55, "B": 59, "HighE": 64}


def meta_pick(paths, fret_target=4):
    """Meta records every note on several strings. For each note and layer keep the string where it sits nearest
    the 4th fret: the most natural position for a player, avoiding both open strings and the high frets."""
    best = {}
    for p in paths:
        b = os.path.basename(p)
        s = re.search(r"_String(\w+?)_Vel", b).group(1)
        lay = re.search(r"_Vel(\d+)", b).group(1)
        m = note_to_midi(re.search(META_NOTE, b).group(1))
        fret = m - OPEN[s]
        score = abs(fret - fret_target) + (2 if fret == 0 else 0)
        k = (m, lay)
        if k not in best or score < best[k][0]:
            best[k] = (score, p)
    return sorted(p for _, p in best.values())


ONE_SHOT = dict(fade_s=0.4, floor_db=-55.0, norm="rms", rms_db=-17.0, mono=True, even_keys=8.0)

BUILDS = {
    "gretsch": ("GUITARS", "karoryfer_bg",
                lambda: folder_zones(every(files(BG, "green", "ord", "*_rr1.wav"), note_re=BG_NOTE), BG_NOTE,
                                     layer(r"_(p|mf|f)_rr", ["p", "mf", "f"]), max_len=4.0, fine_tune=True),
                ONE_SHOT),
    "gretsch_mute": ("GUITARS", "karoryfer_bg",
                     lambda: folder_zones(every(files(BG, "green", "stac", "*_rr1.wav"), note_re=BG_NOTE), BG_NOTE,
                                          lambda p: 0, max_len=0.8, fine_tune=True),
                     dict(ONE_SHOT, fade_s=0.08)),
    "hofner": ("GUITARS", "karoryfer_bg",
               lambda: folder_zones(every(files(BG, "black", "ord", "*_rr1.wav"), note_re=BG_NOTE), BG_NOTE,
                                    layer(r"_(p|mf|f)_rr", ["p", "mf", "f"]), max_len=4.0, fine_tune=True),
               ONE_SHOT),
    "hofner_mute": ("GUITARS", "karoryfer_bg",
                    lambda: folder_zones(every(files(BG, "black", "stac", "*_rr1.wav"), note_re=BG_NOTE), BG_NOTE,
                                         lambda p: 0, max_len=0.8, fine_tune=True),
                    dict(ONE_SHOT, fade_s=0.08)),
    "slack_key": ("GUITARS", "metaopensound",
                  lambda: folder_zones(every(meta_pick(files(META, "meta-steel-guitar", "ogg", "*.ogg")),
                                             note_re=META_NOTE), META_NOTE,
                                       layer(r"_Vel(\d+)_", ["01", "02", "03"]), max_len=4.5, fine_tune=True),
                  ONE_SHOT),
    "palm_wine": ("GUITARS", "metaopensound",
                  lambda: folder_zones(every(meta_pick(files(META, "meta-nylon-guitar", "ogg", "*.ogg")),
                                             note_re=META_NOTE), META_NOTE,
                                       layer(r"_Vel(\d+)", ["01", "02", "03"]), max_len=4.0, fine_tune=True),
                  ONE_SHOT),
}


if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDS)
    for name in names:
        cat, src, zf, kw = BUILDS[name]
        k = build_instrument(name, cat, src, zf(), OUT, **kw)
        layers = sorted({z["lovel"] for z in k["zones"]})
        roots = sorted({z["root"] for z in k["zones"]})
        print(f"{name:14s} zones={len(k['zones']):3d} layers={len(layers)} roots={roots[0]}-{roots[-1]} "
              f"({len(roots)}) {k['total_bytes'] / 1e6:5.1f} MB")
    write_credits(OUT)
