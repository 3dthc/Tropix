#!/usr/bin/env python3
"""Render listening demos for the Tropix guitars, played from the prepared library through tools/sampler.py.

    python3 -I tools/guitar_demo.py [outdir] [name ...]

  guitars_kompa       Gretsch through chorus: the bright picked kompa ostinato, 122 BPM in C
  guitars_highlife    two interlocking guitars (Gretsch lead, Hofner rhythm), 120 BPM in G
  guitars_reggae      Hofner muted skank on 2 and 4 with a one-drop, 76 BPM in A minor
  guitars_slack_key   steel-string acoustic fingerpicking with an alternating bass, 88 BPM in G
  guitars_palm_wine   nylon guitar palm-wine picking, 112 BPM in C
All parts are original, written for these demos. Drums and bass are simple stand-ins for context.
"""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from horn_demo import bass, cowbell  # noqa: E402
from logdrum_demo import kick, rim, shaker  # noqa: E402
from pan_demo import finish, place  # noqa: E402
from sampler import SR, note  # noqa: E402

RNG = np.random.default_rng(5)


def chorus(x, depth_ms=2.5, rate=0.8, delay_ms=14.0, mix=0.45):
    """Stereo chorus: two modulated delay taps in opposite phase, one per side."""
    n = len(x)
    t = np.arange(n) / SR
    out = np.copy(x)
    for c, ph in ((0, 0.0), (1, np.pi)):
        d = (delay_ms + depth_ms * np.sin(2 * np.pi * rate * t + ph)) * SR / 1000
        pos = np.arange(n) - d
        i = np.clip(pos.astype(int), 0, n - 2)
        f = pos - i
        src = x[:, c]
        out[:, c] = (1 - mix) * src + mix * (src[i] * (1 - f) + src[i + 1] * f) * (pos >= 0)
    return out


def pluck(buf, t, inst, m, vel, dur, pan=0.0, cents=0.0):
    y = note(inst, m, vel, dur, release=0.08, cents=cents + RNG.normal(0, 1.5))
    y = y * np.array([1 - max(0, pan), 1 + min(0, pan)])
    place(buf, y, max(0.0, t + RNG.normal(0, 0.003)))


def strum(buf, t, inst, notes, vel, dur, up=False, spread=0.012, pan=0.0):
    """Down-strum low to high (up-strum high to low, a little softer), each string a few ms apart."""
    order = sorted(notes, reverse=up)
    for k, m in enumerate(order):
        v = vel * (0.85 if up else 1.0) * (1 - 0.04 * k)
        pluck(buf, t + k * spread * RNG.uniform(0.8, 1.2), inst, m, v, dur, pan)


def drums_kompa(buf, t0, b):
    for beat in (0, 2):
        place(buf, kick(RNG) * 0.6, t0 + beat * b)
    for e in range(8):
        place(buf, shaker(0.8 if e % 2 else 0.45, RNG), t0 + e * b / 2)
    for beat in range(4):
        place(buf, cowbell() * (1.0 if beat in (1, 3) else 0.6), t0 + beat * b + b / 2)


