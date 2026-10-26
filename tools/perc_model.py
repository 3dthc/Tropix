"""Tropix modeled percussion: timbales and the Hawaiian ipu, computed from scratch.

Timbales are two single-headed drums with thin steel shells, tuned high. A stroke excites
  * the head: circular-membrane modes (ratios 1, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50) that die quickly,
  * the shell: a bright, inharmonic metallic ring that outlasts the head (the timbale "ping"),
  * the rim, on a rimshot: a sharp crack with extra shell ring.
The paila (cascara) stroke plays the shell's side with the stick: shell ring and click, almost no head.

The ipu is a gourd drum: the heel stroke (the gourd dropped onto a pad) sounds the air inside, a deep, woody
Helmholtz resonance; the tip stroke (palm slap near the opening) is higher and drier.
"""
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 44100
MEMBRANE = [1.0, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501]


def _modes(n, f0, ratios, levels, t60s, rng):
    t = np.arange(n) / SR
    y = np.zeros(n)
    for r, a, t60 in zip(ratios, levels, t60s):
        f = f0 * r * rng.uniform(0.995, 1.005)
        if f < SR * 0.45:
            y += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-np.log(1000) / t60 * t)
    return y


def _noise(n, lo, hi, tau, rng, amp=1.0):
    x = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (tau * SR))
    return amp * sosfilt(butter(2, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x)


def timbale(stroke="open", drum="macho", vel=0.8, rng=None, secs=1.2):
    """stroke: open, rim, muted, paila. drum: macho (high) or hembra (low)."""
    rng = rng or np.random.default_rng(hash((stroke, drum)) & 0xFFFF)
    n = int(secs * SR)
    f0 = 410.0 if drum == "macho" else 315.0
    bright = 0.4 + 0.6 * vel
    head = _modes(n, f0, MEMBRANE, [1.0, 0.7, 0.55, 0.4, 0.35, 0.3, 0.22, 0.18],
                  [0.22, 0.14, 0.11, 0.09, 0.08, 0.07, 0.06, 0.05], rng)
    shell_f = (2370.0 if drum == "macho" else 2050.0)
    shell = _modes(n, shell_f, [1.0, 1.37, 1.81, 2.43, 2.97, 3.62], [1.0, 0.8, 0.6, 0.45, 0.3, 0.2],
                   [0.55, 0.45, 0.35, 0.28, 0.22, 0.18], rng)
    stick = _noise(int(0.01 * SR), 2000, 9000, 0.0015, rng)
    y = np.zeros(n)
    if stroke == "open":
        y += head * 0.9 + shell * 0.18 * bright
        y[:len(stick)] += 0.25 * bright * stick
    elif stroke == "rim":
        y += head * 0.7 + shell * 0.45 * bright
        crack = _noise(int(0.02 * SR), 1500, 12000, 0.003, rng, 1.0)
        y[:len(crack)] += 0.8 * bright * crack
    elif stroke == "muted":
        t = np.arange(n) / SR
        y += (head * np.exp(-t / 0.035)) * 0.9 + shell * 0.05 * np.exp(-t / 0.05)
        y[:len(stick)] += 0.2 * stick
    elif stroke == "paila":
        t = np.arange(n) / SR
        y += shell * 0.5 * np.exp(-t / 0.08) + head * 0.04
        click = _noise(int(0.008 * SR), 2500, 10000, 0.001, rng, 1.0)
        y[:len(click)] += 0.9 * click
    on = int(0.0005 * SR)
    y[:on] *= np.linspace(0, 1, on)
    return y * (0.3 + 0.7 * vel)


def ipu(stroke="heel", vel=0.8, rng=None, secs=1.0):
    """stroke: heel (deep), tip (palm near the opening), slap (sharper tip)."""
    rng = rng or np.random.default_rng(hash(("ipu", stroke)) & 0xFFFF)
    n = int(secs * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    if stroke == "heel":
        f = 96.0 * rng.uniform(0.98, 1.02)
        body = np.sin(2 * np.pi * f * t * (1 + 0.04 * np.exp(-t / 0.05))) * np.exp(-t / 0.16)
        wood = _modes(n, 410.0, [1.0, 1.9, 2.7], [0.5, 0.3, 0.15], [0.06, 0.04, 0.03], rng)
        thud = _noise(int(0.03 * SR), 60, 900, 0.008, rng)
        y += body + 0.35 * wood
        y[:len(thud)] += 0.6 * thud
    else:
        f = 260.0 if stroke == "tip" else 330.0
        tau = 0.07 if stroke == "tip" else 0.045
        body = np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
        air = sosfilt(butter(2, [f * 0.8, f * 1.3], "band", fs=SR, output="sos"),
                      rng.normal(0, 1, n) * np.exp(-t / 0.02))
        palm = _noise(int(0.015 * SR), 800, 5000, 0.003 if stroke == "slap" else 0.005, rng)
        y += body * 0.8 + air * 2.0
        y[:len(palm)] += (0.9 if stroke == "slap" else 0.5) * palm
    on = int(0.0008 * SR)
    y[:on] *= np.linspace(0, 1, on)
    return y * (0.3 + 0.7 * vel)


def melodica(m, vel=0.8, secs=3.0, rng=None, a4=440.0):
    """Free-reed melodica: a brass reed chopping the air (a bright, narrow pulse), the plastic body's resonance,
    breath noise, and the reed taking a few tens of milliseconds to speak."""
    rng = rng or np.random.default_rng(m * 101)
    f0 = a4 * 2 ** ((m - 69) / 12)
    n = int(secs * SR)
    t = np.arange(n) / SR
    drift = 1 + 0.0012 * np.sin(2 * np.pi * 0.7 * t + rng.uniform(0, 6.28))   # breath pressure wobble
    ph = np.cumsum(f0 * drift) / SR % 1.0
    width = 0.22
    # band-limited pulse from summed harmonics (keeps it clean at every pitch)
    y = np.zeros(n)
    k = 1
    while k * f0 < min(9000.0, SR * 0.45):
        y += (np.sin(np.pi * k * width) / (np.pi * k)) * np.cos(2 * np.pi * k * ph)
        k += 1
    # body: two broad resonances, a nasal mid and a little presence
    for fc, q, g in ((1300.0, 2.0, 0.7), (3100.0, 3.0, 0.35)):
        w = 2 * np.pi * fc / SR
        r = np.exp(-w / (2 * q))
        res = lfilter([1 - r], [1, -2 * r * np.cos(w), r * r], y)
        y = y + g * res
    breath = sosfilt(butter(2, [1500, 6000], "band", fs=SR, output="sos"), rng.normal(0, 1, n)) * 0.02
    speak = 0.025 + 0.02 * (1 - vel)
    env = 1 - np.exp(-t / speak)
    y = (y + breath) * env * (0.5 + 0.5 * vel)
    y = sosfilt(butter(1, 60, "high", fs=SR, output="sos"), y)
    return y
