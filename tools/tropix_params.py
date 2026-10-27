#!/usr/bin/env python3
"""The Tropix parameter list, in one place. Writes vst/params.json (the VST parameters, for mpc-vst-plugins'
gen_vst.py) and src/params.h (the engine's matching enum, keys, defaults, ranges and value formats), plus
src/presets.h from tools/presets.py.

    python3 tools/tropix_params.py

Order is the VST parameter index. Once a version is public, only append (a saved project stores values by index)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pack_tropix import ORDER, TYPES  # noqa: E402

INSTRUMENTS = [d for _, d, _ in ORDER]
LAYERS = "ab"
GENRES = ["ALL", "AFROBEAT", "AMAPIANO", "KOMPA", "SOCA", "REGGAE", "HAWAIIAN"]   # 0 = every genre
LIST_ROWS = 8                       # the BROWSE view's preset list: pages of 8
VIEWS = ["Browse", "Sound", "Settings"]
THEMES = ["Sunset", "Lagos", "Aloha", "Kingston", "Kanaval", "Jozi Night"]   # = make_skin.THEMES, in order
WAVE_FRAMES = 17                    # the SOUND view's waveform: idle + 4 levels x 4 phases
DELAY_TIMES = ["1/16", "1/8T", "1/8", "1/8.", "1/4T", "1/4", "1/4.", "1/2"]
VOICE_MODES = ["Poly", "Mono", "Legato"]
LFO_TARGETS = ["Tremolo", "Filter", "Auto-Pan"]
SCOOPS = ["Off", "Light", "Deep"]
LAYER_CELLS = [("lv", "level", "LEVEL"), ("pn", "pan", "PAN"), ("oc", "octave", "OCTAVE"), ("fn", "fine", "FINE")]

# SETTINGS view: boxes of rows; each row is a tap pad (a tap steps an option, the data wheel moves the value) and
# its value text. (box title, [(param key, row label)])
SETTINGS_BOXES = [
    ("THIS PRESET", [("voice_mode", "VOICE MODE"), ("lfo_target", "LFO TARGET"), ("scoop", "HORN SCOOP")]),
    ("TUNING", [("a4_ref", "A4 REFERENCE"), ("transpose", "TRANSPOSE"), ("bend_range", "BEND RANGE")]),
    ("PLAYING", [("polyphony", "POLYPHONY"), ("vel_curve", "VELOCITY CURVE"), ("vel_sens", "VELOCITY")]),
    ("CONTROL", [("mod_wheel", "MOD WHEEL"), ("spread", "STEREO SPREAD"), ("anim", "WAVE ANIMATION")]),
]
SETTING_KEYS = [k for _, rows in SETTINGS_BOXES for k, _ in rows]


def knob(key, name, default, lo=0.0, hi=1.0, fmt="PCT", integer=False, preset=True):
    return dict(key=key, name=name, kind="knob", min=lo, max=hi, default=default, fmt=fmt, integer=integer, preset=preset)


def option(key, name, options, default, preset=True, fmt="OPT"):
    return dict(key=key, name=name, kind="option", options=options, default=default, preset=preset, fmt=fmt)


def momentary(key, name):
    return dict(key=key, name=name, kind="momentary", step_of=None, delta=0)


def tap(key, name):
    """A tap pad: a tap sends exactly 0 or 1 and does the pad's job; the data wheel, if the pad was the last thing
    touched, nudges it from 0.5 and the engine steps something instead (MPC gives a touched control the wheel)."""
    return dict(key=key, name=name, kind="knob", min=0.0, max=1.0, default=0.5, fmt="TAP", integer=False, preset=False)


def display(key, name, hi, kind="int"):
    return dict(key=key, name=name, kind="display", max=hi, disp=kind)


def text(key, name):
    return display(key, name, 1, "string")


def spec():
    from presets import PRESETS
    P = [knob("volume", "Volume", 0.8, fmt="VOL", preset=False),           # index 0: MPC toggles it on insert / STOP
         option("preset", "Preset", [p["name"] for p in PRESETS], PRESETS[0]["name"], preset=False)]
    P += [tap("prev", "Previous Preset"), tap("next", "Next Preset"), tap("go_browse", "Show Browser"),
          tap("go_sound", "Show Sound"), tap("go_settings", "Show Settings"), tap("fav_tap", "Favourite"),
          tap("favs_tap", "Favourites List"), tap("reset_tap", "Reset Preset"),
          option("view", "View", VIEWS, VIEWS[0], preset=False)]
    P += [knob("cutoff", "Cutoff", 1.0, fmt="CUTOFF"), knob("resonance", "Resonance", 0.0),
          knob("bright", "Bright", 0.5, fmt="BRIGHT"), knob("drive", "Drive", 0.0),
          knob("attack", "Attack", 0.0, fmt="ATTACK"), knob("decay", "Decay", 0.5, fmt="TIME"),
          knob("sustain", "Sustain", 1.0), knob("release", "Release", 0.55, fmt="TIME"),
          knob("glide", "Glide", 0.0, fmt="GLIDE"), knob("vibrato", "Vibrato", 0.0, fmt="VIB"),
          knob("lfo_rate", "LFO Rate", 0.5, fmt="LFO"), knob("lfo_depth", "LFO Depth", 0.0),
          knob("chorus", "Chorus", 0.0), knob("delay", "Delay", 0.0), knob("reverb", "Reverb", 0.2)]
    # preset-only sound settings (no knob of their own)
    P += [knob("env_amt", "Env Amount", 0.5, fmt="BIPOLAR"), knob("key_track", "Key Track", 0.0),
          option("voice_mode", "Voice Mode", VOICE_MODES, "Poly"),
          option("lfo_target", "LFO Target", LFO_TARGETS, "Tremolo"),
          option("scoop", "Horn Scoop", SCOOPS, "Off"),
          option("delay_time", "Delay Time", DELAY_TIMES, "1/8."),
          knob("delay_fb", "Delay Feedback", 0.4), knob("delay_tone", "Delay Tone", 0.55, fmt="TONE"),
          knob("delay_width", "Delay Width", 0.8),
          knob("rev_size", "Reverb Size", 0.6), knob("rev_damp", "Reverb Damping", 0.4),
          knob("rev_predelay", "Reverb Pre-Delay", 0.1, fmt="PREDELAY"), knob("rev_width", "Reverb Width", 1.0),
          knob("trim", "Preset Trim", 0.0, -12.0, 12.0, fmt="DB")]
    for i, l in enumerate(LAYERS):
        L = l.upper()
        P += [option("layer_" + l, "Layer %s" % L, ["Off", "On"], "On" if i == 0 else "Off"),
              option("inst_" + l, "Layer %s Sound" % L, INSTRUMENTS, INSTRUMENTS[0]),
              knob("level_" + l, "Layer %s Level" % L, 0.8, fmt="LEVEL"),
              knob("pan_" + l, "Layer %s Pan" % L, 0.0, -1.0, 1.0, fmt="PAN"),
              knob("octave_" + l, "Layer %s Octave" % L, 0, -3, 3, fmt="OCT", integer=True),
              knob("fine_" + l, "Layer %s Fine" % L, 0, -100, 100, fmt="CENTS", integer=True),
              option("solo_" + l, "Layer %s Solo" % L, ["Off", "On"], "Off", preset=False),
              momentary("inst_%s_prev" % l, "Layer %s Previous" % L),
              momentary("inst_%s_next" % l, "Layer %s Next" % L)]
    P += [knob("a4_ref", "A4 Ref", 440, 400, 480, fmt="HZINT", integer=True, preset=False),
          knob("transpose", "Transpose", 0, -24, 24, fmt="SEMI", integer=True, preset=False),
          knob("bend_range", "Bend Range", 2, 0, 24, fmt="SEMI", integer=True, preset=False),
          knob("polyphony", "Polyphony", 24, 1, 32, fmt="INT", integer=True, preset=False),
          knob("vel_sens", "Velocity", 0.8, preset=False),
          knob("vel_filter", "Vel > Filter", 0.25, preset=False),
          knob("spread", "Spread", 0.3, preset=False),
          option("vel_curve", "Velocity Curve", ["Soft", "Normal", "Hard"], "Normal", preset=False),
          option("mod_wheel", "Mod Wheel", ["Vibrato", "Filter", "Off"], "Vibrato", preset=False),
          option("anim", "Animation", ["Off", "Low", "Smooth"], "Smooth", preset=False),
          option("theme", "Theme", THEMES, THEMES[0], preset=False),
          momentary("theme_prev", "Previous Theme"), momentary("theme_next", "Next Theme")]
    # the data wheel / Q-Link browser: rests at 500; a move up or down steps one preset in the list shown
    P += [knob("browse", "Browse", 500, 0, 1000, fmt="BROWSE", integer=True, preset=False)]
    P += [option("look", "Look", ["%s %s" % (t, v) for t in THEMES for v in VIEWS], "%s %s" % (THEMES[0], VIEWS[0]),
                 preset=False, fmt="LOOK"),
          display("wave", "Waveform", WAVE_FRAMES - 1), display("fav", "Favourite Lit", 1),
          display("favs", "Favourites Shown", 1), display("edited", "Edited", 1), display("midi_led", "MIDI LED", 1),
          display("cpu", "CPU", 10), display("pgenre", "Preset Genre", len(GENRES) - 1),
          display("ptype", "Preset Type", len(TYPES) - 1)]
    P += [display("act_" + l, "Layer %s Active" % l.upper(), 1) for l in LAYERS]
    P += [text(k, n) for k, n in (("hdr_info", "Header Info"), ("desc_1", "Description 1"), ("desc_2", "Description 2"),
                                  ("list_head", "List Heading"), ("cw_name", "Colorway Name"))]
    for l in LAYERS:
        L = l.upper()
        P += [text("lname_" + l, "Layer %s Name" % L)]
        P += [text("%s_%s" % (c, l), "Layer %s %s" % (L, lab.title())) for c, _, lab in LAYER_CELLS]
    P += [text("sv_" + k, "Setting %s" % k) for k in SETTING_KEYS]
    P += [text("gen_%d" % (i + 1), "Genre %d" % (i + 1)) for i in range(len(GENRES))]
    P += [text("typ_%d" % (i + 1), "Type %d" % (i + 1)) for i in range(len(TYPES))]
    P += [text("row_%d" % (i + 1), "List Row %d" % (i + 1)) for i in range(LIST_ROWS)]
    P += [display("fav_%d" % i, "Favourites %d" % (i + 1), 8191) for i in range(10)]
    P += [tap("gpick_%d" % (i + 1), "Genre Pad %d" % (i + 1)) for i in range(len(GENRES))]
    P += [tap("tpick_%d" % (i + 1), "Type Pad %d" % (i + 1)) for i in range(len(TYPES))]
    P += [tap("pick_%d" % (i + 1), "Preset Pad %d" % (i + 1)) for i in range(LIST_ROWS)]
    for l in LAYERS:
        P += [tap("t%s_%s" % (c, l), "Layer %s %s Pad" % (l.upper(), lab.title())) for c, _, lab in LAYER_CELLS]
        P += [tap("tname_" + l, "Layer %s Sound Pad" % l.upper())]
    P += [tap("set_" + k, "Setting Pad %s" % k) for k in SETTING_KEYS]
    P += [tap("sw_%d" % (i + 1), "Colorway Pad %d" % (i + 1)) for i in range(len(THEMES))]
    return P


def to_json(P):
    out = []
    for p in P:
        q = {"key": p["key"], "name": p["name"]}
        if p["kind"] == "knob":
            q.update(min=p["min"], max=p["max"], default=p["default"])
            if p["fmt"] != "TAP":
                q["dynamic_display"] = True
            if p["integer"]:
                q["display"] = "int"
        elif p["kind"] == "option":
            q.update(options=p["options"], default=p["default"])
            if p["key"] == "preset":
                q["qlink_ticks"] = 2
        elif p["kind"] == "momentary":
            q["momentary"] = True
        else:
            q.update(min=0, max=p["max"], default=0, display=p["disp"])
        out.append(q)
    return {"name": "Tropix", "params": out}


def cf(x):
    """A C float literal."""
    return "%.6gf" % x if "." in "%.6g" % x or "e" in "%.6g" % x else "%.6g.0f" % x


def c_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_header(P):
    L = ["/* Generated by tools/tropix_params.py: the engine's parameters (same order as vst/params.json). */",
         "enum {"]
    for p in P:
        L.append("    P_%s," % p["key"].upper())
    L += ["    NP", "};"]
    L.append("static const char *const PKEY[NP] = {\n" + "".join("    %s,\n" % c_str(p["key"]) for p in P) + "};")
    L.append("static const char *const PNAME[NP] = {\n" + "".join("    %s,\n" % c_str(p["name"].upper()) for p in P) + "};")
    kinds = {"knob": "K_KNOB", "option": "K_OPTION", "momentary": "K_MOMENTARY", "display": "K_DISPLAY"}
    L.append("enum { K_KNOB, K_OPTION, K_MOMENTARY, K_DISPLAY, K_TEXT };")
    fmts = sorted({p.get("fmt", "NONE") for p in P} | {"NONE"})
    L.append("enum { " + ", ".join("F_" + f for f in fmts) + " };")
    rows = []
    for p in P:
        kind = kinds[p["kind"]] if not (p["kind"] == "display" and p.get("disp") == "string") else "K_TEXT"
        if p["kind"] == "knob":
            lo, hi, d = p["min"], p["max"], p["default"]
        elif p["kind"] == "option":
            lo, hi, d = 0, len(p["options"]) - 1, p["options"].index(p["default"])
        elif p["kind"] == "display":
            lo, hi, d = 0, p["max"], 0
        else:
            lo, hi, d = 0, 1, 0
        rows.append("    { %s, F_%s, %s, %s, %s, %d, %d },  /* %s */" % (
            kind, p.get("fmt", "NONE"), cf(lo), cf(hi), cf(d), int(bool(p.get("integer")) or p["kind"] == "option"),
            int(bool(p.get("preset"))), p["key"]))
    L.append("typedef struct { int kind, fmt; float lo, hi, def; int whole, in_preset; } pinfo_t;")
    L.append("static const pinfo_t PINFO[NP] = {\n" + "\n".join(rows) + "\n};")
    opts = [p for p in P if p["kind"] == "option" and p["key"] not in ("preset", "look") and not p["key"].startswith("inst_")]
    L.append("/* option labels (for the SETTINGS rows and the colorway name) */")
    for p in opts:
        L.append("static const char *const OPT_%s[] __attribute__((unused)) = { %s };" % (
            p["key"].upper(), ", ".join(c_str(o.upper()) for o in p["options"])))
    okeys = {p["key"] for p in opts}
    L.append("static const char *const *const OPT_OF[NP] = {\n" + "".join(
        "    %s,\n" % ("OPT_" + p["key"].upper() if p["key"] in okeys else "0") for p in P) + "};")
    L.append("#define LIST_ROWS %d" % LIST_ROWS)
    L.append("#define NTHEME %d" % len(THEMES))
    L.append("#define NVIEW %d" % len(VIEWS))
    L.append("#define NGENRE %d" % len(GENRES))
    L.append("static const char *const GENRE_NAME[NGENRE] = { %s };" % ", ".join(c_str(g) for g in GENRES))
    L.append("#define NSETTING %d" % len(SETTING_KEYS))
    L.append("static const int SETTING_PARAM[NSETTING] = { %s };" % ", ".join("P_" + k.upper() for k in SETTING_KEYS))
    L.append("#define NDELAY_TIMES %d" % len(DELAY_TIMES))
    L.append("static const float DELAY_BEATS[NDELAY_TIMES] = { 0.25f, 1.0f / 3, 0.5f, 0.75f, 2.0f / 3, 1.0f, 1.5f, 2.0f };")
    return "\n".join(L) + "\n"


def main():
    P = spec()
    keys = [p["key"] for p in P]
    assert len(keys) == len(set(keys))
    with open(os.path.join(REPO, "vst", "params.json"), "w") as f:
        json.dump(to_json(P), f, indent=2)
        f.write("\n")
    with open(os.path.join(REPO, "src", "params.h"), "w") as f:
        f.write(to_header(P))
    import presets
    presets.write_header(P, os.path.join(REPO, "src", "presets.h"))
    print("%d parameters, %d presets" % (len(P), len(presets.PRESETS)))


if __name__ == "__main__":
    main()
