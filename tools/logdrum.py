"""Tropix amapiano log drum engine.

The amapiano "log drum" is a synthesized, pitched percussive bass, not a recording of a wooden log drum. Its sound:
  * a mostly-sine body that starts several semitones sharp and drops onto the note within a few tens of ms,
  * soft saturation that adds the 2nd and 3rd harmonics so it reads on small speakers,
  * a short woody "knock" at the attack,
  * a decay from a tight thump to a long boom, and in some styles a resonant filter that sweeps down ("talks").

Everything here is computed from scratch, so the output carries no third-party rights.
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100


def mtof(m, a4=440.0):
    return a4 * 2 ** ((m - 69) / 12)


# Variations. drop: semitones above the note at the strike; drop_ms: time constant of the drop;
# decay: seconds to -60 dB; drive: saturation amount; knock: level of the woody click;
# talk: depth (octaves) of a resonant low-pass sweep (0 = off); sub: extra pure-sine weight.
VARIATIONS = {
    "classic": dict(drop=7.0, drop_ms=22, decay=0.9, drive=2.2, knock=0.35, talk=0.0, sub=0.25,
                    desc="The standard amapiano log drum: round body, quick pitch drop, light knock."),
    "deep": dict(drop=3.0, drop_ms=30, decay=1.8, drive=1.3, knock=0.15, talk=0.0, sub=0.55,
                 desc="Long, clean and round; sits under everything."),
    "knock": dict(drop=12.0, drop_ms=12, decay=0.45, drive=2.8, knock=0.75, talk=0.0, sub=0.10,
                  desc="Short and punchy with a hard wooden attack; cuts through a busy mix."),
    "talking": dict(drop=5.0, drop_ms=25, decay=1.1, drive=2.6, knock=0.30, talk=2.6, sub=0.20,
                    desc="A resonant filter sweeps down after the hit, so the note says 'yow'."),
    "gritty": dict(drop=9.0, drop_ms=18, decay=0.8, drive=6.0, knock=0.45, talk=0.0, sub=0.15,
                   desc="Pushed hard into saturation: more harmonics, more aggression."),
}


def _knock(n, f0, vel, rng):
    """Woody click: a few inharmonic wood modes (ratios of a short bar) plus a filtered noise tick."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    base = np.clip(f0 * 4.0, 350, 900)  # knock sits a couple of octaves above the body, but stays woody
    for ratio, lvl, t60 in ((1.0, 1.0, 0.045), (2.76, 0.55, 0.025), (5.40, 0.30, 0.015)):
        f = base * ratio * rng.uniform(0.98, 1.02)
        out += lvl * np.sin(2 * np.pi * f * t) * np.exp(-np.log(1000) / t60 * t)
    nb = min(n, int(0.004 * SR))
    tick = rng.normal(0, 1, nb) * np.exp(-np.arange(nb) / (0.0007 * SR))
    tick = sosfilt(butter(2, [1500, 6000], "band", fs=SR, output="sos"), tick)
    out[:nb] += 0.6 * tick
    return out * (0.4 + 0.6 * vel)


def _svf_lowpass(x, fc, q):
    """Time-varying state-variable low-pass (Chamberlin), fc per sample."""
    y = np.zeros_like(x)
    low = band = 0.0
    damp = 1.0 / q
    f = 2 * np.sin(np.pi * np.minimum(fc, SR / 6) / SR)
    for i in range(len(x)):
        high = x[i] - low - damp * band
        band += f[i] * high
        low += f[i] * band
        y[i] = low
    return y


def log_drum(m, vel=0.8, variation="classic", rng=None, secs=None, glide_from=None, glide_ms=60, a4=440.0):
    """Render one log drum note. glide_from: MIDI note to slide from (legato glide) instead of the drop."""
    v = VARIATIONS[variation]
    rng = rng or np.random.default_rng(m * 977 + sum(map(ord, variation)))
    f0 = mtof(m, a4)
    decay = v["decay"] * (1.0 + 0.25 * (1 - vel))
    secs = secs or min(3.0, decay + 0.15)
    n = int(secs * SR)
    t = np.arange(n) / SR

    # pitch: drop from above (strike) or slide from the previous note (glide)
    if glide_from is not None:
        st = (glide_from - m) * np.exp(-t / (glide_ms / 1000 / 3))
    else:
        drop = v["drop"] * (0.6 + 0.4 * vel)
        st = drop * np.exp(-t / (v["drop_ms"] / 1000))
    f = f0 * 2 ** (st / 12)
    ph = 2 * np.pi * np.cumsum(f) / SR

    # amp: instant attack, two-stage decay (fast thump into a slower tail)
    k = np.log(1000) / decay
    amp = 0.55 * np.exp(-t * k * 3.0) + 0.45 * np.exp(-t * k)
    osc = np.sin(ph)
    body = osc * amp

    # saturation shapes the oscillator before the envelope, so the note keeps its harmonics as it decays
    # (brightness still eases off a little over the first quarter second). A small bias adds even harmonics.
    d = v["drive"] * (0.6 + 0.4 * vel) * (0.6 + 0.4 * np.exp(-t / 0.25))
    bias = 0.18
    sat = (np.tanh(d * (osc + bias)) - np.tanh(d * bias)) / np.tanh(d * (1 + bias))
    out = ((1 - v["sub"]) * sat + v["sub"] * osc) * amp

    if v["talk"] > 0:
        # resonant low-pass sweeping down from talk octaves above the 3rd harmonic onto the fundamental's area
        start = f0 * 3 * 2 ** v["talk"]
        fc = f0 * 1.5 + (start - f0 * 1.5) * np.exp(-t / 0.12)
        out = _svf_lowpass(out, fc, q=4.5) * 0.8

    out += v["knock"] * 0.35 * _knock(n, f0, vel, rng)
    out = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), out)  # no DC or sub-sonic rumble
    out *= vel ** 0.6

    on = int(0.0005 * SR)
    out[:on] *= np.linspace(0, 1, on)
    fo = int(0.05 * SR)
    out[-fo:] *= np.linspace(1, 0, fo) ** 2
    return out
