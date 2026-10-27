#!/usr/bin/env python3
"""Tropix faceplate: draws every picture the skin uses (vst/art/<colorway>/...) and writes vst/layout.conf.

    python3 tools/make_skin.py               (needs Playwright's Chromium; fonts from vst/fonts)
    python3 tools/make_skin.py --mockup DIR  (full-page renders of every view and colorway, live text included)

One page (MAIN), three views on its screen: BROWSE (genre, type and preset lists), LAYERS (the two layers) and
SETTINGS, in six colorways. A background per colorway and view is chosen by "look" (theme x view); live text is
MPC's own (Titillium Web, the only family it draws besides Roboto), everything else is baked into the pictures
(Pacifico, Outfit and Barlow Semi Condensed, SIL OFL). The 16 knobs keep their place in every view, as the four
Q-Link columns; the 16th Q-Link browses presets (MPC's track has its own volume).

The artwork is HTML/CSS (the approved mockups, tools/ui_mockup.py) rendered by headless Chromium. Overlays (lit
buttons, chips, list rows, meters) are composited onto a crop of their own background, so MPC never has to blend
them; only the knob filmstrip keeps its transparency."""
import base64
import io
import json
import math
import os
import shutil
import sys

from PIL import Image, ImageFont
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ui_mockup as M  # noqa: E402
from pack_tropix import TYPES  # noqa: E402
from tropix_params import GENRES, LAYER_CELLS, LIST_ROWS, SETTINGS_BOXES, THEMES as THEME_LABELS, VIEWS, WAVE_FRAMES  # noqa: E402

VST = os.path.join(HERE, "..", "vst")
ART = os.path.join(VST, "art")
MPC_FONTS = os.path.join(os.environ.get("MPC_VST", os.path.join(HERE, "..", "..", "mpc-vst-plugins")), "tools",
                         "html_art", "fonts")
VERSION = "0.1.0"
Y_OFF = 86
W, H = 1280, 628
THEMES = ["sunset", "lagos", "aloha", "jamaica", "rasta", "haiti", "africa", "kanaval", "jozi"]          # = the "theme" options, in order
assert len(THEMES) == len(THEME_LABELS)
T = {k: M.THEMES[k] for k in THEMES}
JUCE_H = 1.521                       # MPC's Label height = 1.521 x the letter size (Titillium Web's whole line)


def jh(px):
    return int(round(px * JUCE_H))


def hx(c):
    return c.lstrip("#")


# ---------------------------------------------------------------- geometry (plugin-area pixels)
BTN_W, BTN_H, BTN_GAP = 108, 47, 8   # every button one size (the picture is BTN_W x BTN_H + 4: its drop shadow)
KNOB_R = 36                          # every knob one size; the filmstrip frame is 2r + 10
VALUE_PX = 24
SIDE_W, PANEL_H = 268, 303
LX, RX = 8, W - 8 - SIDE_W           # 8, 1004
PANEL_Y = (8, 317)
KCOL, KROW = (70, 198), (88, 223)    # knob centres inside a panel
SECTIONS = [  # (x, y, title, icon, [(key, label)]) -- list order = Q-Link order, one column of four each
    (LX, PANEL_Y[0], "TONE", "sun", [("cutoff", "CUTOFF"), ("resonance", "RESO"), ("bright", "BRIGHT"), ("drive", "DRIVE")]),
    (LX, PANEL_Y[1], "ENVELOPE", "wave", [("attack", "ATTACK"), ("decay", "DECAY"), ("sustain", "SUSTAIN"), ("release", "RELEASE")]),
    (RX, PANEL_Y[0], "MOTION", "palm", [("glide", "GLIDE"), ("vibrato", "VIBRATO"), ("lfo_rate", "LFO RATE"), ("lfo_depth", "LFO DEPTH")]),
    (RX, PANEL_Y[1], "SPACE", "hibiscus", [("chorus", "CHORUS"), ("delay", "DELAY"), ("reverb", "REVERB"), ("volume", "VOLUME")]),
]
QLINKS = [k for *_, ks in SECTIONS for k, _ in ks][:15] + ["browse"]

CX0, CW = 284, 712                   # the centre column
SCR = (284, 74, 712, 486)            # the screen
MIDI_LED = (838, 33, 16)             # cx, cy, size
CPU = (902, 29, 64, 8)               # x, y, w, h
PREV = (300, 88)
NEXT = (CX0 + CW - 16 - BTN_W, 88)
CHIP_G = (394, 87, 132, 26)          # genre chip box (chip right-aligned in it)
CHIP_T = (532, 87, 150, 26)          # type chip box (left-aligned)
HDR_INFO = (690, 86, 176, 28)
NAME = (420, 114, 440, 50)
RULE_Y = 170
# BROWSE
COL1, COL2, COL3 = 286, 454, 630     # column left edges (COL3 runs to the screen's right)
HEAD_Y = 180
LIST_Y, ROW_TH, ROW_GAP = 212, 40, 1
# per list: (text key, highlight display key, highlight x, w, text x, rows, text px); a highlight sits 8 px inside its
# column and 3 px clear of the rows above and below, so it never touches an edge or a neighbour
LISTS = [("gen", "sel_genre", COL1 + 8, COL2 - COL1 - 16, COL1 + 42, len(GENRES), 23),
         ("typ", "sel_type", COL2 + 8, COL3 - COL2 - 16, COL2 + 20, len(TYPES), 23),
         ("row", "sel_row", COL3 + 8, SCR[0] + SCR[2] - 10 - COL3 - 8, COL3 + 20, LIST_ROWS, 24)]
HL_INSET = 3
LIST_HEAD = (646, HEAD_Y, 336, 26)
# SOUND
WAVE = (306, 178, 668, 70)
CARD_Y = (254, 374)
CARD_X, CARD_W, CARD_H = 306, 668, 112
DESC_Y = (496, 524)
# SETTINGS
BOX_X = (302, 646)
BOX_W = 332
BOX_Y = (86, 270)
BOX_H = 176
ROW_H, ROW_Y0 = 44, 34               # a settings row's height, the first row's top inside its box
CW_BOX = (302, 456, 676, 96)
# the buttons along the foot
FOOT_Y = 571
FOOT_STRIP_H = 54                    # >= BTN_W / 2: the skin tool reads a strip as stacked only when it is taller than wide
FOOT = [("go_browse", "BROWSE", 284), ("go_layers", "LAYERS", 400), ("fav_tap", "★ FAV", 516),
        ("favs_tap", "★ LIST", 632), ("go_settings", "SETTINGS", 772), ("reset_tap", "RESET", 888)]