def kompa():
    bpm, bars = 122, 8
    b = 60 / bpm
    gt = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    bg = np.zeros_like(gt)
    prog = [("C", 48, [64, 67, 72, 76]), ("F", 53, [65, 69, 72, 77]), ("G", 55, [62, 67, 71, 74]),
            ("C", 48, [64, 67, 72, 76])] * 2
    for bar, (_, root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        drums_kompa(bg, t0, b)
        for pos, iv, d in ((0, 0, 1.2), (1.5, 7, 0.4), (2.5, 0, 0.4), (3, 12, 0.4), (3.5, 7, 0.4)):
            place(bg, bass(root - 12 + iv, d * b), t0 + pos * b)
        # 16th-note ostinato: chord tones picked in a rolling pattern, muted ghost notes between accents
        seq = [ch[0], ch[2], ch[1], ch[3], ch[2], ch[1], ch[3], ch[2]] * 2
        for s in range(16):
            m = seq[s]
            if s in (3, 7, 11, 15):
                pluck(gt, t0 + s * b / 4, "gretsch_mute", m - 12, 0.55, 0.12)
            else:
                acc = 0.75 if s % 4 == 0 else 0.55
                pluck(gt, t0 + s * b / 4, "gretsch", m, acc, b / 4 * 1.6)
    return finish(chorus(gt) * 0.9 + bg)


def highlife():
    bpm, bars = 120, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    prog = [("G", 43, [55, 59, 62]), ("C", 48, [55, 60, 64]), ("D", 50, [54, 57, 62]), ("G", 43, [55, 59, 62])] * 2
    lead = [  # interlocking lead: thirds and sixths, offbeat entries
        [(0.5, 71), (1, 74), (1.5, 71), (2.5, 67), (3, 71), (3.5, 74)],
        [(0.5, 72), (1, 76), (1.5, 72), (2.5, 67), (3, 72), (3.5, 76)],
        [(0.5, 74), (1, 78), (1.5, 74), (2.5, 69), (3, 72), (3.5, 74)],
        [(0.5, 71), (1, 74), (1.5, 79), (2, 78), (2.5, 74), (3.5, 71)],
    ]
    for bar, (_, root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * (0.6 if beat in (0, 2) else 0.3), t0 + beat * b)
            place(buf, shaker(0.7, RNG), t0 + beat * b + b / 2)
        place(buf, rim(RNG), t0 + 1.5 * b)
        place(buf, rim(RNG), t0 + 3 * b)
        for pos, iv, d in ((0, 0, 0.9), (1, 7, 0.4), (1.5, 12, 0.4), (2.5, 7, 0.4), (3, 0, 0.9)):
            place(buf, bass(root + iv, d * b, 0.7), t0 + pos * b)
        # rhythm (Hofner): short chord chops on the off-beats, slightly left
        for pos in (0.5, 1.5, 2.5, 3.5):
            strum(buf, t0 + pos * b, "hofner_mute", ch, 0.7, 0.2, up=(pos % 1 == 0.5 and pos > 2), pan=-0.3)
        for pos, m in lead[bar % 4]:
            pluck(buf, t0 + pos * b, "gretsch", m, 0.7, b * 0.6, pan=0.3)
    return finish(buf)


def reggae():
    bpm, bars = 76, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    prog = [("Am", 45, [57, 60, 64, 69]), ("D", 50, [57, 62, 66, 69])] * 4
    for bar, (_, root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        place(buf, kick(RNG) * 0.8, t0 + 2 * b)       # one drop: kick and rim together on 3
        place(buf, rim(RNG) * 1.3, t0 + 2 * b)
        for e in range(8):
            place(buf, shaker(0.6 if e % 2 else 0.3, RNG), t0 + e * b / 2 + (0.03 if e % 2 else 0))
        for pos, iv, d in ((0, 0, 1.4), (1.5, 0, 0.4), (2, 7, 0.8), (3, 3, 0.4), (3.5, 5, 0.4)):
            place(buf, bass(root - 12 + iv, d * b, 0.85), t0 + pos * b)
        for beat in (1, 3):   # the skank: a quick, choked up-strum on 2 and 4
            strum(buf, t0 + beat * b, "hofner_mute", ch, 0.75, 0.16, up=True, spread=0.006)
            strum(buf, t0 + beat * b, "hofner", ch, 0.35, 0.09, up=True, spread=0.006)
    return finish(buf)


def slack_key():
    bpm, bars = 88, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    prog = [(43, [59, 62, 67]), (48, [60, 64, 67]), (43, [59, 62, 67]), (50, [57, 62, 66])] * 2
    tops = [[71, 74, 71, 69], [72, 76, 72, 71], [74, 71, 67, 71], [69, 66, 69, 74],
            [71, 74, 79, 78], [76, 72, 76, 79], [74, 71, 74, 79], [78, 74, 69, 67]]
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):   # alternating thumb bass: root and fifth
            pluck(buf, t0 + beat * b, "slack_key", root + (7 if beat % 2 else 0), 0.65, b * 1.2, pan=-0.15)
        for e in range(8):      # fingers: chord tones on the off-beats, melody on the beats
            if e % 2:
                pluck(buf, t0 + e * b / 2, "slack_key", ch[(e // 2) % 3], 0.45, b * 0.9, pan=0.15)
        for beat, m in enumerate(tops[bar]):
            pluck(buf, t0 + beat * b + 0.005, "slack_key", m, 0.75, b * 1.5, pan=0.2)
    pluck(buf, bars * 4 * b, "slack_key", 43, 0.7, 3.0)
    strum(buf, bars * 4 * b, "slack_key", [55, 59, 62, 67, 71], 0.6, 3.0, spread=0.03)
    return finish(buf)


def palm_wine():
    bpm, bars = 112, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    prog = [(48, [64, 67, 72]), (53, [65, 69, 72]), (55, [62, 67, 71]), (48, [64, 67, 72])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, shaker(0.6, RNG), t0 + beat * b + b / 2)
            place(buf, shaker(0.3, RNG), t0 + beat * b)
        place(buf, rim(RNG) * 0.7, t0 + 1.5 * b)
        place(buf, rim(RNG) * 0.7, t0 + 3 * b)
        # thumb on 1 and 3, fingers rolling the chord in a 3+3+2 pattern
        pluck(buf, t0, "palm_wine", root, 0.7, b * 1.8)
        pluck(buf, t0 + 2 * b, "palm_wine", root + 7, 0.65, b * 1.8)
        for k, pos in enumerate((0.5, 1, 1.5, 2.5, 3, 3.5)):
            pluck(buf, t0 + pos * b, "palm_wine", ch[k % 3] + (12 if bar % 4 == 3 and k > 3 else 0), 0.55, b)
    return finish(buf)


JOBS = {"guitars_kompa": kompa, "guitars_highlife": highlife, "guitars_reggae": reggae,
        "guitars_slack_key": slack_key, "guitars_palm_wine": palm_wine}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "docs", "demos")
    os.makedirs(out, exist_ok=True)
    for name in (sys.argv[2:] or JOBS):
        x = JOBS[name]()
        sf.write(os.path.join(out, name + ".wav"), x, SR, subtype="PCM_16")
        print(f"{name}: {len(x) / SR:.1f}s")
