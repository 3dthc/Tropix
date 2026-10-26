"""Tropix sample prep (adapted from the Sonix prep tool, same author, MIT).

Turns raw recordings and our own renders into Tropix multisamples:
trim -> fit length -> (loop) -> normalize per instrument -> 44.1 kHz / 16-bit FLAC
-> keymap JSON, with the source and license of every file recorded.
"""
import json
import os
import re
from fractions import Fraction

import sys

import numpy as np
import soundfile as sf
from scipy.signal import correlate, resample_poly

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LIB = os.path.dirname(HERE)
SOURCES = json.load(open(os.path.join(LIB, "sources.json")))

NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_midi(name):
    """'A0', 'F#3', 'Bb2', 'As0' (A-sharp), 'Cs4' -> MIDI number (C4 = 60)."""
    m = re.fullmatch(r"([A-Ga-g])(#|b|s)?(-?\d)", name)
    if not m:
        raise ValueError(name)
    n = NOTE_BASE[m.group(1).upper()]
    acc = m.group(2)
    if acc in ("#", "s"):
        n += 1
    elif acc == "b":
        n -= 1
    return n + 12 * (int(m.group(3)) + 1)


def midi_name(m):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[m % 12]}{m // 12 - 1}"


def load(path, sr=SR):
    """Load any file as float32 stereo at `sr`."""
    x, fs = sf.read(path, dtype="float32", always_2d=True)
    if fs != sr:
        fr = Fraction(sr, fs).limit_denominator(1000)
        x = resample_poly(x, fr.numerator, fr.denominator, axis=0).astype(np.float32)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x[:, :2]


def db(v):
    return 20 * np.log10(max(v, 1e-12))


def trim_start(x, thresh_db=-50.0, pre_ms=2.0, steady_db=-30.0):
    """Cut leading silence. The onset is where the level first comes within `steady_db` of the note's steady level
    (90th percentile of the envelope) and above `thresh_db` re peak, so a quiet note recorded over room noise is
    trimmed to its real start, not to the noise."""
    env = np.max(np.abs(x), axis=1)
    sm = np.sqrt(np.convolve(env ** 2, np.ones(441) / 441, "same"))
    level = np.percentile(sm, 90)
    thr = max(sm.max() * 10 ** (thresh_db / 20), level * 10 ** (steady_db / 20))
    idx = int(np.argmax(sm > thr))
    idx = max(0, idx - int(SR * pre_ms / 1000))
    return x[idx:]


def tighten_attack(x, attack_db=-14.0, keep_ms=25.0, fade_ms=10.0, max_swell_ms=60.0):
    """For notes that swell in slowly (a player easing into a soft note): if the level takes longer than
    max_swell_ms to come within attack_db of the steady level, start the sample keep_ms before that point with a
    short fade-in, so the note speaks when the key is pressed. Quick attacks are left untouched."""
    env = np.max(np.abs(x), axis=1)
    sm = np.sqrt(np.convolve(env ** 2, np.ones(441) / 441, "same"))
    level = np.percentile(sm, 90)
    idx = int(np.argmax(sm > level * 10 ** (attack_db / 20)))
    if idx <= int(SR * max_swell_ms / 1000):
        return x
    a = max(0, idx - int(SR * keep_ms / 1000))
    y = x[a:].copy()
    n = int(SR * fade_ms / 1000)
    y[:n] *= np.sin(np.linspace(0, np.pi / 2, n))[:, None] ** 2
    return y


def fit_length(x, max_s, fade_s=0.3, floor_db=-60.0):
    """Cut the tail where it falls below `floor_db` (re peak) or at max_s, then fade out. (44.1 kHz input)"""
    env = np.max(np.abs(x), axis=1)
    peak = env.max()
    above = np.nonzero(env > peak * 10 ** (floor_db / 20))[0]
    end = min(len(x), (above[-1] + 1) if len(above) else len(x), int(max_s * SR))
    x = x[:end].copy()
    n = min(int(fade_s * SR), len(x))
    if n > 0:
        x[-n:] *= np.cos(np.linspace(0, np.pi / 2, n))[:, None] ** 2
    return x


def find_loop(x, region=(0.35, 0.9), xfade_s=0.25, win=4096, sr=SR):
    """Pick loop points in the steady part and bake an equal-power crossfade.

    Returns (y, loop_start, loop_end): y ends at loop_end; playback jumps from
    loop_end back to loop_start without a click.
    """
    mono = x.mean(axis=1)
    n = len(mono)
    end = int(n * region[1])
    lo = int(n * region[0])
    L = int(xfade_s * sr)
    ref = mono[end - win:end]
    # search start candidates in the first half of the region
    s_lo, s_hi = max(lo, L + win), max(lo + 1, int(n * (region[0] + (region[1] - region[0]) * 0.45)))
    seg = mono[s_lo - win:s_hi]
    c = correlate(seg, ref, mode="valid")
    energy = np.sqrt(np.convolve(seg ** 2, np.ones(win), mode="valid")) * np.sqrt(np.sum(ref ** 2)) + 1e-9
    score = c / energy
    best = int(np.argmax(score))
    start = s_lo + best
    y = x[:end].copy()
    w = np.sin(np.linspace(0, np.pi / 2, L)) ** 2
    y[end - L:end] = x[end - L:end] * (1 - w)[:, None] + x[start - L:start] * w[:, None]
    return y, start, end, float(score[best])


def _f0_track(m, sr, hop, fmin=60.0, fmax=1500.0):
    """Coarse pitch track (Hz per hop) from short-frame autocorrelation; 0 where unvoiced."""
    from audio import yin
    frame = int(sr * 0.04)
    out = []
    for a in range(0, len(m) - frame, hop):
        f = yin(m[a:a + frame], sr, fmin, fmax, thresh=0.2)
        out.append(f or 0.0)
    return np.array(out)


def find_loop_pitch(x, region=(0.25, 0.92), xfade_s=0.3, sr=SR, root=None):
    """Loop points for notes with vibrato or slow pitch drift.

    The loop end sits near the end of the steady region; the start is the earlier point whose recent pitch contour
    (vibrato phase and depth) and level best match the end's, then refined to the waveform match within one
    period. Returns (y, loop_start, loop_end, score) like find_loop."""
    mono = x.mean(axis=1)
    n = len(mono)
    hop = int(sr * 0.005)
    f0 = None if root is None else 440 * 2 ** ((root - 69) / 12)
    track = _f0_track(mono, sr, hop, *(((f0 / 1.5, f0 * 1.5)) if f0 else (60.0, 1500.0)))
    track = np.where(track > 0, 1200 * np.log2(np.maximum(track, 1) / np.median(track[track > 0])), np.nan)
    env = np.sqrt(np.convolve(mono ** 2, np.ones(hop * 4) / (hop * 4), "same"))[::hop][:len(track)]
    env_db = 20 * np.log10(env + 1e-9)
    end = int(n * region[1])
    L = int(xfade_s * sr)
    ctx = int(0.30 * sr / hop)                           # compare 300 ms of contour before each point
    ei = end // hop
    ref_p, ref_e = track[ei - ctx:ei], env_db[ei - ctx:ei]
    lo_i = max(int(n * region[0]) // hop, ctx + L // hop + 1)
    hi_i = ei - int(0.8 * sr / hop)                       # loop at least 0.8 s long
    best, best_i = np.inf, None
    for i in range(lo_i, max(lo_i + 1, hi_i)):
        cp, ce = track[i - ctx:i], env_db[i - ctx:i]
        if len(cp) != len(ref_p):
            continue
        good = ~np.isnan(cp) & ~np.isnan(ref_p)
        if good.mean() < 0.8:
            continue
        err = np.mean((cp[good] - ref_p[good]) ** 2) + 4.0 * np.mean((ce - ref_e) ** 2)
        if err < best:
            best, best_i = err, i
    if best_i is None:
        return find_loop(x, region=region, xfade_s=xfade_s, sr=sr)
    # refine: within one period, match the waveform just before the end
    period = int(sr / (f0 or 200.0))
    win = max(2 * period, int(0.02 * sr))
    ref = mono[end - win:end]
    c0 = best_i * hop
    cands = range(max(L + win, c0 - period), min(end - L - 1, c0 + period + 1))
    scores = [np.dot(mono[c - win:c], ref) / (np.linalg.norm(mono[c - win:c]) * np.linalg.norm(ref) + 1e-9) for c in cands]
    k = int(np.argmax(scores))
    start = list(cands)[k]
    y = x[:end].copy()
    w = np.sin(np.linspace(0, np.pi / 2, L)) ** 2
    y[end - L:end] = x[end - L:end] * (1 - w)[:, None] + x[start - L:start] * w[:, None]
    return y, start, end, float(scores[k])


def _spectrum(x, start_s=0.05, secs=0.6):
    m = x.mean(axis=1)
    a = min(int(start_s * SR), max(0, len(m) - 4096))
    seg = m[a:a + int(secs * SR)]
    N = 1 << 19
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), N))
    return sp, np.fft.rfftfreq(N, 1 / SR)