GENRE_DOTS = ["var(--ink)", "#e8a33d", "#b06cff", "#ff3b4f", "#ffd23f", "#2fa84f", "#ff5d8f"]


def knob_centres():
    for x, y, title, icon, ks in SECTIONS:
        for i, (k, lab) in enumerate(ks):
            yield k, lab, x + KCOL[i % 2], y + KROW[i // 2]


def card(l):
    """layer l's card: its box, and the boxes of everything on it"""
    x, y = CARD_X, CARD_Y[l]
    r1, r2 = y + 8, y + 8 + BTN_H + 6
    d = dict(box=(x, y, CARD_W, CARD_H), badge=(x + 14, r1 + 8, 30, 30), name=(x + 54, r1, 400, BTN_H),
             prev=(x + CARD_W - 14 - 2 * BTN_W - BTN_GAP, r1), next=(x + CARD_W - 14 - BTN_W, r1),
             on=(x + 14, r2), solo=(x + 14 + BTN_W + BTN_GAP, r2), cells=[])
    cx0 = x + 14 + 2 * (BTN_W + BTN_GAP) + 4
    cw = (x + CARD_W - 14 - cx0 - 3 * 6) // 4
    for i in range(4):
        d["cells"].append((cx0 + i * (cw + 6), r2, cw, BTN_H))
    return d


def setting_rows():
    """(box x, box y, title, [(key, label, row box)])"""
    out = []
    for b, (title, rows) in enumerate(SETTINGS_BOXES):
        bx, by = BOX_X[b % 2], BOX_Y[b // 2]
        out.append((bx, by, title, [(k, lab, (bx + 8, by + ROW_Y0 + i * (ROW_H + 2), BOX_W - 16, ROW_H))
                                    for i, (k, lab) in enumerate(rows)]))
    return out


def cw_parts():
    """the colorway row: arrows either side of the name, centred under its title"""
    x, y, w, h = CW_BOX
    cy = y + 34 + (h - 34) // 2 - 2
    name = (640 - 130, cy - 22, 260, 44)
    prev = (name[0] - 8 - BTN_W, cy - BTN_H // 2)
    nxt = (name[0] + name[2] + 8, cy - BTN_H // 2)
    return prev, name, nxt


# ---------------------------------------------------------------- HTML
def font_faces():
    f = M.font_url
    return (f"@font-face{{font-family:Pacifico;src:url({f('Pacifico-Regular.ttf')})}}"
            f"@font-face{{font-family:Outfit;src:url({f('Outfit-Variable.ttf')});font-weight:100 900}}"
            f"@font-face{{font-family:Barlow;src:url({f('BarlowSemiCondensed-SemiBold.ttf')});font-weight:600}}"
            f"@font-face{{font-family:Barlow;src:url({f('BarlowSemiCondensed-Bold.ttf')});font-weight:700}}"
            + "".join(f"@font-face{{font-family:Titillium;src:url(data:font/ttf;base64,"
                      f"{base64.b64encode(open(os.path.join(MPC_FONTS, 'TitilliumWeb-%s.ttf' % n), 'rb').read()).decode()});"
                      f"font-weight:{w}}}" for n, w in (("Regular", 400), ("SemiBold", 600), ("Bold", 700))))


FONTS_CSS = None


def css_vars(th):
    return ";".join(f"--{k}:{v}" for k, v in T[th].items() if k not in ("label", "flag"))


BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:transparent;font-family:Barlow,sans-serif;color:var(--ink);overflow:hidden}
.abs{position:absolute}
.btn{position:absolute;border-radius:12px;display:flex;align-items:center;justify-content:center;gap:6px;
  font:700 19px Barlow;letter-spacing:2px;color:var(--ink);
  background:linear-gradient(180deg,color-mix(in srgb,var(--panel) 80%,#fff 14%),color-mix(in srgb,var(--panel) 92%,#000 8%));
  box-shadow:0 4px 0 rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.12), inset 0 0 0 1px color-mix(in srgb,var(--ink) 12%,transparent)}
.btn.on{background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 92%,#fff 8%),color-mix(in srgb,var(--accent) 80%,#000 20%));
  color:#140b05;box-shadow:0 4px 0 rgba(0,0,0,.45),0 0 16px color-mix(in srgb,var(--accent) 60%,transparent)}
.btn.edit{box-shadow:0 4px 0 rgba(0,0,0,.45), inset 0 0 0 2px var(--accent2), 0 0 10px color-mix(in srgb,var(--accent2) 45%,transparent);color:var(--accent2)}
.sbtn{position:absolute;border-radius:12px;display:grid;place-items:center;font:700 19px Barlow;letter-spacing:2px;color:var(--ink);
  background:color-mix(in srgb,var(--ink) 8%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 16%,transparent)}
.sbtn.big{font-size:24px}
.sbtn.lit{background:color-mix(in srgb,var(--accent) 85%,#000 5%);color:#140b05;box-shadow:0 0 12px color-mix(in srgb,var(--accent) 55%,transparent)}
.sbtn.lit2{background:var(--accent2);color:#04110f}
.chip{position:absolute;top:0;height:26px;line-height:26px;padding:0 11px;border-radius:999px;font:700 16px Barlow;letter-spacing:2px;
  background:color-mix(in srgb,var(--accent) 25%,transparent);color:var(--accent)}
.chip.c2{background:color-mix(in srgb,var(--accent2) 22%,transparent);color:var(--accent2)}
.row{position:absolute;border-radius:10px}
.row.sel{background:linear-gradient(90deg,color-mix(in srgb,var(--accent) 38%,transparent),color-mix(in srgb,var(--accent) 14%,transparent));
  box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 55%,transparent)}
"""


def page(th, body, w=W, h=H, extra_css=""):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{FONTS_CSS}:root{{{css_vars(th)}}}{BASE_CSS}"
            f"{extra_css}</style></head><body style='width:{w}px;height:{h}px'>{body}</body></html>")


def icon(name, color):
    svg = {"sun": M.SUN, "palm": M.PALM, "hibiscus": M.HIBISCUS,
           "wave": M.WAVE.replace('viewBox="0 0 120 20"', 'viewBox="0 -40 120 100"')}[name]
    return M.svg_url(svg, color)


def button_html(x, y, text, cls=""):
    return f"<div class='btn {cls}' style='left:{x}px;top:{y}px;width:{BTN_W}px;height:{BTN_H}px'><span>{text}</span></div>"


def sbtn_html(x, y, text, cls="", w=BTN_W, h=BTN_H):
    return f"<div class='sbtn {cls}' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px'>{text}</div>"


def chassis_html(th, view):
    """Everything around the screen, and the screen's frame and header: the same in every view."""
    t = T[th]
    out = []
    palm = M.svg_url(M.PALM, t["sym"])
    out.append(f"""<div class='abs' style='inset:0;
  background:radial-gradient(900px 520px at 50% 58%, color-mix(in srgb,var(--bg2) 85%,transparent), transparent 70%),
             linear-gradient(180deg, color-mix(in srgb,var(--bg) 92%,#fff 8%), var(--bg))'></div>
<div class='abs' style='inset:0;opacity:.07;mix-blend-mode:overlay;background-image:url("data:image/svg+xml;utf8,<svg xmlns=%27http://www.w3.org/2000/svg%27 width=%27160%27 height=%27160%27><filter id=%27n%27><feTurbulence type=%27fractalNoise%27 baseFrequency=%27.9%27 numOctaves=%272%27 stitchTiles=%27stitch%27/></filter><rect width=%27160%27 height=%27160%27 filter=%27url(%23n)%27/></svg>")'></div>
<div class='abs' style='left:-38px;top:430px;width:150px;height:150px;opacity:.10;transform:rotate(12deg);background:url({palm}) center/contain no-repeat'></div>
<div class='abs' style='left:1170px;top:-30px;width:150px;height:150px;opacity:.10;transform:scaleX(-1) rotate(10deg);background:url({palm}) center/contain no-repeat'></div>""")
    # side panels: frames, titles with their motif, knob labels (the knobs themselves are the filmstrip)
    for x, y, title, ic, ks in SECTIONS:
        out.append(f"<div class='abs' style='left:{x}px;top:{y}px;width:{SIDE_W}px;height:{PANEL_H}px;border-radius:18px;"
                   f"background:color-mix(in srgb,var(--panel) 92%,#fff 3%);box-shadow:inset 0 0 0 1.2px color-mix(in srgb,var(--ink) 12%,transparent)'></div>")
        out.append(f"<div class='abs' style='left:{x}px;top:{y + 7}px;width:{SIDE_W}px;display:flex;justify-content:center;"
                   f"align-items:center;gap:8px;font:700 16px Barlow;letter-spacing:3px;color:var(--accent)'>"
                   f"<img src='{icon(ic, t['accent'])}' style='width:20px;height:20px'>{title}</div>")
        for i, (k, lab) in enumerate(ks):
            cx, cy = x + KCOL[i % 2], y + KROW[i // 2]
            out.append(f"<div class='abs' style='left:{cx - 64}px;top:{cy - KNOB_R - 26}px;width:128px;text-align:center;"
                       f"font:600 19px Barlow;letter-spacing:1.2px;color:var(--ink)'>{lab}</div>")
    # header: logo, MIDI and CPU captions, the wave line
    sun = icon("sun", t["accent"])
    out.append(f"""<div class='abs' style='left:284px;top:6px;height:54px;display:flex;align-items:center'>
<div style='font-family:Pacifico;font-size:38px;line-height:1;color:var(--ink);position:relative;padding-left:46px;
  text-shadow:0 2px 0 rgba(0,0,0,.35),0 0 18px color-mix(in srgb,var(--accent) 45%,transparent)'>
<img src='{sun}' style='position:absolute;left:0;top:6px;width:40px;height:40px;filter:drop-shadow(0 0 6px var(--accent))'>Tropix</div></div>
<div class='abs' style='left:{MIDI_LED[0] - 48}px;top:{MIDI_LED[1] - 8}px;font:600 13px Barlow;letter-spacing:2px;color:var(--dim)'>MIDI</div>
<div class='abs' style='left:{CPU[0] - 38}px;top:{MIDI_LED[1] - 8}px;font:600 13px Barlow;letter-spacing:2px;color:var(--dim)'>CPU</div>
<div class='abs' style='left:284px;top:58px;width:712px;height:10px;opacity:.55;background:url({M.svg_url(M.WAVE, t["accent2"])}) repeat-x;background-size:60px 10px'></div>""")
    # the screen: glass tinted by the panel colour, so it reads as a lit display, not a black box
    x, y, w, h = SCR
    flag = "".join(f"<div style='flex:1;background:{c}'></div>" for c in t.get("flag", []))
    out.append(f"""<div class='abs' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:20px;overflow:hidden;
  background:linear-gradient(180deg, color-mix(in srgb,var(--glass) 66%,var(--panel)), color-mix(in srgb,var(--glass) 78%,var(--panel)));box-shadow:inset 0 0 0 2px rgba(0,0,0,.6), inset 0 0 0 4px color-mix(in srgb,var(--ink) 10%,transparent),0 10px 24px rgba(0,0,0,.45)'>
<div class='abs' style='left:0;top:0;width:{w}px;height:{RULE_Y - y if view != 2 else 120}px;
  background:radial-gradient(600px 220px at 50% -20%, color-mix(in srgb,var(--accent) 22%,transparent), transparent 70%)'></div>
{"" if view == 2 else f"<div class='abs' style='left:0;top:{RULE_Y - y}px;width:{w}px;height:1px;background:color-mix(in srgb,var(--ink) 12%,transparent)'></div>"}
{f"<div class='abs' style='left:0;top:0;width:{w}px;height:5px;display:flex;opacity:.9'>{flag}</div>" if flag else ""}
</div>""")
    if view != 2:
        out.append(sbtn_html(PREV[0], PREV[1], "◀", "big"))
        out.append(sbtn_html(NEXT[0], NEXT[1], "▶", "big"))
    # the buttons along the foot, unlit (the lit ones are overlays)
    for key, lab, bx in FOOT:
        out.append(button_html(bx, FOOT_Y, lab))
    return "".join(out)


def browse_html(th):
    out = []
    for cx in (COL2, COL3):
        out.append(f"<div class='abs' style='left:{cx}px;top:{RULE_Y + 1}px;width:1px;height:{SCR[1] + SCR[3] - RULE_Y - 6}px;"
                   f"background:color-mix(in srgb,var(--ink) 10%,transparent)'></div>")
    for x, txt in ((COL1 + 18, "GENRE"), (COL2 + 18, "TYPE")):
        out.append(f"<div class='abs' style='left:{x}px;top:{HEAD_Y + 4}px;font:700 16px Barlow;letter-spacing:3px;color:var(--dim)'>{txt}</div>")
    for k in range(len(GENRES)):
        cy = LIST_Y + k * (ROW_TH + ROW_GAP) + ROW_TH // 2
        out.append(f"<div class='abs' style='left:{COL1 + 22}px;top:{cy - 6}px;width:12px;height:12px;border-radius:50%;"
                   f"background:{GENRE_DOTS[k]}'></div>")
    return "".join(out)


def sound_html(th):
    out = []
    for l in range(2):
        c = card(l)
        x, y, w, h = c["box"]
        out.append(f"<div class='abs' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:14px;"
                   f"background:color-mix(in srgb,var(--ink) 6%,transparent);box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--accent) 55%,transparent)'></div>")
        bx, by, bw, bh = c["badge"]
        out.append(f"<div class='abs' style='left:{bx}px;top:{by}px;width:{bw}px;height:{bh}px;border-radius:8px;background:var(--accent);"
                   f"color:#000;font:700 19px Barlow;display:grid;place-items:center'>{'AB'[l]}</div>")
        for (cx, cy, cw, ch), (_, _, lab) in zip(c["cells"], LAYER_CELLS):
            out.append(f"<div class='abs' style='left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px;border-radius:10px;"
                       f"background:color-mix(in srgb,var(--ink) 5%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 14%,transparent)'></div>")
            out.append(f"<div class='abs' style='left:{cx}px;top:{cy + 4}px;width:{cw}px;text-align:center;font:600 14px Barlow;"
                       f"letter-spacing:1.5px;color:var(--dim)'>{lab}</div>")
        for key in ("prev", "next"):
            out.append(sbtn_html(*c[key], "◀" if key == "prev" else "▶", "big"))
        out.append(sbtn_html(*c["on"], "ON"))
        out.append(sbtn_html(*c["solo"], "SOLO"))
    return "".join(out)


def settings_html(th):
    out = []
    for bx, by, title, rows in setting_rows():
        out.append(f"<div class='abs' style='left:{bx}px;top:{by}px;width:{BOX_W}px;height:{BOX_H}px;border-radius:14px;"
                   f"background:color-mix(in srgb,var(--ink) 6%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 12%,transparent)'></div>")
        out.append(f"<div class='abs' style='left:{bx + 16}px;top:{by + 10}px;font:700 16px Barlow;letter-spacing:3px;color:var(--accent)'>{title}</div>")
        for k, lab, (rx, ry, rw, rh) in rows:
            out.append(f"<div class='abs' style='left:{rx + 8}px;top:{ry + 6}px;height:{rh}px;line-height:{rh}px;font:600 20px Barlow;"
                       f"letter-spacing:1px;color:var(--ink)'>{lab}</div>")
            out.append(f"<div class='abs' style='left:{rx + rw - 22}px;top:{ry}px;height:{rh}px;line-height:{rh - 2}px;font:600 26px Outfit;"
                       f"color:var(--dim)'>›</div>")
    x, y, w, h = CW_BOX
    out.append(f"<div class='abs' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:14px;"
               f"background:color-mix(in srgb,var(--ink) 6%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 12%,transparent)'></div>")
    out.append(f"<div class='abs' style='left:{x + 16}px;top:{y + 10}px;font:700 16px Barlow;letter-spacing:3px;color:var(--accent)'>COLORWAY</div>")
    prev, name, nxt = cw_parts()
    out.append(sbtn_html(*prev, "◀", "big"))
    out.append(sbtn_html(*nxt, "▶", "big"))
    return "".join(out)


VIEW_HTML = [browse_html, sound_html, settings_html]


def background_html(th, view):
    return page(th, chassis_html(th, view) + VIEW_HTML[view](th))


# ---- overlays, each drawn alone on a transparent page of its own size
def knob_svg(frac, th):
    t = T[th]
    s = 2 * KNOB_R + 10
    c = s / 2
    a0, a1 = 135, 405
    ang = a0 + (a1 - a0) * frac
    r = KNOB_R - 1

    def pt(a, rr):
        return c + rr * math.cos(math.radians(a)), c + rr * math.sin(math.radians(a))
    x0, y0 = pt(a0, r)
    x1, y1 = pt(a1, r)
    xa, ya = pt(ang, r)
    large = 1 if (ang - a0) > 180 else 0
    arc = (f'<path d="M{x0:.2f} {y0:.2f} A{r} {r} 0 {large} 1 {xa:.2f} {ya:.2f}" fill="none" stroke="{t["accent"]}" '
           f'stroke-width="4.5" stroke-linecap="round" filter="url(#gl)"/>' if frac > 0.004 else "")
    cr = KNOB_R - 8
    px, py = pt(ang, cr - 6)
    qx, qy = pt(ang, cr - 19)
    return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}" xmlns="http://www.w3.org/2000/svg"><defs>'
            f'<radialGradient id="cg" cx="40%" cy="30%" r="80%"><stop offset="0" stop-color="color-mix(in srgb, {t["cap"]} 60%, #fff 40%)"/>'
            f'<stop offset=".55" stop-color="{t["cap"]}"/><stop offset="1" stop-color="#05040a"/></radialGradient>'
            f'<radialGradient id="fg" cx="45%" cy="35%" r="75%"><stop offset="0" stop-color="rgba(255,255,255,.10)"/><stop offset="1" stop-color="rgba(0,0,0,.25)"/></radialGradient>'
            f'<filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            f'<filter id="sh" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="3" stdDeviation="2.5" flood-color="#000" flood-opacity=".55"/></filter></defs>'
            f'<path d="M{x0:.2f} {y0:.2f} A{r} {r} 0 1 1 {x1:.2f} {y1:.2f}" fill="none" stroke="color-mix(in srgb, {t["ink"]} 13%, transparent)" stroke-width="4.5" stroke-linecap="round"/>'
            f'{arc}<circle cx="{c}" cy="{c}" r="{cr}" fill="url(#cg)" stroke="rgba(0,0,0,.55)" stroke-width="1.5" filter="url(#sh)"/>'
            f'<circle cx="{c}" cy="{c}" r="{cr - 4}" fill="url(#fg)"/>'
            f'<line x1="{qx:.2f}" y1="{qy:.2f}" x2="{px:.2f}" y2="{py:.2f}" stroke="{t["knobmark"]}" stroke-width="4" stroke-linecap="round"/></svg>')


class Renderer:
    def __init__(self, p):
        self.b = p.chromium.launch()
        self.pg = self.b.new_page(viewport=dict(width=W, height=H), device_scale_factor=1)

    def shot(self, html, w=W, h=H, transparent=False):
        self.pg.set_viewport_size(dict(width=w, height=h))
        self.pg.set_content(html)
        self.pg.evaluate("document.fonts.ready")
        self.pg.wait_for_timeout(60)
        png = self.pg.screenshot(clip=dict(x=0, y=0, width=w, height=h), omit_background=transparent)
        return Image.open(io.BytesIO(png)).convert("RGBA")

    def overlay(self, th, body, w, h):
        return self.shot(page(th, body, w, h), w, h, transparent=True)

    def close(self):
        self.b.close()


def on_bg(bg, box, ov):
    x, y, w, h = box
    g = bg.crop((x, y, x + w, y + h))
    g.alpha_composite(ov.resize((w, h)) if ov.size != (w, h) else ov)
    return g


def strip(frames):
    w, h = frames[0].size
    out = Image.new("RGBA", (w, h * len(frames)))
    for i, f in enumerate(frames):
        out.paste(f, (0, i * h))
    return out


def save(img, *path):
    p = os.path.join(ART, *path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.convert("RGB").save(p, optimize=True) if img.mode == "RGBA" and img.getextrema()[3][0] == 255 else img.save(p, optimize=True)


def wave_frame(th, w, h, level, phase):
    """the LAYERS view's waveform: idle (level -1) or one of 4 levels x 4 phases"""
    t = T[th]
    if level < 0:
        pts = " ".join(f"{i},{h / 2:.1f}" for i in range(0, w + 1, 8))
        op = ".35"
    else:
        amp = (0.18, 0.38, 0.62, 0.9)[level] * h / 2
        pts = []
        for i in range(0, w + 1, 4):
            u = i / w
            env = math.exp(-((u - 0.5) / 0.42) ** 2)
            y = h / 2 + amp * env * (0.75 * math.sin(2 * math.pi * (u * 3.0 + phase / 4)) + 0.25 * math.sin(2 * math.pi * (u * 11 - phase / 4)))
            pts.append(f"{i},{y:.1f}")
        pts = " ".join(pts)
        op = "1"
    return (f"<svg width='{w}' height='{h}' style='position:absolute;left:0;top:0;opacity:{op}'>"
            f"<polyline points='{pts}' fill='none' stroke='{t['accent2']}' stroke-width='12' opacity='.15' stroke-linejoin='round'/>"
            f"<polyline points='{pts}' fill='none' stroke='{t['accent2']}' stroke-width='3' stroke-linejoin='round'/></svg>")


def export_art():
    global FONTS_CSS
    FONTS_CSS = font_faces()
    for th in THEMES:
        shutil.rmtree(os.path.join(ART, th), ignore_errors=True)
    os.makedirs(ART, exist_ok=True)
    with sync_playwright() as p:
        R = Renderer(p)
        for th in THEMES:
            t = T[th]
            bgs = []
            for v in range(3):
                bg = R.shot(background_html(th, v))
                save(bg, th, "bg_%s.png" % VIEWS[v].lower())
                bgs.append(bg)
            b0, b1, b2 = bgs
            # knob filmstrip (transparent)
            s = 2 * KNOB_R + 10
            col = "".join("<div style='position:absolute;left:0;top:%dpx'>%s</div>" % (f * s, knob_svg(f / 127, th)) for f in range(128))
            save(R.overlay(th, col, s, 128 * s), th, "knob.png")
            # foot buttons: view buttons 3 frames (lit when its view is shown), FAV / LIST / RESET 2 frames
            bh = FOOT_STRIP_H
            for v, (key, lab, bx) in enumerate(FOOT):
                box = (bx, FOOT_Y, BTN_W, bh)
                lit = R.overlay(th, button_html(0, 0, lab, "on"), BTN_W, bh)
                unlit = b0.crop((bx, FOOT_Y, bx + BTN_W, FOOT_Y + bh))
                if key in ("go_browse", "go_layers", "go_settings"):
                    me = ("go_browse", "go_layers", "go_settings").index(key)
                    fr = [on_bg(bgs[i], box, lit) if i == me else bgs[i].crop((bx, FOOT_Y, bx + BTN_W, FOOT_Y + bh)) for i in range(3)]
                else:
                    cls = "edit" if key == "reset_tap" else "on"
                    fr = [unlit, on_bg(b0, box, R.overlay(th, button_html(0, 0, lab, cls), BTN_W, bh))]
                save(strip(fr), th, "foot_%s.png" % key)
            # header chips
            for nm, box, labels, c2, align in (("chip_g", CHIP_G, GENRES, "", "right"), ("chip_t", CHIP_T, TYPES, "c2", "left")):
                fr = []
                for i, lab in enumerate(labels):
                    body = "" if (nm == "chip_g" and i == 0) else f"<div class='chip {c2}' style='{align}:0'>{lab}</div>"
                    fr.append(on_bg(b0, box, R.overlay(th, body, box[2], box[3])))
                save(strip(fr), th, nm + ".png")
            # MIDI LED, CPU bar
            cx, cy, sz = MIDI_LED
            box = (cx - sz // 2, cy - sz // 2, sz, sz)
            fr = [on_bg(b0, box, R.overlay(th, f"<div class='abs' style='left:2px;top:2px;width:12px;height:12px;border-radius:50%;"
                                                f"background:{'var(--accent2)' if on else 'color-mix(in srgb,var(--ink) 18%,transparent)'};"
                                                f"{'box-shadow:0 0 6px var(--accent2)' if on else ''}'></div>", sz, sz)) for on in (0, 1)]
            save(strip(fr), th, "led.png")
            x, y, w, h = CPU
            fr = [on_bg(b0, (x, y, w, h), R.overlay(th, f"<div class='abs' style='inset:0;border-radius:4px;background:color-mix(in srgb,var(--ink) 15%,transparent);overflow:hidden'>"
                                                       f"<div style='height:100%;width:{max(2, c * 10)}%;background:var(--accent2)'></div></div>", w, h)) for c in range(11)]
            save(strip(fr), th, "cpu.png")
            # the lists' highlights: one filmstrip per list, frame 0 none, frame r + 1 row r lit (cut from the screen)
            for key, sel, x, w, tx, rows, size in LISTS:
                box = (x, LIST_Y, w, rows * (ROW_TH + ROW_GAP))
                fr = [b0.crop((x, LIST_Y, x + w, LIST_Y + box[3]))]
                for r in range(rows):
                    top = r * (ROW_TH + ROW_GAP) + HL_INSET
                    fr.append(on_bg(b0, box, R.overlay(th, f"<div class='row sel' style='left:0;top:{top}px;width:{w}px;"
                                                           f"height:{ROW_TH + ROW_GAP - 2 * HL_INSET}px'></div>", w, box[3])))
                save(strip(fr), th, "hl_%s.png" % key)
            # LAYERS view: the waveform (17 frames, two halves), layer ON / SOLO, instrument arrows
            x, y, w, h = WAVE
            fr = [R.overlay(th, wave_frame(th, w, h, -1, 0), w, h)]
            for lvl in range(4):
                for ph in range(4):
                    fr.append(R.overlay(th, wave_frame(th, w, h, lvl, ph), w, h))
            assert len(fr) == WAVE_FRAMES
            full = [on_bg(b1, WAVE, f) for f in fr]
            save(strip([f.crop((0, 0, w // 2, h)) for f in full]), th, "wave_l.png")
            save(strip([f.crop((w // 2, 0, w, h)) for f in full]), th, "wave_r.png")
            c = card(0)
            for nm, txt, lit_cls in (("on", "ON", "lit"), ("solo", "SOLO", "lit2")):
                box = (*c[nm], BTN_W, BTN_H)
                save(on_bg(b1, box, R.overlay(th, sbtn_html(0, 0, txt), BTN_W, BTN_H)), th, "%s_off.png" % nm)
                save(on_bg(b1, box, R.overlay(th, sbtn_html(0, 0, txt, lit_cls), BTN_W, BTN_H)), th, "%s_on.png" % nm)
            for nm, txt in (("prev", "◀"), ("next", "▶")):
                box = (*c[nm], BTN_W, BTN_H)
                save(on_bg(b1, box, R.overlay(th, sbtn_html(0, 0, txt, "big"), BTN_W, BTN_H)), th, "arrow_%s_off.png" % nm)
                save(on_bg(b1, box, R.overlay(th, sbtn_html(0, 0, txt, "big lit"), BTN_W, BTN_H)), th, "arrow_%s_on.png" % nm)
            # SETTINGS: the colorway arrows
            prev, name, nxt = cw_parts()
            for nm, pos, txt in (("cwprev", prev, "◀"), ("cwnext", nxt, "▶")):
                box = (*pos, BTN_W, BTN_H)
                save(on_bg(b2, box, R.overlay(th, sbtn_html(0, 0, txt, "big"), BTN_W, BTN_H)), th, "%s_off.png" % nm)
                save(on_bg(b2, box, R.overlay(th, sbtn_html(0, 0, txt, "big lit"), BTN_W, BTN_H)), th, "%s_on.png" % nm)
        # transparent tap plates, one per size
        R.close()
    sizes = set()
    for _, box in pads():
        sizes.add(box[2:])
    for w, h in sizes:
        Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(os.path.join(ART, "pad_%dx%d.png" % (w, h)))
    Image.new("RGBA", (20, 20 * 128), (0, 0, 0, 0)).save(os.path.join(ART, "clear_knob.png"))


def pads():
    """every transparent tap plate: (key, box), with the view it belongs to in the key's entry of PAD_VIEW"""
    out = [("prev", (*PREV, BTN_W, BTN_H)), ("next", (*NEXT, BTN_W, BTN_H))]
    out += [(k, (bx, FOOT_Y, BTN_W, BTN_H + 4)) for k, _, bx in FOOT]
    for (key, sel, x, w, tx, rows, size), pad in zip(LISTS, ("gpick", "tpick", "pick")):
        for i in range(rows):
            out.append(("%s_%d" % (pad, i + 1), (x, LIST_Y + i * (ROW_TH + ROW_GAP), w, ROW_TH)))
    for l in range(2):
        c = card(l)
        x, y, w, h = c["name"]
        out.append(("tname_" + "ab"[l], (x, y, w, h)))
        for (cx, cy, cw, ch), (code, _, _) in zip(c["cells"], LAYER_CELLS):
            out.append(("t%s_%s" % (code, "ab"[l]), (cx, cy, cw, ch)))
    for bx, by, title, rows in setting_rows():
        for k, lab, box in rows:
            out.append(("set_" + k, box))
    return out


def pad_view(key):
    if key in ("prev", "next"):
        return (0, 1)
    if key.startswith(("gpick", "tpick", "pick")):
        return 0
    if key.startswith(("tname", "tlv", "tpn", "toc", "tfn")):
        return 1
    if key.startswith("set_"):
        return 2
    return None


# ---------------------------------------------------------------- layout.conf
def write_layout():
    Y = Y_OFF
    L = ["# Tropix faceplate. Generated by tools/make_skin.py (edit that, not this file).",
         "theme_bg=1d1430", "theme_ink=ffe9d2", "theme_ink_dim=b79bb0", "theme_accent=ff8a3d", "theme_accent_hi=ff8a3d",
         "theme_lcd=140d22", "theme_line=3a2a52", "theme_box=140d22",
         "qlinks_track = " + ",".join(QLINKS),
         "[tab MAIN]"]
    NV = len(VIEWS)
    for n, th in enumerate(THEMES):
        for v in range(NV):
            L.append("art file=art/%s/bg_%s.png x=0 y=%d w=1280 h=628 fit=stretch when=look:%d" % (th, VIEWS[v].lower(), Y, n * NV + v))

    def readout(key, box, size, color, weight="semibold", align="left", when="", pad=None):
        x, y, w, h = box
        L.append('readout cx=%d cy=%d w=%d h=%d label="" key=%s box=0 tsize=%d tcolor=%s tweight=%s talign=%s%s %s' % (
            x + w // 2, y + h // 2 + Y, w, h, key, jh(size), color, weight, align, " tpad=%d" % pad if pad is not None else "", when))

    def meter(key, box, img, frames, when):
        x, y, w, h = box
        L.append("meter cx=%d cy=%d w=%d h=%d key=%s strip=%s frames=%d %s" % (x + w // 2, y + h // 2 + Y, w, h, key, img, frames, when))

    for n, th in enumerate(THEMES):
        t = T[th]
        ink, dim, a2 = hx(t["ink"]), hx(t["dim"]), hx(t["accent2"])
        w = "when=theme:%d" % n
        meter("midi_led", (MIDI_LED[0] - MIDI_LED[2] // 2, MIDI_LED[1] - MIDI_LED[2] // 2, MIDI_LED[2], MIDI_LED[2]),
              "art/%s/led.png" % th, 2, w)
        meter("cpu", CPU, "art/%s/cpu.png" % th, 11, w)
        for key, lab, cx, cy in knob_centres():
            L.append('knob cx=%d cy=%d r=%d label="%s" key=%s ns=0 vs=%d bw=124 ink=%s ink_dim=%s strip=art/%s/knob.png frames=128 %s' % (
                cx, cy + Y, KNOB_R, lab, key, jh(VALUE_PX), a2, a2, th, w))
        for key, lab, bx in FOOT:
            frames = 3 if key.startswith("go_") else 2
            mkey = {"go_browse": "view", "go_layers": "view", "go_settings": "view", "fav_tap": "fav", "favs_tap": "favs",
                    "reset_tap": "edited"}[key]
            meter(mkey, (bx, FOOT_Y, BTN_W, FOOT_STRIP_H), "art/%s/foot_%s.png" % (th, key), frames, w)
    for n, th in enumerate(THEMES):
        t = T[th]
        ink, dim, a2 = hx(t["ink"]), hx(t["dim"]), hx(t["accent2"])
        for v in (0, 1):                             # the screen's header (BROWSE and SOUND)
            w = "when=look:%d" % (n * NV + v)
            meter("pgenre", CHIP_G, "art/%s/chip_g.png" % th, len(GENRES), w)
            meter("ptype", CHIP_T, "art/%s/chip_t.png" % th, len(TYPES), w)
            readout("hdr_info", HDR_INFO, 18, dim, align="left", when=w, pad=0)
            # the preset's name is a knob that browses: touch it, then the data wheel (or a drag) steps presets
            x, y, bw, bh = NAME
            L.append('knob cx=%d cy=%d r=5 lay=side bw=%d bh=%d vs=%d label="" key=browse ink=%s strip=art/clear_knob.png frames=128 %s' % (
                x + bw // 2 - 12, y + bh // 2 + Y, bw, bh, jh(34), ink, w))
        # BROWSE
        w = "when=look:%d" % (n * NV + 0)
        for key, sel, x, wd, tx, rows, size in LISTS:
            meter(sel, (x, LIST_Y, wd, rows * (ROW_TH + ROW_GAP)), "art/%s/hl_%s.png" % (th, key), rows + 1, w)
            for r in range(rows):
                readout("%s_%d" % (key, r + 1), (tx, LIST_Y + r * (ROW_TH + ROW_GAP), x + wd - 8 - tx, ROW_TH + ROW_GAP), size, ink,
                        align="left", when=w, pad=0)
        readout("list_head", LIST_HEAD, 18, dim, align="left", when=w, pad=0)
        # SOUND
        w = "when=look:%d" % (n * NV + 1)
        x, y, wd, h = WAVE
        for half, nm in ((0, "wave_l"), (1, "wave_r")):
            meter("wave", (x + half * wd // 2, y, wd // 2, h), "art/%s/%s.png" % (th, nm), WAVE_FRAMES, w)
        for l in range(2):
            c = card(l)
            ab = "ab"[l]
            readout("lname_" + ab, c["name"], 25, ink, align="left", when=w, pad=0)
            for (cx, cy, cw, ch), (code, _, _) in zip(c["cells"], LAYER_CELLS):
                readout("%s_%s" % (code, ab), (cx, cy + 16, cw, ch - 18), 22, a2, align="center", when=w, pad=0)
            for nm, key, img in (("on", "layer_" + ab, "on"), ("solo", "solo_" + ab, "solo")):
                bx, by = c[nm]
                L.append('toggle cx=%d cy=%d w=%d h=%d label="" key=%s ns=0 bw=%d img=art/%s/%s_off.png img_on=art/%s/%s_on.png %s' % (
                    bx + BTN_W // 2, by + BTN_H // 2 + Y, BTN_W, BTN_H, key, BTN_W, th, img, th, img, w))
            for nm in ("prev", "next"):
                bx, by = c[nm]
                L.append('button cx=%d cy=%d w=%d h=%d label="" key=inst_%s_%s img=art/%s/arrow_%s_off.png img_on=art/%s/arrow_%s_on.png %s' % (
                    bx + BTN_W // 2, by + BTN_H // 2 + Y, BTN_W, BTN_H, ab, nm, th, nm, th, nm, w))
        for i, y in enumerate(DESC_Y):
            readout("desc_%d" % (i + 1), (CARD_X + 4, y, CARD_W - 8, 28), 21, ink, weight="regular", align="left", when=w, pad=0)
        # SETTINGS
        w = "when=look:%d" % (n * NV + 2)
        for bx, by, title, rows in setting_rows():
            for k, lab, (rx, ry, rw, rh) in rows:
                readout("sv_" + k, (rx + rw - 174, ry, 144, rh), 23, a2, align="right", when=w, pad=0)
        prev, name, nxt = cw_parts()
        readout("cw_name", name, 28, ink, align="center", when=w, pad=0)
        for pos, key, img in ((prev, "theme_prev", "cwprev"), (nxt, "theme_next", "cwnext")):
            L.append('button cx=%d cy=%d w=%d h=%d label="" key=%s img=art/%s/%s_off.png img_on=art/%s/%s_on.png %s' % (
                pos[0] + BTN_W // 2, pos[1] + BTN_H // 2 + Y, BTN_W, BTN_H, key, th, img, th, img, w))
    for key, (x, y, bw, bh) in pads():               # the tap plates, on top (transparent, one set for every colorway)
        v = pad_view(key)
        for vv in (v if isinstance(v, tuple) else (v,)):
            L.append('button cx=%d cy=%d w=%d h=%d label="" key=%s img=art/pad_%dx%d.png img_on=art/pad_%dx%d.png%s' % (
                x + bw // 2, y + bh // 2 + Y, bw, bh, key, bw, bh, bw, bh, " when=view:%d" % vv if vv is not None else ""))
    L.append('qlinks "MAIN" = ' + ",".join(QLINKS))
    with open(os.path.join(VST, "layout.conf"), "w") as f:
        f.write("\n".join(L) + "\n")


# ---------------------------------------------------------------- mockups with live text, for review
def mockups(outdir):
    """Each view in each colorway as MPC should show it: the background, then the live text and widgets drawn on
    top in Titillium (sample values), so the whole design can be checked before a device test."""
    global FONTS_CSS
    FONTS_CSS = font_faces()
    os.makedirs(outdir, exist_ok=True)
    import presets as PR
    pr = PR.PRESETS[39]
    with sync_playwright() as p:
        R = Renderer(p)
        for th in THEMES:
            t = T[th]
            for v in range(3):
                bg = Image.open(os.path.join(ART, th, "bg_%s.png" % VIEWS[v].lower())).convert("RGBA")
                im = bg.copy()

                def paste(path, box, frame=0, frames=1):
                    s_ = Image.open(os.path.join(ART, path)).convert("RGBA")
                    fh = s_.height // frames
                    fr = s_.crop((0, frame * fh, s_.width, (frame + 1) * fh))
                    im.alpha_composite(fr, (box[0], box[1]))

                # knobs at sample positions
                s = 2 * KNOB_R + 10
                for i, (key, lab, cx, cy) in enumerate(knob_centres()):
                    paste("%s/knob.png" % th, (cx - s // 2, cy - s // 2), [100, 15, 70, 0, 6, 60, 100, 40, 0, 40, 64, 0, 25, 20, 36, 100][i], 128)
                for key, lab, bx in FOOT:
                    paste("%s/foot_%s.png" % (th, key), (bx, FOOT_Y), (v if key.startswith("go_") else (1 if key == "fav_tap" else 0)),
                          3 if key.startswith("go_") else 2)
                if v != 2:
                    paste("%s/chip_g.png" % th, CHIP_G, 3, len(GENRES))
                    paste("%s/chip_t.png" % th, CHIP_T, 2, len(TYPES))
                paste("%s/led.png" % th, (MIDI_LED[0] - 8, MIDI_LED[1] - 8), 1, 2)
                paste("%s/cpu.png" % th, CPU, 2, 11)
                txt = []

                def text(box, s_, size, color, weight=600, align="left"):
                    x, y, w, h = box
                    txt.append(f"<div class='abs' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px;display:flex;align-items:center;"
                               f"justify-content:{ {'left': 'flex-start', 'center': 'center', 'right': 'flex-end'}[align] };"
                               f"font:{weight} {size}px Titillium;color:{color};white-space:nowrap'>{s_}</div>")
                # live values under the knobs
                vals = ["8.2k", "12%", "+3 dB", "0%", "4 ms", "1.20 s", "80%", "240 ms", "60 ms", "18 CT", "5.00 Hz", "0%",
                        "20%", "15%", "28%", "-3.0 dB"]
                for (key, lab, cx, cy), val in zip(knob_centres(), vals):
                    text((cx - 62, cy + KNOB_R + 2, 124, 44), val, VALUE_PX, t["accent2"], align="center")
                if v != 2:
                    text(HDR_INFO, "PRESET 040 / 128", 18, t["dim"])
                    text(NAME, pr["name"], 34, t["ink"], align="center")
                if v == 0:
                    names = [q["name"] for q in PR.PRESETS if q["type"] == "HORNS" and "KOMPA" in q["genres"]]
                    items = [GENRES, TYPES, ["%02d   %s%s" % (i + 1, nm, "  ★" if i == 3 else "") for i, nm in enumerate(names[:LIST_ROWS])]]
                    for (key, sel, x, wd, tx, rows, size), labels, lit in zip(LISTS, items, (4, 3, 1)):
                        paste("%s/hl_%s.png" % (th, key), (x, LIST_Y), lit, rows + 1)
                        for i, g in enumerate(labels):
                            text((tx, LIST_Y + i * (ROW_TH + ROW_GAP), x + wd - 8 - tx, ROW_TH + ROW_GAP), g, size, t["ink"])
                    text(LIST_HEAD, "PRESETS  ·  %d" % len(names), 18, t["dim"])
                elif v == 1:
                    paste("%s/wave_l.png" % th, WAVE[:2], 10, WAVE_FRAMES)
                    paste("%s/wave_r.png" % th, (WAVE[0] + WAVE[2] // 2, WAVE[1]), 10, WAVE_FRAMES)
                    for l, (nm, cells) in enumerate((("ALTO SAX VIBRATO", ["0 dB", "C", "0", "0 CT"]),
                                                     ("BRIGHT TRUMPET", ["-5 dB", "R12", "+1", "+4 CT"]))):
                        c = card(l)
                        paste("%s/on_on.png" % th, c["on"])
                        paste("%s/solo_off.png" % th, c["solo"])
                        text(c["name"], nm, 25, t["ink"])
                        for (cx, cy, cw, ch), val in zip(c["cells"], cells):
                            text((cx, cy + 16, cw, ch - 18), val, 22, t["accent2"], align="center")
                    d1, d2 = PR.desc_lines(pr["desc"])
                    for y, s_ in zip(DESC_Y, (d1, d2)):
                        text((CARD_X + 4, y, CARD_W - 8, 28), s_, 21, t["ink"], weight=400)
                else:
                    sample = dict(voice_mode="LEGATO", lfo_target="TREMOLO", scoop="LIGHT", a4_ref="440 Hz", transpose="0 st",
                                  bend_range="2 st", polyphony="24", vel_curve="NORMAL", vel_sens="80%", mod_wheel="VIBRATO",
                                  spread="30%", anim="SMOOTH")
                    for bx, by, title, rows in setting_rows():
                        for k, lab, (rx, ry, rw, rh) in rows:
                            text((rx + rw - 174, ry, 144, rh), sample[k], 23, t["accent2"], align="right")
                    prev, name, nxt = cw_parts()
                    text(name, THEME_LABELS[THEMES.index(th)].upper(), 28, t["ink"], align="center")
                live = R.overlay(th, "".join(txt), W, H)
                im.alpha_composite(live)
                im.convert("RGB").save(os.path.join(outdir, "%s_%s.png" % (VIEWS[v].lower(), th)))
        R.close()


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--mockup":
        mockups(sys.argv[2])
        return
    export_art()
    write_layout()


if __name__ == "__main__":
    main()
