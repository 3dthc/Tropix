"""Tropix tine piano: a physical-style model of a Rhodes-type electric piano, computed from scratch.

How the sound is made, and how this models it:
  * A hammer strikes a thin steel tine bolted to a heavier tone bar. The tine vibrates mostly at its fundamental,
    with a short, inharmonic upper mode (the "bell" or "ping") that dies away within a fraction of a second.
  * The tine and tone bar are tuned close but not identical, so energy trades between them: a slow, gentle beat.
  * An electromagnetic pickup sits just off the tine's tip. Its output follows the change in magnetic flux, which
    is a strongly nonlinear function of how far the tip is from the pole: small swings sound round and sine-like,
    big swings (hard strikes, or the tip set close to the pole) add odd and even harmonics: the "bark".
  * Low notes ring for many seconds; high notes are short. The decay has a quick first stage then a long tail.
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100


def mtof(m, a4=440.0):
    return a4 * 2 ** ((m - 69) / 12)


def tine_note(m, vel, rng=None, secs=None, a4=440.0, bark=1.0, bell=1.0):
    """One struck note. vel in (0, 1]. bark scales the pickup drive, bell the inharmonic ping."""
    rng = rng or np.random.default_rng(m * 7919 + 17)
    f0 = mtof(m, a4)
    pos = np.clip((m - 28) / (96 - 28), 0, 1)
    t60 = 9.0 * (1.6 / 9.0) ** pos            # ~9 s at E1, ~1.6 s at C7
    secs = secs or min(5.0, 0.3 + t60 * 0.6)
    n = int(secs * SR)
    t = np.arange(n) / SR

    # tine displacement: fundamental with a two-stage decay, beating slowly against the tone bar
    k_slow = np.log(1000) / t60
    k_fast = k_slow * 4
    env = 0.35 * np.exp(-k_fast * t) + 0.65 * np.exp(-k_slow * t)
    beat = 1 + 0.06 * np.sin(2 * np.pi * rng.uniform(0.3, 0.9) * t + rng.uniform(0, 6.28))
    amp = 0.25 + 0.75 * vel ** 1.2           # how far the tine swings
    x = amp * env * beat * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 6.28))

    # bell: the tine's second mode, ~7x up and slightly detuned per note, short; louder on harder strikes
    ratio = 7.1 * (1 + rng.normal(0, 0.01))
    fb = f0 * ratio
    if fb < SR * 0.45:
        bt = 0.08 + 0.25 * (1 - pos)
        x += bell * 0.10 * vel ** 1.5 * np.exp(-t / bt) * np.sin(2 * np.pi * fb * t)

    # pickup: flux through the coil as a function of tip displacement (pole slightly offset, so the response is
    # asymmetric and gives even harmonics too); the output is its rate of change
    drive = (0.45 + 0.85 * vel ** 1.3) * bark
    off = 0.35
    q = drive * x + off
    flux = 1.0 / (1.0 + q * q)
    y = np.gradient(flux) * SR / (2 * np.pi * f0)  # normalise the derivative so pitch doesn't change level
    y -= y.mean()

    # hammer: a felt-tipped thump and a short tine "tick", stronger when hit hard
    nb = int(0.012 * SR)
    th = rng.normal(0, 1, nb) * np.exp(-np.arange(nb) / (0.002 * SR))
    th = sosfilt(butter(2, [400, min(3500, SR * 0.45)], "band", fs=SR, output="sos"), th)
    y[:nb] += 0.05 * vel ** 2 * th

    # the amp and speaker cabinet of the stage piano: gentle low-pass, small low-mid bump
    y = sosfilt(butter(2, 7000, "low", fs=SR, output="sos"), y)
    y = sosfilt(butter(1, 40, "high", fs=SR, output="sos"), y)

    on = int(0.0008 * SR)
    y[:on] *= np.linspace(0, 1, on)
    fo = int(0.08 * SR)
    y[-fo:] *= np.linspace(1, 0, fo) ** 2
    return y  # level already follows the strike through the tine swing and pickup; the plugin adds velocity gain