def measured_root(x, named, search=(-24, -12, 0, 12, 24)):
    """Pick the octave of `named` that the audio actually sounds in.

    Scores each candidate by energy at its harmonics minus energy at the
    half-harmonics (which only an octave-too-high candidate would see).
    Sample names in different libraries use different middle-C conventions,
    so the mapping always follows the measured pitch."""
    sp, fr = _spectrum(x)

    def s(f):
        if f > SR * 0.45:
            return 0.0
        lo, hi = np.searchsorted(fr, [f * 2 ** (-0.4 / 12), f * 2 ** (0.4 / 12)])
        return float(sp[lo:hi].max()) if hi > lo else 0.0

    # The true pitch is the HIGHEST candidate whose harmonic series explains the spectrum:
    # little energy between its harmonics (an octave too high leaves real partials there),
    # and real energy on them (an octave too low only adds empty odd harmonics, so it is
    # never preferred because we take the highest passing candidate).
    passing = []
    for k in sorted(search):
        m = named + k
        if not 12 <= m <= 120:
            continue
        f = 440 * 2 ** ((m - 69) / 12)
        harm = np.mean([s(f * h) for h in range(1, 9)])
        half = np.mean([s(f * (h - 0.5)) for h in range(1, 9)])
        if harm > 0 and half / harm < 0.25:
            passing.append(m)
    return passing[-1] if passing else named


