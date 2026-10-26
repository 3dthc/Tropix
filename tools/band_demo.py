#!/usr/bin/env python3
"""Genre demos for the Tropix keys, basses, percussion kits and mallets, all played from the prepared library
(plus the log drum engine for amapiano).

    python3 -I tools/band_demo.py [outdir] [name ...]

  band_amapiano        Kawai grand chords, log drum, kalimba, shakers and congas; 113 BPM, F minor
  band_kompa_keys      FM keys and CP80 comping, flatwound bass, congas and cowbell; 122 BPM, C major
  band_reggae_keys     upright piano skank, Pianet bubble, flatwound bass, one-drop; 76 BPM, A minor
  band_afrobeats       Wurlitzer chords, finger bass, balafon and marimba riff, congas and shaker; 104 BPM, D minor
  perc_kits            the island percussion kit, then the bobobo and cajon kit, each in a groove
  mallets_thumb        kalimba, mbira, balafon, marimba and vibraphone, one phrase each
Every part is original, written for these demos.
"""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logdrum import log_drum  # noqa: E402
from logdrum_demo import kick, rim  # noqa: E402
from pan_demo import finish, place  # noqa: E402
from sampler import SR, note  # noqa: E402

RNG = np.random.default_rng(9)
# island_perc keys
TUMBA, TUMBA_M, CONGA, CONGA_M, QUINTO, QUINTO_M = 36, 37, 38, 39, 40, 41
BONGO_L, BONGO_LM, BONGO_H, BONGO_HM = 42, 43, 44, 45
SHAKE_D, SHAKE_U, SHAKE_SLAP, LSHAKE, LSHAKE_SH, CAB, CAB_RUB = 46, 47, 48, 49, 50, 51, 52
AGOGO_H, AGOGO_L, BELL, BELL_M, BELL2, CLAVES, WOOD, GUIRO, GUIRO_L = 53, 54, 55, 56, 57, 58, 59, 60, 61


def hitp(buf, t, inst, key, vel, dur=0.6, gain=1.0, pan=0.0):
    y = note(inst, key, np.clip(vel + RNG.uniform(-0.05, 0.05), 0.05, 1), dur, release=0.05) * gain
    y = y * np.array([1 - max(0, pan), 1 + min(0, pan)])
    place(buf, y, max(0.0, t + RNG.normal(0, 0.004)))


def play(buf, t, inst, m, vel, dur, gain=1.0, pan=0.0, release=0.15):
    y = note(inst, m, np.clip(vel + RNG.uniform(-0.04, 0.04), 0.05, 1), dur, release=release,
             cents=RNG.normal(0, 1.0)) * gain
    y = y * np.array([1 - max(0, pan), 1 + min(0, pan)])
    place(buf, y, max(0.0, t + RNG.normal(0, 0.003)))


def chord(buf, t, inst, notes, vel, dur, gain=1.0, spread=0.004, pan=0.0):
    for k, m in enumerate(notes):
        play(buf, t + k * spread, inst, m, vel * (1 - 0.03 * k), dur, gain, pan)


def shaker16(buf, t0, b, gain=0.6, swing=0.012):
    for s in range(16):
        key = SHAKE_D if s % 2 == 0 else SHAKE_U
        hitp(buf, t0 + s * b / 4 + (swing if s % 2 else 0), "island_perc", key, 0.8 if s % 4 == 2 else 0.45, 0.2,
             gain)


def amapiano():
    bpm, bars = 113, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    chords = [[53, 56, 60, 63, 67], [49, 53, 56, 60, 63], [46, 49, 53, 56, 60], [48, 52, 55, 58, 63]]
    ld = [(0, 41, 0.95), (3, 41, 0.6), (6, 53, 0.75), (10, 48, 0.8), (14, 46, 0.7)]
    roots = [41, 37, 34, 36]
    for bar in range(bars):
        t0 = bar * 16 * b / 4
        ch = chords[bar % 4]
        for beat in range(4):
            place(buf, kick(RNG) * 0.55, t0 + beat * b)
        shaker16(buf, t0, b, 0.5)
        for s in (4, 12):
            hitp(buf, t0 + s * b / 4, "island_perc", CONGA_M, 0.6, 0.3, 0.8)
        hitp(buf, t0 + 7 * b / 4, "island_perc", CONGA, 0.55, 0.3, 0.7, pan=0.3)
        hitp(buf, t0 + 14 * b / 4, "island_perc", TUMBA, 0.6, 0.4, 0.7, pan=-0.3)
        # piano: the amapiano rhythm stab pattern, chords voiced with a 9th on top
        for s, d in ((2, 0.4), (6, 0.4), (10, 0.3), (13, 0.6)):
            chord(buf, t0 + s * b / 4, "grand_piano", ch, 0.55 if s != 13 else 0.62, d * b * 2, 0.8)
        root = roots[bar % 4]
        for s, m, v in ld:
            x = log_drum(root + (m - 41), v, "classic")
            place(buf, np.stack([x, x], 1) * 0.6, t0 + s * b / 4)
        if bar % 2 == 1:   # kalimba sprinkle
            for k, (s, m) in enumerate(((0, 72), (3, 75), (6, 79), (8, 77), (11, 75))):
                play(buf, t0 + s * b / 4, "kalimba", m, 0.6, b, 0.6, pan=0.4)
    return finish(buf)


