"""Offline Tropix sampler: plays library/<instrument>/keymap.json the way the plugin engine will (zone choice by
key and velocity, per-zone tuning, looped sustains, release), plus the horn articulations rendered from the real
recordings: scoops into the note, falls and doits off it, and delayed vibrato on straight notes.

Used for listening demos and for checking the library before it is packed for the MPC.
"""
import json
import os

import numpy as np
import soundfile as sf

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "library")

_maps, _audio = {}, {}


def keymap(inst):
    if inst not in _maps:
        _maps[inst] = json.load(open(os.path.join(LIB, inst, "keymap.json")))
    return _maps[inst]


def audio(inst, fn):
    k = (inst, fn)
    if k not in _audio:
        x, sr = sf.read(os.path.join(LIB, inst, fn), dtype="float32", always_2d=True)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, axis=1)
        _audio[k] = (x, sr)
    return _audio[k]


def pick_zone(inst, m, vel):
    v = int(np.clip(round(vel * 127), 1, 127))
    zs = [z for z in keymap(inst)["zones"] if z["lokey"] <= m <= z["hikey"] and z["lovel"] <= v <= z["hivel"]]
    if not zs:  # outside the mapped range: nearest root at this velocity
        zs = [z for z in keymap(inst)["zones"] if z["lovel"] <= v <= z["hivel"]] or keymap(inst)["zones"]
        zs = [min(zs, key=lambda z: abs(z["root"] - m))]
    return zs[0]


def scoop(depth=-1.5, secs=0.09):
    """Bend up into the note from `depth` semitones."""
    return lambda t: np.where(t < secs, depth * (1 - t / secs) ** 2, 0.0)


def fall(at, depth=-7.0, secs=0.4):
    """Drop off the note starting at `at` seconds."""
    return lambda t: np.where(t > at, depth * np.clip((t - at) / secs, 0, 1) ** 2, 0.0)


def doit(at, depth=4.0, secs=0.25):
    return fall(at, depth, secs)


def vibrato(delay=0.25, rate=5.4, cents=18.0, ramp=0.35):
    def f(t):
        d = np.clip((t - delay) / ramp, 0, 1)
        return d * cents / 100 * np.sin(2 * np.pi * rate * np.maximum(t - delay, 0))
    return f


def note(inst, m, vel, dur, release=0.12, bends=(), cents=0.0, fade_with_fall=None):
    """Render one note. dur = held time (s). bends: functions t -> semitones, summed.
    fade_with_fall: (at, secs) fades the note out as a fall drops."""
    z = pick_zone(inst, m, vel)
    x, sr = audio(inst, z["file"])
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    semis = (m - z["root"]) + (z.get("tune", 0) + cents) / 100 + sum((b(t) for b in bends), np.zeros(n))
    step = 2 ** (semis / 12) * sr / SR
    pos = np.concatenate([[0.0], np.cumsum(step)[:-1]])
    ls, le = z.get("loop_start"), z.get("loop_end")
    if ls is not None and le is not None and le > ls:
        over = pos >= le
        pos[over] = ls + (pos[over] - le) % (le - ls)
    valid = pos < len(x) - 1
    i = np.minimum(pos.astype(int), len(x) - 2)
    fr = (pos - i)[:, None]
    y = (x[i] * (1 - fr) + x[i + 1] * fr) * valid[:, None]
    # layer-internal velocity gain: soft end of each layer a little quieter
    v = int(np.clip(round(vel * 127), 1, 127))
    span = max(1, z["hivel"] - z["lovel"])
    g = 0.7 + 0.3 * (v - z["lovel"]) / span
    env = np.ones(n)
    r0 = int(dur * SR)
    env[r0:] = np.exp(-np.arange(n - r0) / (release * SR / 4))
    if fade_with_fall:
        at, secs = fade_with_fall
        env *= np.clip(1 - (t - at) / secs, 0, 1) ** 1.5 * (t > at) + (t <= at)
    on = int(0.002 * SR)
    env[:on] *= np.linspace(0, 1, on)
    return y * (g * env)[:, None]