def measured_cents(x, root):
    """Deviation of the sample from equal temperament at `root`, in cents (from the
    strongest of the first three harmonics, searched within a semitone)."""
    sp, fr = _spectrum(x)
    f = 440 * 2 ** ((root - 69) / 12)
    best = (0.0, 0.0)
    for h in (1, 2, 3):
        lo, hi = np.searchsorted(fr, [f * h * 2 ** (-0.7 / 12), f * h * 2 ** (0.7 / 12)])
        i = lo + int(np.argmax(sp[lo:hi]))
        if sp[i] > best[0]:
            best = (sp[i], 1200 * np.log2(fr[i] / (f * h)))
    return float(best[1])


def steady_cents(x, root):
    """Deviation from equal temperament over the steady part of the note (median YIN pitch), which is what the
    ear hears for short horn notes whose attack bends into the pitch; falls back to the spectral estimate."""
    from audio import pitch_of
    f = pitch_of(x, SR, guess_midi=root)
    if f is None:
        return measured_cents(x, root)
    return float(1200 * np.log2(f / (440 * 2 ** ((root - 69) / 12))))


def folder_zones(files, note_re, layer_key, max_len=8.0, measure=True, extra=None, fine_tune=False, shift=None):
    """Build zones from files: `note_re` captures the note name, `layer_key(path)` gives
    a sortable velocity label (None = skip). Layers spread evenly over velocity 1-127."""
    items = []
    for p in files:
        m = re.search(note_re, os.path.basename(p))
        if not m:
            continue
        lk = layer_key(p)
        if lk is None:
            continue
        items.append((p, note_to_midi(m.group(1)), lk))
    labels = sorted({lk for *_, lk in items})
    n = len(labels)
    bounds = [(1 + round(127 * i / n), round(127 * (i + 1) / n)) for i in range(n)]
    bounds[0] = (1, bounds[0][1])
    loaded = [(p, named, lk, load(p)) for p, named, lk in items]
    # One sample set uses one naming convention, so apply the octave offset most samples
    # measure at. Single notes can mis-measure (bells, weak low fundamentals); the mode can't.
    if shift is None and measure and loaded:
        offs = [measured_root(x, named) - named for _, named, _, x in loaded]
        shift = max(set(offs), key=offs.count)
    shift = shift or 0
    zones, seen = [], set()
    for p, named, lk, x in loaded:
        root = named + shift
        L = labels.index(lk)
        if (root, L) in seen:
            continue
        seen.add((root, L))
        z = dict(audio=x, path=p, root=root, vel=L + 1, lovel=bounds[L][0], hivel=bounds[L][1], max_len=max_len)
        if fine_tune:   # instruments tuned off equal temperament get a per-zone correction
            z["tune"] = -round(steady_cents(x, root))
        if extra:
            z.update(extra(p, root))
        zones.append(z)
    return zones


