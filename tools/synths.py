"""Tropix synth voices, computed from scratch and voiced for the genres rather than as generic presets.

  soca_lead      the big stacked-saw lead of modern soca: seven detuned saws, a quick upward blip on the attack,
                 bright but not harsh
  soca_brass     synth brass for soca and kompa hits: saw stack through a low-pass that opens with each note
  afro_pluck     the short, warm square pluck of Afrobeats melodies
  piano_pluck    amapiano's glassy FM pluck (the "private school" bell lead)
  island_pad     soft, warm pad for amapiano and ballads (the plugin's LFO makes it breathe)
  sub_bass       pure low end with a touch of warmth, for when the log drum needs a floor
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100


def mtof(m, a4=440.0):
    return a4 * 2 ** ((m - 69) / 12)


LOOP_S = 4.0   # looped voices repeat exactly every 4 s: every oscillator sits on a multiple of 1/4 Hz


def snap(f, period=LOOP_S):
    """Round a frequency to a whole number of cycles per loop, so the sum of detuned oscillators (and their
    beating) repeats exactly and the loop is seamless. The small pitch error is corrected by the zone's tune."""
    return np.round(np.asarray(f) * period) / period


def _blsaw(f, n, phase0=0.0):
    """Band-limited saw (polyBLEP); f may be a per-sample array."""
    f = np.broadcast_to(np.asarray(f, dtype=np.float64), (n,))
    dt = f / SR
    t = (phase0 + np.cumsum(dt)) % 1.0
    y = 2 * t - 1
    a = t < dt
    x = t[a] / dt[a]
    y[a] -= x + x - x * x - 1
    b = t > 1 - dt
    x = (t[b] - 1) / dt[b]
    y[b] -= x * x + x + x + 1
    return y


def _lp_sweep(x, f_start, f_end, tau, q=0.9, steps=32):
    """Low-pass whose cutoff moves from f_start to f_end (time constant tau), applied in short blocks."""
    n = len(x)
    out = np.zeros(n)
    edges = np.unique(np.concatenate([np.geomspace(1, max(2, int(6 * tau * SR)), steps).astype(int), [n]]))
    edges = edges[edges <= n]
    a = 0
    zi = None
    for e in list(edges) + [n]:
        if e <= a:
            continue
        tm = a / SR
        fc = f_end + (f_start - f_end) * np.exp(-tm / tau)
        sos = butter(2, min(max(fc, 30), SR * 0.45), "low", fs=SR, output="sos")
        from scipy.signal import sosfilt_zi
        if zi is None:
            zi = sosfilt_zi(sos) * 0
        out[a:e], zi = sosfilt(sos, x[a:e], zi=zi)
        a = e
    return out


def soca_lead(m, vel=0.8, secs=1.0 + LOOP_S, rng=None):
    rng = rng or np.random.default_rng(m)
    n = int(secs * SR)
    t = np.arange(n) / SR
    f0 = mtof(m)
    blip = 2 ** ((1.2 * vel) * np.exp(-t / 0.02) / 12)
    y = np.zeros(n)
    for c in np.linspace(-22, 22, 7):
        y += _blsaw(snap(f0 * 2 ** ((c + rng.normal(0, 1.5)) / 1200)) * blip, n, rng.uniform())
    y += 0.5 * _blsaw(snap(f0 / 2) * blip, n, rng.uniform())   # an octave below for weight
    y = sosfilt(butter(2, 7500, "low", fs=SR, output="sos"), y)
    y = sosfilt(butter(1, 120, "high", fs=SR, output="sos"), y)
    env = 1 - np.exp(-t / 0.004)
    return y * env / 5.0


def soca_brass(m, vel=0.8, secs=1.0 + LOOP_S, rng=None):
    rng = rng or np.random.default_rng(m + 7)
    n = int(secs * SR)
    t = np.arange(n) / SR
    f0 = mtof(m)
    y = sum(_blsaw(snap(f0 * 2 ** (c / 1200)), n, rng.uniform()) for c in (-9, 0, 8))
    open_ = 900 + 3500 * vel
    y = _lp_sweep(y, open_, 1400 + 600 * vel, 0.1)
    env = (1 - np.exp(-t / 0.025)) * (0.75 + 0.25 * np.exp(-t / 0.12))   # settled well before the loop at 1 s
    return y * env / 2.0


def afro_pluck(m, vel=0.8, secs=1.5, rng=None):
    rng = rng or np.random.default_rng(m + 11)
    n = int(secs * SR)
    t = np.arange(n) / SR
    f0 = mtof(m)
    sq = _blsaw(f0, n, 0.0) - _blsaw(f0, n, 0.5)               # square from two saws
    tri = np.abs(((t * f0 * 2) % 2) - 1) * 2 - 1
    y = 0.7 * sq + 0.5 * tri
    y = _lp_sweep(y, 2500 + 4000 * vel, 600, 0.06)
    env = np.exp(-t / (0.18 + 0.1 * vel)) * (1 - np.exp(-t / 0.002))
    return y * env / 1.5


def piano_pluck(m, vel=0.8, secs=2.5, rng=None):
    """Two-operator FM: a modulator at 3.5x (a glassy, slightly inharmonic shimmer) whose depth decays fast."""
    n = int(secs * SR)
    t = np.arange(n) / SR
    f0 = mtof(m)
    idx = (1.2 + 2.2 * vel) * np.exp(-t / 0.12) + 0.25
    mod = np.sin(2 * np.pi * f0 * 3.5 * t)
    y = np.sin(2 * np.pi * f0 * t + idx * mod) + 0.25 * np.sin(2 * np.pi * f0 * 2 * t) * np.exp(-t / 0.4)
    env = np.exp(-t / 0.9) * (1 - np.exp(-t / 0.0015))
    return y * env * 0.6


def island_pad(m, vel=0.8, secs=1.0 + LOOP_S, rng=None):
    rng = rng or np.random.default_rng(m + 23)
    n = int(secs * SR)
    t = np.arange(n) / SR
    f0 = mtof(m)
    y = np.zeros(n)
    for c in (-11, -4, 3, 10):
        y += _blsaw(snap(f0 * 2 ** (c / 1200)), n, rng.uniform())
    y += 0.8 * np.sin(2 * np.pi * snap(f0) * t)
    y = sosfilt(butter(2, 1800 + 800 * vel, "low", fs=SR, output="sos"), y)
    env = 1 - np.exp(-t / 0.11)   # fully swelled before the loop starts at 1 s; the plugin's attack sets the swell
    return y * env / 4.0   # the slow "breathing" comes from the plugin's LFO, so the sample loops cleanly


def sub_bass(m, vel=0.8, secs=1.0 + LOOP_S, rng=None):
    n = int(secs * SR)
    t = np.arange(n) / SR
    f0 = mtof(m)
    y = np.sin(2 * np.pi * snap(f0) * t)
    y = np.tanh(1.6 * y) / np.tanh(1.6)
    env = 1 - np.exp(-t / 0.004)
    return y * env * 0.8


VOICES = {"soca_lead": (soca_lead, True), "soca_brass": (soca_brass, True), "afro_pluck": (afro_pluck, False),
          "piano_pluck": (piano_pluck, False), "island_pad": (island_pad, True), "sub_bass": (sub_bass, True)}
