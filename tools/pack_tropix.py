#!/usr/bin/env python3
"""Pack the prepared library (library/<instrument>/keymap.json + FLAC) into the files the Tropix engine loads.

    python3 -I tools/pack_tropix.py [instrument ...]

Writes engine/<instrument>.tpx (one per instrument), src/instruments.h (the engine's instrument table) and
engine/LIBRARY_VERSION. The engine reads every instrument into RAM in the background when Tropix first opens.

Sample file "TPXB" v1 (read by src/engine.c, "sample file"); the layout is Sonix's SNXB:
  header (32 bytes): "TPXB", u32 version 1, u32 samples, u32 zones, u32 data offset, u32 flags (1 = mono, 2 = kit),
                     f32 level trim, u32 sample rate (44100)
  per sample (16 bytes): u32 byte offset into data, u32 frames, u32 loop start, u32 loop end (0 = one-shot)
  per zone (12 bytes): u8 lokey, hikey, root, lovel, hivel, pad; i16 tune (cents); u32 sample index
  data, per sample: u32 len0, u32 len1, then the left and right bitstreams.
The bitstream codec is Fretty's (3dthc/fretty-mpc, MIT): lossless 16-bit, 1024-frame blocks, a header byte
(order << 5 | k), then one Rice code per frame of the zigzagged residual of a fixed order-0..3 predictor.
A kit (one sound per key) plays each key's own sample unpitched; keys without a sound are silent.
"""
import json
import os
import struct
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LIB = os.path.join(REPO, "library")
ENGINE = os.path.join(REPO, "engine")

TYPES = ["KEYS", "GUITARS", "HORNS", "STEEL PAN", "MALLETS", "BASS", "PERCUSSION", "SYNTHS & FX"]

# The instrument list, in type order: (file, display name, type). Names describe the sound, not a maker's product.
ORDER = [
    ("grand_piano", "Grand Piano", "KEYS"), ("upright_piano", "Upright Piano", "KEYS"),
    ("tine_piano", "Tine E-Piano", "KEYS"), ("wurlitzer", "Reed E-Piano", "KEYS"),
    ("cp80", "Electric Grand", "KEYS"), ("pianet", "Pluck E-Piano", "KEYS"), ("fm_keys", "FM Keys", "KEYS"),
    ("organ_bubble", "Organ Bubble", "KEYS"), ("organ_perc", "Organ Perc", "KEYS"), ("organ_full", "Organ Full", "KEYS"),
    ("gretsch", "Hollow Electric", "GUITARS"), ("gretsch_mute", "Hollow Muted", "GUITARS"),
    ("hofner", "Archtop Electric", "GUITARS"), ("hofner_mute", "Archtop Muted", "GUITARS"),
    ("slack_key", "Slack-Key Steel", "GUITARS"), ("palm_wine", "Palm-Wine Nylon", "GUITARS"),
    ("ukulele", "Ukulele", "GUITARS"), ("pedal_steel", "Pedal Steel", "GUITARS"), ("lap_steel", "Lap Steel", "GUITARS"),
    ("trumpet", "Trumpet", "HORNS"), ("trumpet_bright", "Bright Trumpet", "HORNS"),
    ("trumpet_bright_vib", "Bright Trumpet Vibrato", "HORNS"), ("trumpet_stab", "Trumpet Stab", "HORNS"),
    ("trumpet_harmon", "Harmon Trumpet", "HORNS"), ("trombone", "Trombone", "HORNS"),
    ("trombone_stab", "Trombone Stab", "HORNS"), ("trombone_fall", "Trombone Fall", "HORNS"),
    ("alto_sax", "Alto Sax", "HORNS"), ("alto_sax_vib", "Alto Sax Vibrato", "HORNS"),
    ("tenor_sax", "Tenor Sax", "HORNS"), ("tenor_sax_vib", "Tenor Sax Vibrato", "HORNS"),
    ("tenor_sax_stab", "Tenor Sax Stab", "HORNS"), ("soprano_sax", "Soprano Sax", "HORNS"),
    ("soprano_sax_vib", "Soprano Sax Vibrato", "HORNS"), ("harmonica", "Harmonica", "HORNS"),
    ("harmonica_vib", "Harmonica Vibrato", "HORNS"), ("melodica", "Melodica", "HORNS"),
    ("pan_tenor", "Tenor Pan", "STEEL PAN"), ("pan_double_second", "Double Second Pan", "STEEL PAN"),
    ("pan_cello", "Cello Pan", "STEEL PAN"), ("pan_bass", "Bass Pan", "STEEL PAN"), ("pan_roll", "Pan Roll", "STEEL PAN"),
    ("marimba", "Marimba", "MALLETS"), ("balafon", "Balafon", "MALLETS"), ("vibraphone", "Vibraphone", "MALLETS"),
    ("kalimba", "Kalimba", "MALLETS"), ("mbira", "Mbira", "MALLETS"),
    ("flat_bass", "Flatwound Bass", "BASS"), ("finger_bass", "Finger Bass", "BASS"),
    ("finger_bass_short", "Finger Bass Short", "BASS"), ("sub_bass", "Sub Bass", "BASS"),
    ("logdrum_classic", "Log Drum Classic", "BASS"), ("logdrum_deep", "Log Drum Deep", "BASS"),
    ("logdrum_knock", "Log Drum Knock", "BASS"), ("logdrum_talking", "Log Drum Talking", "BASS"),
    ("logdrum_gritty", "Log Drum Gritty", "BASS"),
    ("island_perc", "Island Percussion", "PERCUSSION"), ("west_africa", "West African Drums", "PERCUSSION"),
    ("timbales", "Timbales", "PERCUSSION"), ("ipu", "Ipu", "PERCUSSION"),
    ("soca_lead", "Soca Lead", "SYNTHS & FX"), ("soca_brass", "Soca Brass", "SYNTHS & FX"),
    ("afro_pluck", "Afro Pluck", "SYNTHS & FX"), ("piano_pluck", "Piano Pluck", "SYNTHS & FX"),
    ("island_pad", "Island Pad", "SYNTHS & FX"),
]
KITS = {"island_perc", "west_africa", "timbales", "ipu"}