def key_ranges(roots, stretch=12):
    """Split the keyboard between sorted root notes (midpoints)."""
    roots = sorted(roots)
    out = {}
    for i, r in enumerate(roots):
        lo = 0 if i == 0 else (roots[i - 1] + r) // 2 + 1
        hi = 127 if i == len(roots) - 1 else (r + roots[i + 1]) // 2
        lo = max(lo, r - stretch)
        hi = min(hi, r + stretch)
        out[r] = (lo, hi)
    return out


def to_rate(x, rate):
    if rate == SR:
        return x
    fr = Fraction(rate, SR).limit_denominator(1000)
    return resample_poly(x, fr.numerator, fr.denominator, axis=0).astype(np.float32)


def build_instrument(name, category, source, zones, out_root, loop=False,
                     max_len=8.0, peak_db=-1.0, loop_region=(0.35, 0.9), trim=True,
                     rate=SR, mono=False, floor_db=-60.0, fade_s=0.3, loop_xfade=0.25, loop_mode="wave", norm="peak", rms_db=-16.0, attack_db=None, even_keys=None):
    """zones: list of dicts {audio (array) or path, root, vel (layer index), lovel, hivel}.

    rate: the stored sample rate (32000 or 22050 for sounds with little or nothing above 16 / 11 kHz: synth pads,
    basses); mono: store one channel (the engine's chorus and spread widen it); floor_db: where a one-shot's tail
    is cut (re its peak), then faded over fade_s."""
    assert source in SOURCES, source
    out_dir = os.path.join(out_root, name)
    if os.path.isdir(out_dir):                       # a rebuild replaces the whole instrument
        for f in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, f))
    os.makedirs(out_dir, exist_ok=True)
    processed = []
    for z in zones:
        x = z["audio"] if "audio" in z else load(z["path"])
        if trim:
            x = trim_start(x)
            if attack_db is not None:
                x = tighten_attack(x, attack_db)
        x = fit_length(x, z.get("max_len", max_len), fade_s=0.02 if loop else fade_s, floor_db=floor_db)
        if mono:
            x = np.repeat(x.mean(axis=1, keepdims=True), 2, axis=1)
        x = to_rate(x, rate)
        ls = le = None
        q = None
        if loop:
            if loop_mode == "pitch":
                # try several loop ends and both finders; keep the best waveform match
                best = None
                for e in np.linspace(loop_region[1] - 0.2, loop_region[1], 6):
                    for cand in (find_loop_pitch(x, region=(loop_region[0], e), xfade_s=loop_xfade, sr=rate,
                                                 root=z["root"]),
                                 find_loop(x, region=(loop_region[0], e), xfade_s=loop_xfade, sr=rate)):
                        if (cand[2] - cand[1]) >= 0.6 * rate and (best is None or cand[3] > best[3]):
                            best = cand
                x, ls, le, q = best
            else:
                x, ls, le, q = find_loop(x, region=loop_region, xfade_s=loop_xfade, sr=rate)
        processed.append((z, x, ls, le, q))

    if even_keys:
        # even out note-to-note loudness within each velocity layer (a soft high string recorded much quieter
        # than its neighbours), by at most even_keys dB, towards the layer's median
        by_layer = {}
        for i, (z, x, *_r) in enumerate(processed):
            by_layer.setdefault(z["vel"], []).append(i)
        lim = 10 ** (even_keys / 20)
        for idx in by_layer.values():
            r = np.array([np.sqrt(np.mean(processed[i][1][:int(0.3 * rate)] ** 2)) + 1e-9 for i in idx])
            med = float(np.median(r))
            for i, ri in zip(idx, r):
                z, x, ls, le, q = processed[i]
                processed[i] = (z, x * float(np.clip(med / ri, 1 / lim, lim)), ls, le, q)
    peak_gain = 10 ** (peak_db / 20) / max(np.max(np.abs(x)) for _, x, *_ in processed)
    if norm == "rms":
        # level the instrument by loudness: the loudest layer's median note RMS (first 0.4 s) hits rms_db,
        # so short stabs and long sustains sit at the same loudness; never past the peak limit
        top = max(z["vel"] for z, *_ in processed)
        r = [np.sqrt(np.mean(x[:int(0.4 * rate)] ** 2)) for z, x, *_ in processed if z["vel"] == top]
        gain = min(peak_gain, 10 ** (rms_db / 20) / float(np.median(r)))
    else:
        gain = peak_gain

    layers = {}
    for z, *_ in processed:
        layers.setdefault(z["vel"], []).append(z["root"])
    ranges = {v: key_ranges(r) for v, r in layers.items()}

    entries, total = [], 0
    for z, x, ls, le, q in processed:
        fn = f"{name}_{z['root']:03d}_{midi_name(z['root']).replace('#', 's')}_v{z['vel']}.flac"
        path = os.path.join(out_dir, fn)
        y = np.clip(x * gain, -1, 1)
        sf.write(path, y[:, :1] if mono else y, rate, subtype="PCM_16", format="FLAC")
        size = os.path.getsize(path)
        total += size
        lk, hk = ranges[z["vel"]][z["root"]]
        e = {"file": fn, "root": z["root"], "lokey": lk, "hikey": hk,
             "lovel": z["lovel"], "hivel": z["hivel"], "frames": len(x),
             "orig": os.path.relpath(z["path"], LIB) if "path" in z else "rendered",
             "bytes": size}
        if "tune" in z:
            e["tune"] = z["tune"]
        if loop:
            e.update(loop_start=int(ls), loop_end=int(le), loop_score=round(q, 3))
        entries.append(e)

    keymap = {"name": name, "category": category, "source": source,
              "license": SOURCES[source]["license"], "credit": SOURCES[source]["credit"],
              "samplerate": rate, "loop": loop, "zones": sorted(entries, key=lambda e: (e["lovel"], e["root"])),
              "total_bytes": total}
    json.dump(keymap, open(os.path.join(out_dir, "keymap.json"), "w"), indent=1)
    return keymap


