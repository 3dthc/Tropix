#!/usr/bin/env python3
"""Build the Tropix keys multisamples.

    python3 -I tools/build_keys.py [instrument ...]

  grand_piano     VCSL Kawai grand, three dynamics (CC0): amapiano chords, kompa piano
  upright_piano   VCSL Yamaha upright, three dynamics (CC0): reggae and kompa skank piano
  wurlitzer       Greg Sullivan's Wurlitzer EP200 (CC BY 3.0): soft and hard layers
  cp80            Greg Sullivan's Yamaha CP80 electric grand (CC BY 3.0): three dynamics
  pianet          Greg Sullivan's Hohner Pianet T (CC BY 3.0): the clav-like reggae and Afrobeat comp
  fm_keys         VCSL TX81Z "FM Piano" (CC0): the bright 80s FM keys of kompa and zouk
Pianos are stored mono and cut at a few seconds (the plugin's release and reverb carry the tail), to fit the budget.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_horns import files, layer, rr1  # noqa: E402
from prep import LIB, build_instrument, folder_zones, load, note_to_midi, write_credits  # noqa: E402

RAW = os.path.join(LIB, "raw")
OUT = os.path.join(LIB, "library")
VZ = os.path.join(RAW, "VCSL", "Chordophones", "Zithers")
TX = os.path.join(RAW, "VCSL", "Electrophones", "TX81Z")
GS = os.path.join(RAW, "GregSullivan")

KEYS = dict(fade_s=0.5, floor_db=-55.0, norm="rms", rms_db=-17.0, mono=True, even_keys=6.0)


def wurli_zones():
    """The Wurlitzer set samples different notes at each dynamic. Two layers: soft takes mp (else pp), hard takes
    f (else ff), so every sampled note has both a soft and a hard sound."""
    by_note = {}
    for p in files(GS, "Wurlitzer EP200", "Samples", "*.flac"):
        m = re.match(r"([a-g]b?\d)(pp|mp|f|ff)\.flac$", os.path.basename(p))
        if m:
            by_note.setdefault(note_to_midi(m.group(1)), {})[m.group(2)] = p
    picks = []
    for n, d in by_note.items():
        for lay, pref in ((0, ("mp", "pp", "f")), (1, ("f", "ff", "mp"))):
            for dyn in pref:
                if dyn in d:
                    picks.append((d[dyn], lay))
                    break
    chosen = {p: lay for p, lay in picks}
    return folder_zones(sorted(chosen), r"^([a-g]b?\d)(?:pp|mp|f|ff)\.flac$", lambda p: chosen[p],
                        max_len=3.5, fine_tune=True)


BUILDS = {
    "grand_piano": ("KEYS", "vcsl",
                    lambda: folder_zones(rr1(files(VZ, "Grand Piano, Kawai", "Sustains", "*.wav")),
                                         r"_sus_([A-G]#?-?\d)_v", layer(r"_v(\d)_", ["2", "3", "4"]),
                                         max_len=3.5, fine_tune=True),
                    KEYS),
    "upright_piano": ("KEYS", "vcsl",
                      lambda: folder_zones(rr1(files(VZ, "Upright Piano, Yamaha", "Sustains", "*.wav")),
                                           r"_Sus_([A-G]#?-?\d)_vl", layer(r"_vl(\d)_", ["1", "2", "3"]),
                                           max_len=3.0, fine_tune=True),
                      KEYS),
    "wurlitzer": ("KEYS", "gregsullivan", wurli_zones, KEYS),
    "cp80": ("KEYS", "gregsullivan",
             lambda: folder_zones(files(GS, "CP80", "Samples", "*.flac"), r"-([A-G]#?\d)-",
                                  layer(r"-(MP|F|FF)\.flac$", ["MP", "F", "FF"]), max_len=3.5, fine_tune=True),
             KEYS),
    "pianet": ("KEYS", "gregsullivan",
               lambda: folder_zones(files(GS, "Pianet T", "Samples", "*.flac"), r"_([A-G]#?\d)_",
                                    layer(r"_(P|FF)\.flac$", ["P", "FF"]), max_len=2.5, fine_tune=True),
               KEYS),
    "fm_keys": ("KEYS", "vcsl",
                lambda: folder_zones(files(TX, "FM Piano", "*.wav"), r"_([A-G]#?-?\d)_vl",
                                     layer(r"_vl(\d)", ["1", "2", "3"]), max_len=3.0, fine_tune=True),
                KEYS),
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
