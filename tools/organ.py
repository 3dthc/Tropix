"""Tropix tonewheel organ, computed from scratch.

A tonewheel organ adds up near-sine "wheels" set by nine drawbars at fixed footages (16', 5 1/3', 8', 4', 2 2/3',
2', 1 3/5', 1 1/3', 1'), each 0-8. This models:
  * the nine harmonic ratios (0.5, 1.5, 1, 2, 3, 4, 5, 6, 8) with the real organ's foldback: the top wheels stop
    at about 6 kHz, so very high footages fold down an octave;
  * each wheel's slight impurity (a trace of its own 3rd harmonic);
  * key click: the contacts bounce as the key closes, a short broadband tick;
  * optional percussion (the 2nd or 3rd harmonic, decaying quickly on each new note);
  * faint leakage from neighbouring wheels, which keeps the tone alive.
The rotary speaker is not baked in; the plugin's chorus/vibrato and the demo's rotary simulation supply it.
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
FOOT = [0.5, 1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
TOP_WHEEL = 5900.0

REGISTRATIONS = {
    "organ_bubble": dict(bars="888000000", perc=None, click=0.6,
                         desc="The reggae bubble: first three drawbars full, round and woody."),
    "organ_perc": dict(bars="888000000", perc=3, click=0.4,
                       desc="Same body with third-harmonic percussion: a crisp, plucky attack for skanks and comps."),
    "organ_full": dict(bars="888800008", perc=None, click=0.8,
                       desc="Fuller and brighter, with the top 1' bar: for big chords and gospel-tinged pads."),
}


def mtof(m, a4=440.0):
    return a4 * 2 ** ((m - 69) / 12)


def organ_note(m, vel=0.8, reg="organ_bubble", secs=3.0, rng=None, a4=440.0):
    """A held note (no release; the sampler loops the steady part and applies the release)."""
    r = REGISTRATIONS[reg]
    rng = rng or np.random.default_rng(m * 31 + sum(map(ord, reg)))
    f0 = mtof(m, a4)
    n = int(secs * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    levels = [int(c) for c in r["bars"]]
    for ratio, lvl in zip(FOOT, levels):
        if lvl == 0:
            continue
        f = f0 * ratio
        while f > TOP_WHEEL:          # foldback
            f /= 2
        if f < 30:
            continue
        a = 10 ** ((lvl - 8) * 3 / 20)   # each drawbar step is about 3 dB
        ph = rng.uniform(0, 2 * np.pi)
        y += a * (np.sin(2 * np.pi * f * t + ph) + 0.03 * np.sin(6 * np.pi * f * t + ph))
    # leakage: a whisper of the wheels a fifth and an octave away
    for ratio in (1.5 * 2, 0.75):
        y += 0.004 * np.sin(2 * np.pi * f0 * ratio * t + rng.uniform(0, 6.28))
    if r["perc"]:
        fp = f0 * r["perc"]
        while fp > TOP_WHEEL:
            fp /= 2
        y += 0.9 * np.exp(-t / 0.22) * np.sin(2 * np.pi * fp * t)
    # key click: contact bounce, a few ms of filtered noise and a DC-ish step
    nc = int(0.006 * SR)
    click = rng.normal(0, 1, nc) * np.exp(-np.arange(nc) / (0.0012 * SR))
    click = sosfilt(butter(2, [800, 9000], "band", fs=SR, output="sos"), click)
    y[:nc] += r["click"] * (0.3 + 0.7 * vel) * 0.6 * click
    on = int(0.003 * SR)
    y[:on] *= np.linspace(0, 1, on)
    return y / max(1.0, sum(10 ** ((lv - 8) * 3 / 20) for lv in levels if lv)) * 2.0


def rotary(x, speed="slow", sr=SR):
    """Simple rotary speaker for demos: the horn (highs) and drum (lows) turn at different rates, giving tremolo
    and Doppler vibrato, spread across the stereo field."""
    rates = {"slow": (0.83, 0.67), "fast": (6.7, 5.8)}[speed]
    lo = sosfilt(butter(2, 800, "low", fs=sr, output="sos"), x)
    hi = x - lo
    n = len(x)
    t = np.arange(n) / sr
    out = np.zeros((n, 2))
    for band, rate, depth_ms, am in ((hi, rates[0], 0.35, 0.35), (lo, rates[1], 0.15, 0.2)):
        for c, ph in ((0, 0.0), (1, np.pi / 2)):
            d = depth_ms / 1000 * sr * (1 + np.sin(2 * np.pi * rate * t + ph))
            pos = np.arange(n) - d
            i = np.clip(pos.astype(int), 0, n - 2)
            f = pos - i
            v = band[i] * (1 - f) + band[i + 1] * f
            out[:, c] += v * (1 - am / 2 + am / 2 * np.sin(2 * np.pi * rate * t + ph))
    return out