def kompa_keys():
    bpm, bars = 122, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    prog = [(48, [64, 67, 72]), (53, [65, 69, 72]), (55, [62, 67, 71]), (48, [64, 67, 72])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in (0, 2):
            place(buf, kick(RNG) * 0.55, t0 + beat * b)
        for beat in range(4):
            hitp(buf, t0 + beat * b + b / 2, "island_perc", BELL, 0.7 if beat % 2 else 0.5, 0.2, 0.5)
            hitp(buf, t0 + beat * b, "island_perc", CONGA_M if beat % 2 == 0 else CONGA, 0.6, 0.3, 0.7)
        shaker16(buf, t0, b, 0.35, 0.0)
        for pos, iv, d in ((0, 0, 1.2), (1.5, 7, 0.4), (2.5, 0, 0.4), (3, 12, 0.4), (3.5, 7, 0.4)):
            play(buf, t0 + pos * b, "flat_bass", root - 12 + iv, 0.8, d * b)
        for pos in (0.5, 1.5, 2.5, 3.5):      # FM keys on the off-beats
            chord(buf, t0 + pos * b, "fm_keys", [m + 12 for m in ch], 0.6, 0.35 * b, 0.6, pan=0.3)
        for pos, d in ((0, 1.4), (2, 1.4)):    # CP80 sustained pads underneath
            chord(buf, t0 + pos * b, "cp80", ch, 0.5, d * b, 0.55, spread=0.01, pan=-0.3)
    return finish(buf)


def reggae_keys():
    bpm, bars = 76, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    prog = [(45, [57, 60, 64]), (50, [57, 62, 66])] * 4
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        place(buf, kick(RNG) * 0.8, t0 + 2 * b)
        place(buf, rim(RNG) * 1.2, t0 + 2 * b)
        for e in range(8):
            hitp(buf, t0 + e * b / 2 + (0.03 if e % 2 else 0), "island_perc", SHAKE_D if e % 2 == 0 else SHAKE_U,
                 0.5, 0.2, 0.4)
        for pos, iv, d in ((0, 0, 1.4), (1.5, 0, 0.4), (2, 7, 0.8), (3, 3, 0.4), (3.5, 5, 0.4)):
            play(buf, t0 + pos * b, "flat_bass", root - 12 + iv, 0.85, d * b)
        for beat in (1, 3):                    # piano skank on 2 and 4, short
            chord(buf, t0 + beat * b, "upright_piano", ch + [ch[0] + 12], 0.6, 0.18, 0.7, spread=0.002)
        for e in range(8):                     # Pianet "bubble": muted eighths, accent on the off-beat
            m = (ch[0] - 12) if e % 2 == 0 else ch[1]
            play(buf, t0 + e * b / 2, "pianet", m, 0.7 if e % 2 else 0.45, 0.12, 0.55, pan=-0.3, release=0.04)
    return finish(buf)


def afrobeats():
    bpm, bars = 104, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    prog = [(50, [57, 60, 64, 65]), (46, [57, 62, 65, 69]), (48, [55, 60, 64, 67]), (45, [55, 60, 64, 69])] * 2
    riff = [(0, 74), (0.75, 72), (1.5, 69), (2, 72), (2.75, 74), (3.5, 77)]
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for pos in (0, 1.5, 2.5):
            place(buf, kick(RNG) * 0.65, t0 + pos * b)
        place(buf, rim(RNG), t0 + 1 * b)
        place(buf, rim(RNG), t0 + 3 * b)
        shaker16(buf, t0, b, 0.45)
        for pos, key in ((0.5, CONGA_M), (0.75, CONGA), (1.75, QUINTO), (2.5, CONGA_M), (3.25, TUMBA), (3.75, CONGA)):
            hitp(buf, t0 + pos * b, "island_perc", key, 0.6, 0.3, 0.7, pan=0.2)
        for pos, iv, d in ((0, 0, 0.7), (0.75, 0, 0.25), (1.5, 7, 0.5), (2.5, 10, 0.4), (3, 12, 0.4), (3.5, 7, 0.4)):
            play(buf, t0 + pos * b, "finger_bass", root - 12 + iv, 0.75, d * b)
        for pos, d in ((0, 1.2), (1.5, 0.4), (2.5, 1.4)):
            chord(buf, t0 + pos * b, "wurlitzer", ch, 0.55, d * b, 0.6, spread=0.008, pan=-0.2)
        inst = "balafon" if bar < 4 else "marimba"
        for pos, m in riff:
            play(buf, t0 + pos * b, inst, m - (0 if inst == "balafon" else 12), 0.65, 0.4 * b, 0.6, pan=0.35)
    return finish(buf)


def perc_kits():
    bpm = 108
    b = 60 / bpm
    buf = np.zeros((int(SR * (16 * 4 * b + 4)), 2))
    for bar in range(8):                    # island kit: tumbao on congas, martillo on bongos, bells, guiro
        t0 = bar * 4 * b
        for pos, key, v in ((0, CONGA_M, 0.5), (1, CONGA, 0.65), (1.5, QUINTO, 0.7), (2, CONGA_M, 0.5),
                            (3, TUMBA, 0.75), (3.5, TUMBA, 0.7)):
            hitp(buf, t0 + pos * b, "island_perc", key, v, 0.4, pan=-0.2)
        for e in range(8):
            key = BONGO_H if e % 4 == 0 else (BONGO_HM if e % 2 else BONGO_L)
            hitp(buf, t0 + e * b / 2, "island_perc", key, 0.55, 0.25, 0.8, pan=0.3)
        for pos in (0, 1, 1.5, 2.5, 3):
            hitp(buf, t0 + pos * b, "island_perc", AGOGO_H if pos in (0, 2.5) else AGOGO_L, 0.6, 0.3, 0.6, pan=0.4)
        if bar >= 4:
            for beat in range(4):
                hitp(buf, t0 + beat * b, "island_perc", GUIRO, 0.6, 0.3, 0.5, pan=-0.4)
                hitp(buf, t0 + beat * b + b / 2, "island_perc", BELL, 0.6, 0.3, 0.5)
            for pos in (0, 1.5, 3):
                hitp(buf, t0 + pos * b, "island_perc", CLAVES, 0.7, 0.2, 0.6, pan=0.5)
    for bar in range(8, 16):                # west africa kit: bobobo bass and tenors, cajon, bell from the island kit
        t0 = bar * 4 * b
        for pos, key, v in ((0, 36, 0.8), (1.5, 36, 0.6), (2.5, 36, 0.75)):
            hitp(buf, t0 + pos * b, "west_africa", key, v, 0.6)
        for e in range(8):
            hitp(buf, t0 + e * b / 2, "west_africa", 38 if e % 2 == 0 else 39, 0.55 + 0.15 * (e % 4 == 3), 0.3,
                 pan=-0.25)
        for pos, key in ((0.5, 43), (1.25, 44), (2, 43), (2.75, 44), (3.5, 45)):
            hitp(buf, t0 + pos * b, "west_africa", key, 0.65, 0.3, pan=0.3)
        for pos, key in ((1, 50), (3, 50), (3.75, 49)):
            hitp(buf, t0 + pos * b, "west_africa", key, 0.7, 0.4)
        for pos in (0, 1, 2, 2.5, 3.5):     # 12/8-flavoured bell line
            hitp(buf, t0 + pos * b, "island_perc", AGOGO_H, 0.6, 0.3, 0.5, pan=0.4)
    return finish(buf)


def mallets_thumb():
    bpm = 100
    b = 60 / bpm
    phrase = [(0, 72), (0.5, 76), (1, 79), (1.5, 76), (2, 74), (2.5, 77), (3, 81), (4, 79), (5, 72)]
    insts = [("kalimba", 0), ("mbira", 0), ("balafon", 0), ("marimba", -12), ("vibraphone", -12)]
    span = 7 * b
    buf = np.zeros((int(SR * (span * len(insts) + 4)), 2))
    for k, (inst, tr) in enumerate(insts):
        for pos, m in phrase:
            play(buf, k * span + pos * b, inst, m + tr, 0.65, b * (1.5 if pos >= 4 else 0.6))
    return finish(buf)


JOBS = {"band_amapiano": amapiano, "band_kompa_keys": kompa_keys, "band_reggae_keys": reggae_keys,
        "band_afrobeats": afrobeats, "perc_kits": perc_kits, "mallets_thumb": mallets_thumb}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "docs", "demos")
    os.makedirs(out, exist_ok=True)
    for name in (sys.argv[2:] or JOBS):
        x = JOBS[name]()
        sf.write(os.path.join(out, name + ".wav"), x, SR, subtype="PCM_16")
        print(f"{name}: {len(x) / SR:.1f}s")
