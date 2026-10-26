#!/usr/bin/env python3
"""Build the Tropix horn multisamples from VSCO 2 CE (trumpet, trombone) and VCSL (tenor sax, saxello).

    python3 -I tools/build_horns.py [instrument ...]

Raw sources are expected under raw/ (raw/VSCO-2-CE, raw/VCSL). Every zone is tuned to equal temperament from its
measured pitch, sustains get a crossfaded loop in their steady part, and dynamics stay real recordings (a soft layer
is a soft performance, never a loud one turned down).
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prep import LIB, build_instrument, folder_zones, write_credits  # noqa: E402

RAW = os.path.join(LIB, "raw")
OUT = os.path.join(LIB, "library")
VSCO = os.path.join(RAW, "VSCO-2-CE", "Brass")
SAX = os.path.join(RAW, "VCSL", "Aerophones", "Reed Aerophones")
IOWA = os.path.join(RAW, "IowaMIS-notes")
IOWA_NOTE = r"\.([A-G]s?\d)\.wav$"
DYN = ["pp", "mf", "ff"]
NOTE = r"_([A-G]#?\d)_"


def files(*parts):
    return sorted(glob.glob(os.path.join(*parts)))


def layer(pattern, keep):
    """Velocity label from a file name: the first group of `pattern`, kept only if in `keep` (in order)."""
    def key(p):
        m = re.search(pattern, os.path.basename(p))
        if not m or m.group(1) not in keep:
            return None
        return keep.index(m.group(1))
    return key


def rr1(paths):
    """Keep one round robin per note/dynamic (the first); others are alternates for a later RR feature."""
    seen, out = set(), []
    for p in paths:
        k = re.sub(r"_r[r]?\d+", "", os.path.basename(p))
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


# Known-bad takes found in the survey (an overblown note that sounds a fifth above its name).
SKIP = {"BrettTenor_NV_Main_D2_vl3_rr1.wav", "BrettTenor_Staccato_Main_D2_vl2_rr4.wav"}


def every(paths, step=2, base=0, note_re=None):
    """Keep every `step`-th semitone (by MIDI number), so a chromatic set becomes whole-tone; horns stretch a
    semitone either way without sounding pitched."""
    from prep import note_to_midi
    out = []
    for p in paths:
        m = re.search(note_re or IOWA_NOTE, os.path.basename(p))
        if m and (note_to_midi(m.group(1)) - base) % step == 0:
            out.append(p)
    return out


def ok(paths):
    return [p for p in paths if os.path.basename(p) not in SKIP]


BUILDS = {
    # name: (category, source, zone builder, build_instrument kwargs)
    "trumpet": ("HORNS", "vsco2ce",
                lambda: folder_zones(files(VSCO, "Trumpet", "sus", "*.wav"), NOTE,
                                     layer(r"_v(\d)_", ["1", "3"]), max_len=4.5, fine_tune=True),
                dict(loop=True, loop_region=(0.3, 0.85))),
    "trumpet_vib": ("HORNS", "vsco2ce",
                    lambda: folder_zones(files(VSCO, "Trumpet", "susvib", "*.wav"), NOTE,
                                         layer(r"_v(\d)_", ["1", "2"]), max_len=4.5, fine_tune=True),
                    dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch")),
    "trumpet_stab": ("HORNS", "vsco2ce",
                     lambda: folder_zones(rr1(files(VSCO, "Trumpet", "stac", "*.wav")), NOTE,
                                          layer(r"_v(\d)_", ["1", "2", "3"]), max_len=1.2, fine_tune=True),
                     dict(fade_s=0.12, floor_db=-50.0)),
    "trumpet_harmon": ("HORNS", "vsco2ce",
                       lambda: folder_zones(files(VSCO, "Trumpet", "harmonM-sus", "*.wav"), NOTE,
                                            layer(r"_v(\d)_", ["1", "3"]), max_len=4.5, fine_tune=True),
                       dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch")),
    "trombone": ("HORNS", "vsco2ce",
                 lambda: folder_zones(files(VSCO, "OldTrombone", "Sustain", "*.wav"), NOTE,
                                      layer(r"_v(\d)_", ["1", "3", "5"]), max_len=4.5, fine_tune=True),
                 dict(loop=True, loop_region=(0.3, 0.85))),
    "trombone_stab": ("HORNS", "vsco2ce",
                      lambda: folder_zones(files(VSCO, "OldTrombone", "Short", "*.wav"), NOTE,
                                           layer(r"_v(\d)_", ["1", "2", "3"]), max_len=1.0, fine_tune=True),
                      dict(fade_s=0.1, floor_db=-50.0)),
    "trombone_fall": ("HORNS", "vsco2ce",
                      lambda: folder_zones(files(VSCO, "OldTrombone", "Fall", "*.wav"), NOTE,
                                           lambda p: 0, max_len=1.4, fine_tune=False),
                      dict(fade_s=0.1, floor_db=-50.0)),
    "tenor_sax": ("HORNS", "vcsl",
                  lambda: folder_zones(ok(files(SAX, "Tenor Saxophone", "Non-Vibrato", "*.wav")), NOTE,
                                       layer(r"_vl(\d)_", ["2", "3"]), max_len=4.5, fine_tune=True),
                  dict(loop=True, loop_region=(0.3, 0.85))),
    "tenor_sax_vib": ("HORNS", "vcsl",
                      lambda: folder_zones(files(SAX, "Tenor Saxophone", "Vibrato", "*.wav"), NOTE,
                                           lambda p: 0, max_len=4.5, fine_tune=True),
                      dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch")),
    "tenor_sax_stab": ("HORNS", "vcsl",
                       lambda: folder_zones(ok(rr1(files(SAX, "Tenor Saxophone", "Staccato", "*.wav"))), NOTE,
                                            layer(r"_vl(\d)_", ["1", "2"]), max_len=0.9, fine_tune=True),
                       dict(fade_s=0.08, floor_db=-50.0)),
    "saxello": ("HORNS", "vcsl",
                lambda: folder_zones(rr1(files(SAX, "Saxello", "Non-Vibrato", "*.wav")), NOTE,
                                     layer(r"_vl(\d)_", ["2", "3"]), max_len=4.5, fine_tune=True),
                dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch")),
    "saxello_vib": ("HORNS", "vcsl",
                    lambda: folder_zones(files(SAX, "Saxello", "Vibrato", "*.wav"), NOTE,
                                         lambda p: 0, max_len=4.5, fine_tune=True),
                    dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch")),
    # University of Iowa MIS (pre-2012 set): three real dynamics, straight and vibrato, mono
    "alto_sax": ("HORNS", "iowa",
                 lambda: folder_zones(every(files(IOWA, "Woodwinds", "altosaxophone", "AltoSax.NoVib.*.wav")), IOWA_NOTE,
                                      layer(r"\.(pp|mf|ff)\.", DYN), max_len=4.0, fine_tune=True),
                 dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch", mono=True, attack_db=-14.0)),
    "alto_sax_vib": ("HORNS", "iowa",
                     lambda: folder_zones(every(files(IOWA, "Woodwinds", "altosaxophone", "AltoSax.Vib.*.wav")), IOWA_NOTE,
                                          layer(r"\.(pp|mf|ff)\.", DYN), max_len=4.0, fine_tune=True),
                     dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch", mono=True, attack_db=-14.0)),
    "soprano_sax": ("HORNS", "iowa",
                    lambda: folder_zones(every(files(IOWA, "Woodwinds", "sopranosaxophone", "SopSax.NoVib.*.wav")), IOWA_NOTE,
                                         layer(r"\.(pp|mf|ff)\.", DYN), max_len=4.0, fine_tune=True),
                    dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch", mono=True, attack_db=-14.0)),
    "soprano_sax_vib": ("HORNS", "iowa",
                        lambda: folder_zones(every(files(IOWA, "Woodwinds", "sopranosaxophone", "SopSax.Vib.*.wav")), IOWA_NOTE,
                                             layer(r"\.(pp|mf|ff)\.", DYN), max_len=4.0, fine_tune=True),
                        dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch", mono=True, attack_db=-14.0)),
    "trumpet_bright": ("HORNS", "iowa",
                       lambda: folder_zones(every(files(IOWA, "Brass", "Bbtrumpet", "Trumpet.novib.*.wav")), IOWA_NOTE,
                                            layer(r"\.(pp|mf|ff)\.", DYN), max_len=4.0, fine_tune=True),
                       dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch", mono=True)),
    "trumpet_bright_vib": ("HORNS", "iowa",
                           lambda: folder_zones(every(files(IOWA, "Brass", "Bbtrumpet", "Trumpet.vib.*.wav")), IOWA_NOTE,
                                                layer(r"\.(pp|mf|ff)\.", DYN), max_len=4.0, fine_tune=True),
                           dict(loop=True, loop_region=(0.25, 0.92), loop_xfade=0.3, loop_mode="pitch", mono=True)),
}


if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDS)
    for name in names:
        cat, src, zf, kw = BUILDS[name]
        zones = zf()
        kw = dict(norm="rms", rms_db=-17.0, **kw)
        k = build_instrument(name, cat, src, zones, OUT, **kw)
        layers = sorted({z["lovel"] for z in k["zones"]})
        roots = sorted({z["root"] for z in k["zones"]})
        loops = [z["loop_score"] for z in k["zones"] if "loop_score" in z]
        print(f"{name:16s} zones={len(k['zones']):3d} layers={len(layers)} roots={roots[0]}-{roots[-1]} "
              f"({len(roots)}) {k['total_bytes'] / 1e6:5.1f} MB"
              + (f" loop score min {min(loops):.2f}" if loops else ""))
    write_credits(OUT)