def write_credits(out_root):
    """Regenerate LICENSES.md and a per-file CSV from every keymap in the library."""
    rows, used, sizes = [], {}, {}
    for inst in sorted(os.listdir(out_root)):
        kp = os.path.join(out_root, inst, "keymap.json")
        if not os.path.exists(kp):
            continue
        k = json.load(open(kp))
        used.setdefault(k["source"], []).append(inst)
        sizes[inst] = k["total_bytes"]
        for z in k["zones"]:
            rows.append(f'{inst}/{z["file"]},{k["source"]},{k["license"]},"{z["orig"]}"')
    with open(os.path.join(out_root, "files.csv"), "w") as f:
        f.write("file,source,license,original\n" + "\n".join(rows) + "\n")
    lines = ["# Tropix sound library: sources and licenses", ""]
    for s, insts in used.items():
        src = SOURCES[s]
        lines += [f"## {src['name']}", "", f"- License: {src['license']}",
                  f"- Source: {src['url'] or 'original to this project'}",
                  f"- Credit: {src['credit']}", f"- Used in: {', '.join(insts)}", ""]
    lines += ["Every sample file and its original is listed in files.csv."]
    open(os.path.join(out_root, "LICENSES.md"), "w").write("\n".join(lines) + "\n")
    return sizes