LIBRARY_VERSION = "0.2.0"   # written to engine/LIBRARY_VERSION; install.sh repacks the instruments when it differs

REF_DB = -20.0      # every instrument is trimmed so its typical loud-note attack sits near this loudness,
LAYER_KEEP = 1 / 3  # velocity layers keep this share of their natural loudness gap (their tone stays): the engine's
                    # velocity curve makes the dynamics, so playing softer gets quieter smoothly, with no jump at a layer
PEAK_MAX = 0.4      # unless that would push a single hard-played note's peak above this (a 4-note chord then stays
                    # clear of the output limiter: plucked and struck sounds have a high peak for their loudness)


# ------------------------------------------------------------------ codec (from Fretty's tools/pack_samples.py)
BLOCK = 1024
ESC_Q = 24


def residuals(x, order):
    p = np.concatenate([np.zeros(3, np.int64), x])
    n = len(x)
    if order == 0:
        return x.copy()
    if order == 1:
        return p[3:] - p[2:2 + n]
    if order == 2:
        return p[3:] - 2 * p[2:2 + n] + p[1:1 + n]
    return p[3:] - 3 * p[2:2 + n] + 3 * p[1:1 + n] - p[0:n]


def encode_channel(x):
    """int64 samples -> bytes: per 1024-frame block a header byte (order << 5 | k), then Rice-coded residuals."""
    n = len(x)
    nb = (n + BLOCK - 1) // BLOCK
    best_cost = np.full(nb, np.inf)
    best_u = np.zeros(n, np.uint64)
    best_k = np.zeros(nb, np.int64)
    best_o = np.zeros(nb, np.int64)
    pad = nb * BLOCK - n
    for order in range(4):
        r = residuals(x, order)
        u = np.where(r >= 0, 2 * r, -2 * r - 1).astype(np.int64)
        ub = np.concatenate([u, np.zeros(pad, np.int64)]).reshape(nb, BLOCK)
        order_cost = np.full(nb, np.inf)
        order_k = np.zeros(nb, np.int64)
        for k_value in range(21):
            q = ub >> k_value
            cost = np.where(q >= ESC_Q, ESC_Q + 20, q + 1 + k_value)
            cost[-1, BLOCK - pad:] = 0
            cost = cost.sum(1) + 8
            better_k = cost < order_cost
            order_cost = np.where(better_k, cost, order_cost)
            order_k = np.where(better_k, k_value, order_k)
        better = order_cost < best_cost
        best_cost = np.where(better, order_cost, best_cost)
        best_k = np.where(better, order_k, best_k)
        best_o = np.where(better, order, best_o)
        sel = np.repeat(better, BLOCK)[:n]
        best_u = np.where(sel, u.astype(np.uint64), best_u)
    kk = np.repeat(best_k, BLOCK)[:n].astype(np.uint64)
    q = best_u >> kk
    esc = q >= ESC_Q
    L_res = np.where(esc, ESC_Q + 20, q + 1 + kk).astype(np.int64)
    V_res = np.where(esc, best_u, (np.uint64(1) << kk) | (best_u & ((np.uint64(1) << kk) - np.uint64(1))))
    starts = np.arange(nb) * BLOCK
    L = np.insert(L_res, starts, 8)
    V = np.insert(V_res, starts, ((best_o << 5) | best_k).astype(np.uint64))
    end = np.cumsum(L) - 1
    total = int(end[-1]) + 1
    words = np.zeros(total // 64 + 2, np.uint64)
    w = end // 64
    s = (63 - end % 64).astype(np.uint64)
    np.bitwise_or.at(words, w, V << s)
    hi_mask = s > 0
    np.bitwise_or.at(words, w[hi_mask] - 1, V[hi_mask] >> (np.uint64(64) - s[hi_mask]))
    return words.astype(">u8").tobytes()[:(total + 7) // 8]


# ------------------------------------------------------------------ packing
def attack_db(audio, rate=44100):
    """Loudness of the loudest half second (the attack for most sounds)."""
    x = audio.astype(np.float64) / 32768
    w = int(0.5 * rate)
    best = -120.0
    for s in range(0, max(1, len(x) - w + 1), w // 2):
        best = max(best, 10 * np.log10(np.mean(x[s:s + w] ** 2) + 1e-12))
    return best


def level_layers(samples, zones, rate):
    """Bring each softer velocity layer up toward the loudest layer of the same note (same root), keeping LAYER_KEEP of
    the natural gap; scaled in place (never past full scale)."""
    by_root = {}
    for z in zones:
        by_root.setdefault(z[2], []).append(z)
    for root, zs in by_root.items():
        if len({(z[3], z[4]) for z in zs}) < 2:
            continue
        top = max(zs, key=lambda z: z[4])
        ref = attack_db(samples[top[6]][0], rate)
        for z in zs:
            if z is top:
                continue
            a, ls, le = samples[z[6]]
            gap = ref - attack_db(a, rate)
            if gap <= 0.5:
                continue
            g = 10 ** (gap * (1 - LAYER_KEEP) / 20)
            g = min(g, 32000 / max(1, np.abs(a.astype(np.int32)).max()))
            samples[z[6]] = (np.round(a.astype(np.float64) * g).clip(-32768, 32767).astype(np.int16), ls, le)


def pack(name):
    k = json.load(open(os.path.join(LIB, name, "keymap.json")))
    rate = k["samplerate"]
    assert rate == 44100, name
    samples, zones, levels, peaks = [], [], [], []
    mono = True
    for z in k["zones"]:
        a, sr = sf.read(os.path.join(LIB, name, z["file"]), dtype="int16", always_2d=True)
        assert sr == rate
        if a.shape[1] == 1:
            a = np.repeat(a, 2, axis=1)
        if not np.array_equal(a[:, 0], a[:, 1]):
            mono = False
        ls, le = (z.get("loop_start", 0), z.get("loop_end", 0)) if k["loop"] else (0, 0)
        if le:
            a = a[:le]
        idx = len(samples)
        samples.append((a, ls, le))
        zones.append((z["lokey"], z["hikey"], z["root"], z["lovel"], z["hivel"], int(z.get("tune", 0)), idx))
        if z["hivel"] >= 100:
            levels.append(attack_db(a, rate))
            peaks.append(np.abs(a.astype(np.int32)).max() / 32768)
    level_layers(samples, zones, rate)
    levels = [attack_db(samples[z[6]][0], rate) for z in zones if z[4] >= 100]
    peaks = [np.abs(samples[z[6]][0].astype(np.int32)).max() / 32768 for z in zones if z[4] >= 100]
    gain = float(np.clip(10 ** ((REF_DB - np.median(levels)) / 20), 0.25, 8.0)) if levels else 1.0
    if peaks:
        gain = min(gain, PEAK_MAX / np.percentile(peaks, 90))

    data = bytearray()
    ents = []
    for a, ls, le in samples:
        c0 = encode_channel(a[:, 0].astype(np.int64))
        c1 = b"" if mono else encode_channel(a[:, 1].astype(np.int64))
        ents.append((len(data), len(a), ls, le))
        data += struct.pack("<II", len(c0), len(c1)) + c0 + c1
    ns, nz = len(samples), len(zones)
    doff = 32 + ns * 16 + nz * 12
    flags = (1 if mono else 0) | (2 if name in KITS else 0)
    out = bytearray(b"TPXB" + struct.pack("<IIIIIfI", 1, ns, nz, doff, flags, gain, rate))
    for e in ents:
        out += struct.pack("<IIII", *e)
    for lo, hi, root, lv, hv, tune, idx in zones:
        out += struct.pack("<BBBBBBhI", lo, hi, root, lv, hv, 0, tune, idx)
    assert len(out) == doff
    out += data
    path = os.path.join(ENGINE, name + ".tpx")
    with open(path + ".new", "wb") as f:
        f.write(out)
    os.replace(path + ".new", path)
    return len(out), gain, mono


def write_tables():
    names = [n for n, _, _ in ORDER]
    assert sorted(names) == sorted(d for d in os.listdir(LIB) if os.path.isdir(os.path.join(LIB, d))), "ORDER != library"
    with open(os.path.join(REPO, "src", "instruments.h"), "w") as f:
        f.write("/* Generated by tools/pack_tropix.py: the instrument list (engine/<file>.tpx), in type order. */\n")
        f.write(f"#define NINST {len(names)}\n")
        f.write("static const char *INST_FILE[NINST] = {\n" + "".join(f'    "{n}",\n' for n in names) + "};\n")
        f.write("static const char *INST_NAME[NINST] = {\n" + "".join(f'    "{d}",\n' for _, d, _ in ORDER) + "};\n")
        f.write(f"#define NTYPE {len(TYPES)}\n")
        f.write("static const char *TYPE_NAME[NTYPE] = { " + ", ".join(f'"{c}"' for c in TYPES) + " };\n")
        f.write("static const unsigned char INST_TYPE[NINST] = { " + ", ".join(str(TYPES.index(t)) for _, _, t in ORDER) + " };\n")


def main():
    os.makedirs(ENGINE, exist_ok=True)
    want = sys.argv[1:] or [n for n, _, _ in ORDER]
    total = 0
    for n in want:
        size, gain, mono = pack(n)
        total += size
        print(f"{n:20s} {size / 1e6:6.1f} MB  trim {gain:5.2f}{'  mono' if mono else ''}", flush=True)
    write_tables()
    if not sys.argv[1:]:
        with open(os.path.join(ENGINE, "LIBRARY_VERSION"), "w") as f:
            f.write(LIBRARY_VERSION + "\n")
    print(f"packed {len(want)} instruments, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
