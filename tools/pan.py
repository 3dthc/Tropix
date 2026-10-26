"""Tropix steel pan engine: modal synthesis of a struck steel pan note.

Everything is computed from scratch, so the output carries no third-party rights.

How a pan note sounds, and how this models it:
  * Each note area is tuned so its first modes sit at f, 2f and 3f (tenor and cello pans may carry 4f too).
    Bass pans are tuned with a weak fundamental; the ear hears it from 2f and 3f.
  * The note area is not perfectly round, so every mode is a close pair of frequencies (a doublet). The pair
    beats slowly, which gives the pan its shimmer.
  * The note is nonlinear: a hard strike starts slightly sharp, and energy flows from the fundamental into the
    octave over the first tens of milliseconds, so the octave "blooms" after the attack.
  * A rubber-tipped stick touches the steel for about a millisecond; a harder strike is a shorter contact, which
    reaches higher modes. That is modelled as a gentle low-pass on the excitation whose corner rises with force.
  * Strikes also ring the skirt and the steel around the note (fast-decaying inharmonic modes) and sympathetic
    notes tuned a fourth, a fifth or an octave away.
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100


def mtof(m, a4=440.0):
    return a4 * 2 ** ((m - 69) / 12)


# Pan voicings. Ranges are MIDI notes (lowest, highest) as on standard pans:
#   tenor (lead) D4-F#6, double second F#3-C#6, cello B2-E5, six bass A1-F3.
# modes: (harmonic ratio, level, decay factor relative to the fundamental's T60)
VOICINGS = {
    "tenor": dict(
        lo=62, hi=90,
        modes=[(1, 1.00, 1.00), (2, 0.85, 0.62), (3, 0.40, 0.42), (4, 0.12, 0.30)],
        t60_lo=2.6, t60_hi=0.9,     # fundamental T60 (s) at the bottom / top of the range
        bright=(1400, 5200),        # mallet corner frequency (Hz) soft / hard
        bloom=0.55, skirt=0.16, symp=0.040, body_hz=None,
    ),
    "double_second": dict(
        lo=54, hi=85,
        modes=[(1, 1.00, 1.00), (2, 0.75, 0.66), (3, 0.32, 0.45), (4, 0.08, 0.32)],
        t60_lo=2.9, t60_hi=1.0,
        bright=(1100, 4200),
        bloom=0.50, skirt=0.13, symp=0.045, body_hz=None,
    ),
    "cello": dict(
        lo=47, hi=76,
        modes=[(1, 1.00, 1.00), (2, 0.62, 0.70), (3, 0.26, 0.48)],
        t60_lo=3.2, t60_hi=1.3,
        bright=(800, 3000),
        bloom=0.42, skirt=0.10, symp=0.050, body_hz=110.0,
    ),
    "bass": dict(
        lo=33, hi=53,
        modes=[(1, 0.45, 1.00), (2, 1.00, 0.75), (3, 0.55, 0.50)],
        t60_lo=3.4, t60_hi=2.0,
        bright=(450, 1600),
        bloom=0.30, skirt=0.06, symp=0.030, body_hz=70.0,
    ),
}

# Inharmonic skirt / surrounding-steel modes, as ratios of the fundamental, with level and T60 (s).
SKIRT = [(4.62, 0.50, 0.09), (5.81, 0.40, 0.07), (7.13, 0.30, 0.05), (8.9, 0.22, 0.04), (11.3, 0.15, 0.03)]


def contact_gain(f, fc):
    """Mallet spectrum: a rubber tip acts like a gentle low-pass whose corner rises with strike force.
    fc is the corner (Hz); the slope is ~9 dB/octave above it, below which modes are excited fully."""
    return 1.0 / (1.0 + (np.asarray(f) / fc) ** 2) ** 0.75


def _decaying(f, t60, n, phase, t):
    k = np.log(1000.0) / t60
    return np.sin(2 * np.pi * f * t + phase) * np.exp(-k * t)


def pan_note(m, vel, voicing="tenor", rng=None, secs=None, a4=440.0):
    """Render one struck note. vel in (0, 1]. Returns mono float64, peak not normalised."""
    v = VOICINGS[voicing]
    rng = rng or np.random.default_rng(m * 131 + sum(map(ord, voicing)))  # same pan, same note at every velocity
    f0 = mtof(m, a4)
    pos = np.clip((m - v["lo"]) / max(1, v["hi"] - v["lo"]), 0, 1)
    t60 = v["t60_lo"] * (v["t60_hi"] / v["t60_lo"]) ** pos
    secs = secs or min(4.5, t60 * 1.15 + 0.25)
    n = int(secs * SR)
    t = np.arange(n) / SR

    fc = v["bright"][0] * (v["bright"][1] / v["bright"][0]) ** (vel ** 0.9)

    # Pitch glide: hard strikes start sharp (up to ~+9 cents) and settle within ~120 ms.
    glide_cents = 9.0 * vel ** 1.5 * np.exp(-t / 0.045)
    glide = 2 ** (glide_cents / 1200)
    # integrate frequency for phase so the glide is smooth
    def phase_track(f):
        return 2 * np.pi * np.cumsum(f * glide) / SR

    out = np.zeros(n)
    for i, (ratio, lvl, dfac) in enumerate(v["modes"]):
        f = f0 * ratio * 2 ** (rng.normal(0, 1.2) / 1200)  # tuners leave a cent or so
        if f > SR * 0.45:
            continue
        # louder strikes drive the steel harder, so upper harmonics grow faster than the fundamental
        g = lvl * contact_gain(f, fc) * (vel / 0.7) ** (0.5 * (ratio - 1))
        mt60 = t60 * dfac * (1.0 - 0.15 * vel)  # hard hits lose energy faster (radiation + coupling)
        k = np.log(1000.0) / mt60
        # doublet: two close components beating at 0.4-3 Hz
        split = f * (2 ** (rng.uniform(3.0, 8.0) / 1200) - 1)  # doublet 3-8 cents apart
        mix = rng.uniform(0.25, 0.5)
        # the tuner tunes the stronger component; the weaker one sits just above or below it
        ph = phase_track(np.full(n, f))
        ph2 = phase_track(np.full(n, f + split * rng.choice([-1.0, 1.0])))
        p0, p1 = rng.uniform(0, 2 * np.pi, 2)
        osc = (1 - mix) * np.sin(ph + p0) + mix * np.sin(ph2 + p1)
        env = np.exp(-k * t)
        if ratio == 2:
            # bloom: the octave is fed by the fundamental and swells in after the strike
            rise = 0.012 + 0.03 * (1 - vel)
            b = v["bloom"] * (0.5 + 0.5 * vel)
            env = env * ((1 - b) + b * (1 - np.exp(-t / rise)) * 1.35)
        if ratio == 1 and m < 72:
            # the fundamental gives a little energy away early on
            env = env * (1 - 0.18 * vel * np.exp(-t / 0.05) * (1 - np.exp(-t / 0.004)))
        out += g * osc * env

    # skirt and surrounding steel: inharmonic, short, mostly on harder strikes
    sk = np.zeros(n)
    for ratio, lvl, st60 in SKIRT:
        f = f0 * ratio * rng.uniform(0.97, 1.03)
        if f > SR * 0.45:
            continue
        sk += lvl * contact_gain(f, fc) * _decaying(f, st60, n, rng.uniform(0, 6.28), t)
    out += v["skirt"] * (0.35 + 0.65 * vel) * sk

    # stick tick: a very short band-passed noise burst
    nb = int(0.006 * SR)
    noise = rng.normal(0, 1, nb) * np.exp(-np.arange(nb) / (0.0012 * SR))
    lo_hz = min(1800 + 2500 * vel, SR * 0.4)
    sos = butter(2, [lo_hz, min(lo_hz * 3.2, SR * 0.45)], "band", fs=SR, output="sos")
    out[:nb] += 0.05 * vel ** 1.3 * sosfilt(sos, noise)

    # sympathetic notes: a fourth up, a fifth down and the octave, swelling in slowly and quietly
    for semis, lvl in ((5, 1.0), (-7, 0.8), (12, 0.6)):
        fs_ = mtof(m + semis, a4)
        if fs_ > SR * 0.45:
            continue
        env = (1 - np.exp(-t / 0.08)) * np.exp(-np.log(1000) / (t60 * 0.8) * t)
        out += v["symp"] * lvl * vel * np.sin(2 * np.pi * fs_ * t + rng.uniform(0, 6.28)) * env

    # drum body (cello and bass pans): the barrel adds a low thump
    if v["body_hz"]:
        bh = v["body_hz"] * rng.uniform(0.95, 1.05)
        out += 0.12 * vel * _decaying(bh, 0.18, n, 0.0, t)

    out *= vel ** 0.7  # overall loudness follows the strike

    # tiny onset ramp to avoid a click, and a fade at the end of the render
    on = int(0.0007 * SR)
    out[:on] *= np.linspace(0, 1, on)
    fo = int(0.08 * SR)
    out[-fo:] *= np.linspace(1, 0, fo) ** 2
    return out


def stereo_place(x, m, lo, hi, width=0.35, rng=None):
    """Place a mono note in stereo the way a player hears the pan: low notes and high notes sit at different
    points on the drum. A small inter-channel delay and gain keep it natural on headphones."""
    rng = rng or np.random.default_rng(m)
    pos = (np.clip((m - lo) / max(1, hi - lo), 0, 1) - 0.5) * 2 * width
    d = int(abs(pos) * 0.0004 * SR)
    l, r = np.copy(x), np.copy(x)
    if pos > 0:
        l = np.concatenate([np.zeros(d), l[:len(l) - d]]) * (1 - 0.25 * pos)
    elif pos < 0:
        r = np.concatenate([np.zeros(d), r[:len(r) - d]]) * (1 + 0.25 * pos)
    return np.stack([l, r], axis=1)
