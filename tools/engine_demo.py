#!/usr/bin/env python3
"""Demos for the rendered Tropix engines (tine piano, organ, steels, timbales, reeds, synths), played from the
library through the offline sampler like any other instrument.

    python3 -I tools/engine_demo.py [outdir] [name ...]
Every part is original, written for these demos.
"""
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from band_demo import CONGA, CONGA_M, SHAKE_D, SHAKE_U, TUMBA, chord, hitp, play, shaker16  # noqa: E402
from logdrum_demo import kick, rim  # noqa: E402
from organ import rotary  # noqa: E402
from pan_demo import finish, place  # noqa: E402
from sampler import SR, note, vibrato  # noqa: E402

RNG = np.random.default_rng(21)


def tremolo(x, rate=4.2, depth=0.5):
    """Suitcase-style stereo tremolo: the signal pans gently between the speakers."""
    t = np.arange(len(x)) / SR
    l = 1 - depth / 2 + depth / 2 * np.sin(2 * np.pi * rate * t)
    r = 1 - depth / 2 - depth / 2 * np.sin(2 * np.pi * rate * t)
    return np.stack([x[:, 0] * l, x[:, 1] * r], 1)


def tine_piano():
    bpm, bars = 84, 8
    b = 60 / bpm
    keys = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    rest = np.zeros_like(keys)
    prog = [(38, [53, 57, 60, 64]), (43, [53, 57, 59, 64]), (36, [52, 55, 59, 62]), (45, [52, 55, 60, 61])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        hard = bar >= 4
        for beat in range(4):
            place(rest, kick(RNG) * (0.5 if beat in (0, 2) else 0.0), t0 + beat * b)
            if beat in (1, 3):
                place(rest, rim(RNG) * 0.8, t0 + beat * b)
        shaker16(rest, t0, b, 0.3)
        play(rest, t0, "finger_bass", root - 12 + 12 * (root < 40), 0.7, 2.5 * b)
        play(rest, t0 + 2.5 * b, "finger_bass", root - 5, 0.6, 1.2 * b)
        v = 0.85 if hard else 0.45
        chord(keys, t0, "tine_piano", ch, v, 1.8 * b, spread=0.012)
        chord(keys, t0 + 2.5 * b, "tine_piano", ch, v - 0.1, 1.2 * b, spread=0.01)
        top = [72, 74, 76, 74][bar % 4] + (5 if hard else 0)
        play(keys, t0 + 1.5 * b, "tine_piano", top, v + 0.05, 0.9 * b)
        play(keys, t0 + 3.5 * b, "tine_piano", top - 3, v, 0.5 * b)
    return finish(tremolo(keys) + rest)


def reggae_organ():
    bpm, bars = 74, 8
    b = 60 / bpm
    org = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    rest = np.zeros_like(org)
    prog = [(45, [57, 60, 64]), (50, [57, 62, 66]), (52, [56, 59, 64]), (45, [57, 60, 64])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        place(rest, kick(RNG) * 0.85, t0 + 2 * b)
        place(rest, rim(RNG) * 1.2, t0 + 2 * b)
        for e in range(8):
            hitp(rest, t0 + e * b / 2 + (0.03 if e % 2 else 0), "island_perc", SHAKE_D if e % 2 == 0 else SHAKE_U,
                 0.45, 0.2, 0.4)
        for pos, iv, d in ((0, 0, 1.4), (1.5, 0, 0.4), (2, 7, 0.8), (3, 3, 0.4), (3.5, 5, 0.4)):
            play(rest, t0 + pos * b, "flat_bass", root - 12 + iv, 0.85, d * b)
        for beat in (1, 3):   # guitar-style skank chord on the organ's percussion voice
            chord(org, t0 + beat * b, "organ_perc", [m + 12 for m in ch], 0.8, 0.22, 0.5)
        # the bubble: left hand on the off-beat eighths, right hand chord stabs in between, beat 1 left empty
        for e in range(1, 8):
            if e % 2:
                play(org, t0 + e * b / 2, "organ_bubble", ch[0] - 12, 0.7, 0.18, 0.7, release=0.03)
            else:
                chord(org, t0 + e * b / 2 + 0.01, "organ_bubble", ch, 0.7, 0.16, 0.55)
    return finish(rotary(org.mean(1), "slow") + rest)


def glide_path(points, glide=0.12):
    """Pitch path for a steel bar: points (time s, semitones from the first note); each move glides over `glide`
    seconds with an ease-in-out, the way a bar slides between positions."""
    def f(t):
        y = np.full_like(t, float(points[0][1]))
        for (t0, s0), (t1, s1) in zip(points, points[1:]):
            u = np.clip((t - t1) / glide, 0, 1)
            y = np.where(t >= t1, s0 + (s1 - s0) * (0.5 - 0.5 * np.cos(np.pi * u)), y)
        return y
    return f


def steel_phrase(buf, t, inst, start, moves, vel, dur, vib=True, gain=1.0, glide=0.12, pan=0.0):
    """One bar stroke: a held note whose pitch follows `moves` ((time from stroke start, semitones from start))."""
    bends = [glide_path([(0.0, 0)] + moves, glide)]
    if vib:
        bends.append(vibrato(0.35, 5.2, 14, 0.3))
    y = note(inst, start, vel, dur, release=0.35, bends=bends, cents=RNG.normal(0, 2)) * gain
    y = y * np.array([1 - max(0, pan), 1 + min(0, pan)])
    place(buf, y, t)


def juju_steel():
    bpm, bars = 116, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    prog = [(43, [55, 59, 62]), (48, [55, 60, 64]), (50, [54, 57, 62]), (43, [55, 59, 62])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * (0.55 if beat in (0, 2) else 0.25), t0 + beat * b)
        shaker16(buf, t0, b, 0.35)
        for pos, key in ((0.5, CONGA_M), (1, CONGA), (2.5, CONGA_M), (3, TUMBA), (3.5, CONGA)):
            hitp(buf, t0 + pos * b, "island_perc", key, 0.55, 0.3, 0.6, pan=-0.3)
        for pos, iv, d in ((0, 0, 0.9), (1.5, 7, 0.4), (2, 12, 0.4), (3, 7, 0.9)):
            play(buf, t0 + pos * b, "finger_bass", root - 12 + iv, 0.7, d * b)
        for pos in (0.5, 1.5, 2.5, 3.5):
            for k, m in enumerate(ch):
                play(buf, t0 + pos * b + 0.008 * k, "hofner_mute", m, 0.55, 0.15, 0.6, pan=0.25)
    # the steel: swells and glides over the top, two-bar phrases
    lines = [
        (0, 71, [(0.9, 3), (1.6, 5), (2.4, 3)], 3.4), (8, 72, [(0.6, 4), (1.4, 7), (2.2, 4)], 3.4),
        (16, 74, [(0.5, 2), (1.0, 4), (1.8, 2), (2.4, 0)], 3.6), (24, 79, [(0.8, -1), (1.6, -3), (2.6, -8)], 3.6),
    ]
    for beat, start, moves, dur in lines:
        steel_phrase(buf, beat * b, "pedal_steel", start, moves, 0.75, dur, pan=0.1)
        steel_phrase(buf, beat * b, "pedal_steel", start - 4, [(tm, s) for tm, s in moves], 0.6, dur, gain=0.6,
                     pan=0.1)   # a pedal steel plays in harmony: a third below, sliding with it
    return finish(buf)


def hawaiian_steel():
    bpm, bars = 92, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    prog = [(43, [55, 59, 62, 67]), (48, [55, 60, 64, 67]), (50, [54, 57, 60, 62]), (43, [55, 59, 62, 67])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):   # slack-key style accompaniment: bass on the beat, chord on the off-beat
            play(buf, t0 + beat * b, "slack_key", root + (7 if beat % 2 else 0), 0.55, b, 0.7, pan=-0.2)
            for k, m in enumerate(ch[:3]):
                play(buf, t0 + beat * b + b / 2 + 0.01 * k, "slack_key", m, 0.4, b * 0.4, 0.55, pan=-0.2)
    lines = [
        (0, 69, [(0.25, 2), (1.3, 0), (2.0, -2)], 3.0), (4, 74, [(0.9, 2), (1.8, 4)], 2.8),
        (8, 78, [(0.3, 2), (1.2, 0), (2.0, -4)], 3.0), (12, 74, [(1.0, -2), (2.0, -5)], 3.4),
        (16, 67, [(0.2, 4), (0.9, 7), (1.8, 12)], 2.8), (20, 79, [(0.9, -2), (1.7, -5)], 2.8),
        (24, 81, [(0.4, -2), (1.0, -3), (1.8, -7)], 3.0), (28, 74, [(0.6, 5), (1.4, 7), (2.4, -5)], 3.8),
    ]
    for beat, start, moves, dur in lines:
        steel_phrase(buf, beat * b, "lap_steel", start - 12 * 0, [(0.0, -2)] + moves, 0.75, dur, glide=0.18,
                     pan=0.15)
    return finish(buf)


def delay(x, secs, fb=0.45, mix=0.4, tone=3000.0):
    """Dub tape echo: repeats darken as they fade, the right side a touch later."""
    from scipy.signal import butter, sosfilt
    n = len(x)
    out = np.copy(x)
    d = int(secs * SR)
    tap = np.copy(x)
    g = mix
    k = 1
    while g > 0.02 and k * d < n:
        tap = sosfilt(butter(1, tone, "low", fs=SR, output="sos"), tap, axis=0)
        shift = k * d
        out[shift:, 0] += g * tap[: n - shift, 0]
        s2 = min(n, shift + int(0.012 * SR))
        out[s2:, 1] += g * tap[: n - s2, 1]
        g *= fb
        k += 1
    return out


def timbales_ipu():
    bpm = 104
    b = 60 / bpm
    buf = np.zeros((int(SR * (16 * 4 * b + 4)), 2))
    for bar in range(8):                       # cascara on the paila, hembra and macho answers, a rimshot fill
        t0 = bar * 4 * b
        for pos in (0, 0.5, 1, 1.75, 2, 2.5, 3.25, 3.5):
            hitp(buf, t0 + pos * b, "timbales", 42, 0.65 if pos in (0, 2) else 0.5, 0.3, 0.8, pan=0.2)
        hitp(buf, t0 + 1 * b, "timbales", 38, 0.5, 0.3, 0.7)
        hitp(buf, t0 + 3 * b, "timbales", 36, 0.75, 0.5, 0.9, pan=-0.2)
        for pos, key in ((0, CONGA_M), (1, CONGA), (2, CONGA_M), (3, TUMBA), (3.5, TUMBA)):
            hitp(buf, t0 + pos * b, "island_perc", key, 0.55, 0.3, 0.6, pan=-0.3)
        if bar % 4 == 3:
            for k, pos in enumerate((2, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5)):
                hitp(buf, t0 + pos * b, "timbales", 40 if k % 2 else 37, 0.6 + 0.05 * k, 0.4, 0.9,
                     pan=0.25 if k % 2 else -0.25)
    for bar in range(8, 16):                   # ipu: heel on the beat, tips between, a slap to turn the phrase
        t0 = bar * 4 * b
        for pos, key, v in ((0, 36, 0.9), (1, 37, 0.6), (1.5, 37, 0.5), (2, 36, 0.8), (3, 37, 0.6), (3.5, 38, 0.7)):
            hitp(buf, t0 + pos * b, "ipu", key, v, 0.6)
        for e in range(8):
            hitp(buf, t0 + e * b / 2, "island_perc", 49 if e % 2 == 0 else 50, 0.45, 0.2, 0.45, pan=0.35)
    return finish(buf)


def melodica_dub():
    bpm, bars = 72, 8
    b = 60 / bpm
    lead = np.zeros((int(SR * (bars * 4 * b + 6)), 2))
    rest = np.zeros_like(lead)
    prog = [(45, [57, 60, 64]), (43, [55, 59, 62]), (41, [57, 60, 65]), (40, [56, 59, 64])] * 2
    for bar, (root, ch) in enumerate(prog):
        t0 = bar * 4 * b
        place(rest, kick(RNG) * 0.85, t0 + 2 * b)
        place(rest, rim(RNG) * 1.1, t0 + 2 * b)
        for pos, iv, d in ((0, 0, 1.4), (1.5, 0, 0.4), (2, 7, 0.8), (3, 5, 0.9)):
            play(rest, t0 + pos * b, "flat_bass", root - 12 + iv, 0.85, d * b)
        for beat in (1, 3):
            chord(rest, t0 + beat * b, "organ_perc", [m + 12 for m in ch], 0.75, 0.2, 0.4)
    line = [(0.5, 69, 1.5), (2, 72, 0.5), (2.5, 74, 1.5), (4.5, 76, 1.0), (5.5, 74, 0.5), (6, 71, 2.0),
            (8.5, 69, 1.0), (9.5, 72, 1.0), (10.5, 69, 1.5), (12, 64, 3.5),
            (16.5, 76, 1.5), (18, 79, 0.5), (18.5, 76, 1.5), (20.5, 74, 1.0), (21.5, 71, 1.5),
            (24.5, 72, 1.0), (25.5, 71, 0.5), (26, 69, 1.0), (27, 68, 1.0), (28, 69, 3.5)]
    for beat, m, d in line:
        inst = "melodica" if beat < 16 else "harmonica_vib"
        y = note(inst, m, 0.75, d * b * 0.95, release=0.12, bends=[vibrato(0.4, 5.0, 10)] if d > 1.2 else [])
        place(lead, y * 0.8, beat * b)
    return finish(delay(lead, 0.75 * b, 0.5, 0.35) + rest)


def synths_soca():
    bpm, bars = 156, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 4)), 2))
    chords = {"A": [57, 61, 64, 69], "D": [57, 62, 66, 69], "E": [56, 59, 64, 68], "F#m": [57, 61, 66, 69]}
    prog = ["A", "D", "E", "A", "F#m", "D", "E", "A"]
    roots = {"A": 33, "D": 38, "E": 40, "F#m": 42}
    lead = [(0, 76), (1, 78), (1.5, 76), (2.5, 73), (3, 76), (4, 81), (5.5, 80), (6, 78), (6.5, 76), (7, 73)]
    for bar, ch in enumerate(prog):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * 0.85, t0 + beat * b)
            hitp(buf, t0 + beat * b + b / 2, "island_perc", 48, 0.7, 0.2, 0.6)
        place(buf, rim(RNG) * 1.2, t0 + 1 * b)
        place(buf, rim(RNG) * 1.2, t0 + 3 * b)
        for pos in (0, 0.75, 1.5, 2, 2.75, 3.5):
            play(buf, t0 + pos * b, "sub_bass", roots[ch], 0.8, 0.3 * b, 0.9, release=0.05)
        hits = [(0.5, 0.4), (1.5, 0.4), (2.5, 0.4), (3, 0.9)] if bar % 2 == 0 else [(0, 0.4), (0.75, 0.4), (1.5, 0.4), (2.5, 1.2)]
        for pos, d in hits:
            chord(buf, t0 + pos * b, "soca_brass", [m + 12 for m in chords[ch]], 0.85, d * b, 0.45, spread=0.0)
        if bar >= 4:
            for beat, m in lead:
                if int(beat // 4) == bar % 2:
                    play(buf, t0 + (beat % 4) * b, "soca_lead", m, 0.8, 0.45 * b, 0.55, pan=0.1)
    return finish(buf)


def synths_amapiano():
    from logdrum import log_drum
    bpm, bars = 112, 8
    b = 60 / bpm
    buf = np.zeros((int(SR * (bars * 4 * b + 5)), 2))
    chords = [[53, 56, 60, 63, 67], [49, 53, 56, 60, 63], [46, 49, 53, 56, 60], [48, 52, 55, 58, 63]]
    roots = [41, 37, 34, 36]
    bell = [(0.5, 79), (1.25, 77), (2, 75), (2.75, 72), (3.5, 75)]
    for bar in range(bars):
        t0 = bar * 4 * b
        for beat in range(4):
            place(buf, kick(RNG) * 0.55, t0 + beat * b)
        shaker16(buf, t0, b, 0.45)
        hitp(buf, t0 + 1.75 * b, "island_perc", CONGA, 0.55, 0.3, 0.6, pan=0.3)
        chord(buf, t0, "island_pad", chords[bar % 4], 0.6, 3.8 * b, 0.35, spread=0.0)
        for s16, m, v in ((0, 41, 0.95), (3, 41, 0.6), (6, 53, 0.75), (10, 48, 0.8), (14, 46, 0.7)):
            x = log_drum(roots[bar % 4] + (m - 41), v, "deep" if bar < 4 else "talking")
            place(buf, np.stack([x, x], 1) * 0.6, t0 + s16 * b / 4)
        for pos, m in bell:
            inst = "piano_pluck" if bar < 4 else "afro_pluck"
            play(buf, t0 + pos * b, inst, m, 0.65, 0.5 * b, 0.5, pan=0.35)
    return finish(buf)


JOBS = {"engines_tine_piano": tine_piano, "engines_reggae_organ": reggae_organ,
        "engines_juju_steel": juju_steel, "engines_hawaiian_steel": hawaiian_steel,
        "engines_timbales_ipu": timbales_ipu, "engines_melodica_dub": melodica_dub,
        "engines_synths_soca": synths_soca, "engines_synths_amapiano": synths_amapiano}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "docs", "demos")
    os.makedirs(out, exist_ok=True)
    for name in (sys.argv[2:] or JOBS):
        x = JOBS[name]()
        sf.write(os.path.join(out, name + ".wav"), x, SR, subtype="PCM_16")
        print(f"{name}: {len(x) / SR:.1f}s")
