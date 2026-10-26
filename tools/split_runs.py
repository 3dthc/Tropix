#!/usr/bin/env python3
"""Split University of Iowa MIS chromatic runs (one file per range, e.g. AltoSax.NoVib.mf.Db3B3.aiff) into one
file per note.

    python3 -I tools/split_runs.py <in_dir> <out_dir>

Notes in a run are separated by silence. The detector lowers or raises its silence threshold until it finds exactly
as many notes as the run's range holds, then checks each note's pitch against its expected name; a note more than
60 cents from its name is reported and left out (sax notes played softly up high run up to ~50 cents sharp; every zone is retuned later).
"""
import os
import re
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio import midi_name, name_to_midi, pitch_of, rms_env  # noqa: E402

RUN = re.compile(r"^(.+)\.([A-G]b?\d)([A-G]b?\d)\.aiff?$", re.I)


def segments(x, sr, thresh_db, min_gap=0.12, min_note=0.15, hop_s=0.005):
    """Note spans (sample indices) where the level stays above thresh_db re peak, bridging gaps < min_gap."""
    hop = int(sr * hop_s)
    env = rms_env(x, sr, 15)[::hop]
    on = env > env.max() * 10 ** (thresh_db / 20)
    edges = np.diff(np.concatenate([[0], on.astype(int), [0]]))
    starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
    segs = []
    for a, b in zip(starts, ends):
        if segs and (a - segs[-1][1]) * hop_s < min_gap:
            segs[-1] = (segs[-1][0], b)
        else:
            segs.append((a, b))
    return [(a * hop, b * hop) for a, b in segs if (b - a) * hop_s >= min_note]


def split(path, out_dir):
    m = RUN.match(os.path.basename(path))
    lo, hi = name_to_midi(m.group(2)), name_to_midi(m.group(3))
    want = hi - lo + 1
    x, sr = sf.read(path, dtype="float32")
    if x.ndim == 2:
        x = x.mean(axis=1)
    segs = None
    for th in np.arange(-50, -20, 1.0):
        s = segments(x, sr, th)
        if len(s) == want:
            segs = s
            break
    if segs is None:
        print(f"  !! {os.path.basename(path)}: could not find {want} notes")
        return 0
    os.makedirs(out_dir, exist_ok=True)
    ok = 0
    for k, (a, b) in enumerate(segs):
        note = lo + k
        pre, post = int(0.05 * sr), int(0.25 * sr)       # keep the breath before and the room after
        y = x[max(0, a - pre):min(len(x), b + post)]
        f = pitch_of(y, sr, guess_midi=note)
        c = None if f is None else 1200 * np.log2(f / (440 * 2 ** ((note - 69) / 12)))
        if c is None or abs(c) > 60:   # high pp sax notes can run ~50 cents sharp; zones are retuned anyway
            print(f"  !! {os.path.basename(path)} note {k + 1} expected {midi_name(note)}: {c}")
            continue
        name = f"{m.group(1)}.{midi_name(note).replace('#', 's')}.wav"
        sf.write(os.path.join(out_dir, name), y, sr, subtype="PCM_24")
        ok += 1
    return ok


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    for root, _, files in os.walk(src):
        for f in sorted(files):
            if RUN.match(f):
                rel = os.path.relpath(root, src)
                n = split(os.path.join(root, f), os.path.join(dst, rel))
                print(f"{rel}/{f}: {n} notes")
