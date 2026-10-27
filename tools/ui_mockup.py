#!/usr/bin/env python3
"""Tropix UI mockups: the plugin area (1280 x 628, MPC's own header sits above it) drawn as HTML and rendered by
headless Chromium, in every colorway.

    python3 tools/ui_mockup.py [outdir] [page ...]      pages: browse, sound, settings

Layout rules carried over from the other MPC plugins: every knob one size, every button one size, 16 knobs as four
Q-Link columns of four (two columns per side panel), large legible text, no hidden sub-pages.
"""
import base64
import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "vst", "fonts")
W, H = 1280, 628

THEMES = {
    # name: bg (chassis), bg2 (glow), panel, accent, accent2, glass (screen), ink (screen text), dim, sym (motif)
    "sunset": dict(label="SUNSET", bg="#1d1430", bg2="#5a2340", panel="#2a1c3f", accent="#ff8a3d", accent2="#2fd3c6",
                   glass="#140d22", ink="#ffe9d2", dim="#b79bb0", sym="#ff8a3d", cap="#3a2a52", knobmark="#ffe9d2"),
    "lagos": dict(label="LAGOS", bg="#0f2419", bg2="#2d4a1f", panel="#173323", accent="#f2b632", accent2="#d9573b",
                  glass="#0a1912", ink="#fbf1d6", dim="#a7b896", sym="#f2b632", cap="#21422f", knobmark="#fbf1d6"),
    "aloha": dict(label="ALOHA", bg="#0b2a3a", bg2="#11586b", panel="#123a4d", accent="#ff5d8f", accent2="#f6d7a7",
                  glass="#08202d", ink="#eefaff", dim="#93b8c6", sym="#7fe3e0", cap="#1a4a60", knobmark="#eefaff"),
    "jamaica": dict(label="JAMAICA", bg="#08130c", bg2="#0f4422", panel="#10241a", accent="#fed100", accent2="#2dbd5a",
                    glass="#07120b", ink="#fbf6dc", dim="#a3b8a3", sym="#fed100", cap="#1d3626", knobmark="#fbf6dc",
                    flag=["#1f9e47", "#fed100", "#111111", "#fed100", "#1f9e47"]),
    "rasta": dict(label="RASTA", bg="#0e0d0a", bg2="#2a2410", panel="#1a1813", accent="#f5c518", accent2="#3fb950",
                  glass="#0c0b08", ink="#f7f1df", dim="#aca68f", sym="#e0392b", cap="#2c2a22", knobmark="#f7f1df",
                  flag=["#d7261e", "#f5c518", "#1e9e3e"]),
    "haiti": dict(label="HAITI", bg="#0b1660", bg2="#2a0f4a", panel="rgba(10,14,48,.74)", accent="#ffffff", accent2="#f5c84c",
                  glass="#0a0f33", ink="#ffffff", dim="#c3cae8", sym="#3fae49", cap="#1c2c86", knobmark="#ffffff",
                  flag=["#00209f", "#d21034"], split=["#0a2a9e", "#a30d2b"], palm_op=".2"),
    "africa": dict(label="AFRICA", bg="#100c0b", bg2="#3d1210", panel="#1c1514", accent="#e5372e", accent2="#33b864",
                   glass="#0e0a09", ink="#f6eee8", dim="#b4a29c", sym="#33b864", cap="#2d2321", knobmark="#f6eee8",
                   flag=["#e5372e", "#141414", "#1f9e47"]),
    "kanaval": dict(label="KANAVAL", bg="#0d1a4a", bg2="#3b1660", panel="#16245c", accent="#ff3b4f", accent2="#ffd23f",
                    glass="#09113a", ink="#f3f5ff", dim="#9aa6d6", sym="#ffd23f", cap="#23326e", knobmark="#f3f5ff"),
    "jozi": dict(label="JOZI NIGHT", bg="#120f1c", bg2="#3a1d5c", panel="#1d1830", accent="#b06cff", accent2="#3de0b0",
                 glass="#0b0914", ink="#f1ebff", dim="#a197bd", sym="#3de0b0", cap="#2a2342", knobmark="#f1ebff"),
}

GENRES = ["ALL", "AFROBEAT", "AMAPIANO", "KOMPA", "SOCA", "REGGAE", "HAWAIIAN"]
TYPES = ["KEYS", "GUITARS", "HORNS", "STEEL PAN", "MALLETS", "BASS", "PERCUSSION", "SYNTHS & FX"]
PRESETS = ["Alto Lead Kompa", "Sax & Trumpet Section", "Kompa Brass Hits", "Twoubadou Sax", "Harmon Night",
           "Bright Trumpet Line", "Soft Alto Pad", "Gala Horns"]
KNOBS = {  # section: [(label, value text, 0..1)]
    "TONE": [("CUTOFF", "8.2k", 0.78), ("RESO", "12%", 0.12), ("BRIGHT", "+3", 0.62), ("DRIVE", "0%", 0.0)],
    "ENVELOPE": [("ATTACK", "4 ms", 0.06), ("DECAY", "1.2 s", 0.45), ("SUSTAIN", "80%", 0.8), ("RELEASE", "240 ms", 0.3)],
    "MOTION": [("GLIDE", "OFF", 0.0), ("VIBRATO", "18%", 0.18), ("LFO RATE", "5.2 Hz", 0.52), ("LFO DEPTH", "0%", 0.0)],
    "SPACE": [("CHORUS", "20%", 0.2), ("DELAY", "15%", 0.15), ("REVERB", "28%", 0.28), ("VOLUME", "-3 dB", 0.82)],
}


def font_url(name):
    with open(os.path.join(FONTS, name), "rb") as f:
        return "data:font/ttf;base64," + base64.b64encode(f.read()).decode()


# Island motifs as inline SVG (drawn here, original): a palm frond, a wave line, a hibiscus, the sun
PALM = ('<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><g fill="currentColor">'
        '<path d="M100 200 C 98 150, 92 120, 96 86 L 102 86 C 100 120, 106 150, 108 200 Z"/>'
        + "".join(f'<path transform="rotate({a} 99 84)" d="M99 84 C 120 70, 150 66, 182 74 C 156 76, 128 82, 99 90 Z"/>'
                  for a in (-160, -125, -95, -60, -25, 5, 35))
        + '</g></svg>')
WAVE = ('<svg viewBox="0 0 120 20" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M0 12 C 15 2, 30 2, 45 12 S 75 22, 90 12 S 120 2, 120 12" fill="none" stroke="currentColor" '
        'stroke-width="2.2" stroke-linecap="round"/></svg>')
HIBISCUS = ('<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><g fill="currentColor">'
            + "".join(f'<ellipse cx="50" cy="28" rx="17" ry="24" transform="rotate({a} 50 50)"/>' for a in (0, 72, 144, 216, 288))
            + '</g><circle cx="50" cy="50" r="8" fill="rgba(0,0,0,.35)"/></svg>')
SUN = ('<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="22" fill="currentColor"/>'
       + "".join(f'<rect x="48" y="4" width="4" height="14" rx="2" fill="currentColor" transform="rotate({a} 50 50)"/>'
                 for a in range(0, 360, 30)) + '</svg>')


def svg_url(svg, color):
    s = svg.replace("currentColor", color)
    return "data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode()


KNOB_R = 36
BTN_W, BTN_H = 108, 47


def knob(cx, cy, label, val, frac, t):
    """A lit knob: dark cap, a value arc that glows in the accent colour, a pointer, label above and value below."""
    a0, a1 = 135, 405
    ang = a0 + (a1 - a0) * frac
    import math
    r = KNOB_R + 7

    def pt(a, rr):
        return cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))
    x0, y0 = pt(a0, r)
    x1, y1 = pt(a1, r)
    xa, ya = pt(ang, r)
    large = 1 if (ang - a0) > 180 else 0
    track = f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 1 1 {x1:.1f} {y1:.1f}" class="track"/>'
    arc = (f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 {large} 1 {xa:.1f} {ya:.1f}" class="arc"/>' if frac > 0.004 else "")
    px, py = pt(ang, KNOB_R - 9)
    qx, qy = pt(ang, KNOB_R - 24)
    return (f'<g>{track}{arc}'
            f'<circle cx="{cx}" cy="{cy}" r="{KNOB_R}" class="cap"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{KNOB_R - 5}" class="capface"/>'
            f'<line x1="{qx:.1f}" y1="{qy:.1f}" x2="{px:.1f}" y2="{py:.1f}" class="pointer"/>'
            f'<text x="{cx}" y="{cy - KNOB_R - 14}" class="klabel">{label}</text>'
            f'<text x="{cx}" y="{cy + KNOB_R + 27}" class="kvalue">{val}</text></g>')


ICONS = {}


def side_panel(x, sections, t, qcols):
    """A side panel: two sections stacked, each a 2 x 2 knob grid. qcols: the Q-Link column numbers (left, right)."""
    out = []
    for i, name in enumerate(sections):
        y = 8 + i * 309
        out.append(f'<rect x="{x}" y="{y}" width="268" height="303" rx="18" class="panel"/>')
        out.append(f'<image href="{ICONS[name]}" x="{x + 134 - 62 - len(name) * 6}" y="{y + 10}" width="22" height="22"/>')
        out.append(f'<text x="{x + 134 + 12}" y="{y + 28}" class="stitle">{name}</text>')
        out.append(f'<line x1="{x + 24}" y1="{y + 40}" x2="{x + 244}" y2="{y + 40}" class="rule"/>')
        for k, (lab, val, frac) in enumerate(KNOBS[name]):
            col, row = k % 2, k // 2
            cx = x + (70 if col == 0 else 198)
            cy = y + 108 + row * 130
            out.append(knob(cx, cy, lab, val, frac, t))
    return "".join(out)


def button(x, y, text, on=False, icon=None):
    cls = "btn on" if on else "btn"
    return (f'<div class="{cls}" style="left:{x}px;top:{y}px;width:{BTN_W}px;height:{BTN_H}px">'
            f'{icon or ""}<span>{text}</span></div>')


def screen_browse(t):
    rows_g = "".join(f'<div class="row{" sel" if g == "KOMPA" else ""}"><i class="dot d{k}"></i>{g}</div>'
                     for k, g in enumerate(GENRES))
    rows_t = "".join(f'<div class="row{" sel" if ty == "HORNS" else ""}">{ty}</div>' for ty in TYPES)
    rows_p = "".join(f'<div class="row prow{" sel" if k == 0 else ""}"><b>{k + 1:02d}</b>{p}'
                     f'{"<em>★</em>" if k in (0, 4) else ""}</div>' for k, p in enumerate(PRESETS))
    return f"""
<div class="cols">
  <div class="col c1"><div class="chead">GENRE</div>{rows_g}</div>
  <div class="col c2"><div class="chead">TYPE</div>{rows_t}</div>
  <div class="col c3"><div class="chead">PRESETS <span>8 of 14</span></div>{rows_p}<div class="scroll"><i></i></div></div>
</div>"""


def screen_sound(t):
    import math
    pts = []
    for i in range(0, 641, 4):
        y = 40 + 24 * math.sin(i / 640 * 2 * math.pi * 3.0) * math.exp(-((i - 320) / 260) ** 2) \
            + 7 * math.sin(i / 640 * 2 * math.pi * 11)
        pts.append(f"{i},{y:.1f}")
    wave = (f'<svg class="wave" viewBox="0 0 640 80"><polyline points="{" ".join(pts)}" class="wl2"/>'
            f'<polyline points="{" ".join(pts)}" class="wl"/></svg>')

    def card(letter, name, meta, on=True, solo=False):
        return (f'<div class="layer{" on" if on else ""}"><div class="linfo"><div class="lh"><b>{letter}</b>{name}</div>'
                f'<div class="lmeta">{meta}</div></div><div class="lbtns">'
                f'<div class="sbtn">◀</div><div class="sbtn">▶</div><div class="sbtn{" lit" if on else ""}">ON</div>'
                f'<div class="sbtn{" lit2" if solo else ""}">SOLO</div></div></div>')
    return f"""
<div class="sound">
  {wave}
  {card("A", "ALTO SAX · VIBRATO", "LEVEL 0 dB · PAN C · OCT 0")}
  {card("B", "TRUMPET · BRIGHT", "LEVEL −9 dB · PAN R12 · OCT +1")}
  <div class="desc">A warm alto lead with a trumpet an octave up, tucked in quietly. Scoops on the attack; hold notes
    for vibrato. Made for kompa melodies and gala hooks.</div>
</div>"""


def page_html(theme, view):
    t = THEMES[theme]
    css_vars = ";".join(f"--{k}:{v}" for k, v in t.items() if k not in ("label", "flag", "split", "palm_op"))
    if view == "settings":
        center = settings_center(t, theme)
    else:
        scr = screen_browse(t) if view == "browse" else screen_sound(t)
        center = f"""
<div class="screen">
  <div class="shead">
    <div class="arrow">◀</div>
    <div class="ptitle"><div class="pmeta"><span class="chip">KOMPA</span><span class="chip c2">HORNS</span>
      <span class="num">PRESET 001 / 128</span></div><div class="pname">Alto Lead Kompa</div></div>
    <div class="arrow">▶</div>
  </div>
  {scr}
</div>
<div class="btnrow">
  {button(284, 571, "BROWSE", view == "browse")}{button(400, 571, "SOUND", view == "sound")}
  {button(516, 571, "★ FAV")}{button(632, 571, "★ LIST")}{button(772, 571, "SETTINGS")}{button(888, 571, "INIT")}
</div>"""
    palm_l = svg_url(PALM, t["sym"])
    ICONS.update(TONE=svg_url(SUN, t["accent"]), ENVELOPE=svg_url(WAVE.replace('viewBox="0 0 120 20"', 'viewBox="0 -40 120 100"'), t["accent"]),
                 MOTION=svg_url(PALM, t["accent"]), SPACE=svg_url(HIBISCUS, t["accent"]))
    sun = svg_url(SUN, t["accent"])
    hib = svg_url(HIBISCUS, t["accent"])
    wave = svg_url(WAVE, t["accent2"])
    left = side_panel(8, ["TONE", "ENVELOPE"], t, (1, 2))
    right = side_panel(1004, ["MOTION", "SPACE"], t, (3, 4))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Pacifico;src:url({font_url("Pacifico-Regular.ttf")})}}
@font-face{{font-family:Outfit;src:url({font_url("Outfit-Variable.ttf")});font-weight:100 900}}
@font-face{{font-family:Barlow;src:url({font_url("BarlowSemiCondensed-SemiBold.ttf")});font-weight:600}}
@font-face{{font-family:Barlow;src:url({font_url("BarlowSemiCondensed-Bold.ttf")});font-weight:700}}
:root{{{css_vars}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;overflow:hidden;background:var(--bg);font-family:Barlow,sans-serif;color:var(--ink)}}
.chassis{{position:absolute;inset:0;
  background:radial-gradient(900px 520px at 50% 58%, color-mix(in srgb,var(--bg2) 85%,transparent), transparent 70%),
             linear-gradient(180deg, color-mix(in srgb,var(--bg) 92%,#fff 8%), var(--bg))}}
.grain{{position:absolute;inset:0;opacity:.07;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='160' height='160' filter='url(%23n)'/></svg>")}}
svg.layer0{{position:absolute;left:0;top:0;width:{W}px;height:{H}px}}
.panel{{fill:color-mix(in srgb,var(--panel) 92%,#fff 3%);stroke:color-mix(in srgb,var(--ink) 12%,transparent);stroke-width:1.2}}
.stitle{{font:700 17px Barlow;letter-spacing:3px;fill:var(--accent);text-anchor:middle}}
.rule{{stroke:color-mix(in srgb,var(--ink) 14%,transparent);stroke-width:1}}
.track{{fill:none;stroke:color-mix(in srgb,var(--ink) 13%,transparent);stroke-width:5;stroke-linecap:round}}
.arc{{fill:none;stroke:var(--accent);stroke-width:5;stroke-linecap:round;filter:drop-shadow(0 0 5px var(--accent))}}
.cap{{fill:url(#capgrad);stroke:rgba(0,0,0,.55);stroke-width:1.5;filter:drop-shadow(0 4px 5px rgba(0,0,0,.55))}}
.capface{{fill:url(#facegrad)}}
.pointer{{stroke:var(--knobmark);stroke-width:4.5;stroke-linecap:round}}
.klabel{{font:600 18px Barlow;letter-spacing:1.2px;fill:var(--ink);text-anchor:middle}}
.kvalue{{font:700 22px Barlow;fill:var(--accent2);text-anchor:middle}}
.qtag{{font:600 11px Barlow;letter-spacing:1px;fill:color-mix(in srgb,var(--ink) 35%,transparent);text-anchor:middle}}
.palm{{position:absolute;width:150px;height:150px;opacity:.10;background:url({palm_l}) center/contain no-repeat}}
.top{{position:absolute;left:284px;top:6px;width:712px;height:54px;display:flex;align-items:center}}
.logo{{font-family:Pacifico;font-size:38px;line-height:1;color:var(--ink);position:relative;padding-left:46px;
  text-shadow:0 2px 0 rgba(0,0,0,.35),0 0 18px color-mix(in srgb,var(--accent) 45%,transparent)}}
.logo:before{{content:"";position:absolute;left:0;top:6px;width:40px;height:40px;background:url({sun}) center/contain no-repeat;
  filter:drop-shadow(0 0 6px var(--accent))}}
.logo small{{font:600 13px Barlow;letter-spacing:3px;color:var(--dim);margin-left:12px;vertical-align:middle}}
.status{{margin-left:auto;display:flex;gap:16px;align-items:center;font:600 13px Barlow;letter-spacing:2px;color:var(--dim)}}
.led{{width:12px;height:12px;border-radius:50%;background:var(--accent2);box-shadow:0 0 8px var(--accent2);display:inline-block;margin-left:6px;vertical-align:-1px}}
.cpu{{width:64px;height:8px;border-radius:4px;background:color-mix(in srgb,var(--ink) 15%,transparent);display:inline-block;margin-left:6px;position:relative;overflow:hidden}}
.cpu:after{{content:"";position:absolute;inset:0;width:22%;background:var(--accent2)}}
.wavebar{{position:absolute;left:284px;top:58px;width:712px;height:10px;background:url({wave}) repeat-x;background-size:60px 10px;opacity:.55}}
.screen{{position:absolute;left:284px;top:74px;width:712px;height:486px;border-radius:20px;overflow:hidden;
  background:radial-gradient(600px 300px at 50% -10%, color-mix(in srgb,var(--accent) 22%,transparent), transparent 70%),
             linear-gradient(180deg, color-mix(in srgb,var(--glass) 80%,var(--bg2) 20%), var(--glass));
  box-shadow:inset 0 0 0 2px rgba(0,0,0,.6), inset 0 0 0 4px color-mix(in srgb,var(--ink) 10%,transparent),
             0 10px 24px rgba(0,0,0,.45)}}
.screen:before{{content:"";position:absolute;right:-40px;bottom:-30px;width:260px;height:260px;opacity:.06;
  background:url({palm_l}) center/contain no-repeat;transform:scaleX(-1)}}
.screen:after{{content:"";position:absolute;inset:0;pointer-events:none;border-radius:20px;
  background:linear-gradient(160deg, rgba(255,255,255,.07), transparent 35%)}}
.shead{{display:flex;align-items:center;gap:10px;padding:14px 16px 10px;border-bottom:1px solid color-mix(in srgb,var(--ink) 12%,transparent)}}
.arrow{{width:{BTN_W}px;height:{BTN_H}px;border-radius:12px;display:grid;place-items:center;font-size:26px;color:var(--ink);
  background:color-mix(in srgb,var(--ink) 8%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 15%,transparent)}}
.ptitle{{flex:1;text-align:center}}
.pmeta{{display:flex;gap:8px;justify-content:center;align-items:center;font:600 14px Barlow;letter-spacing:2px;color:var(--dim)}}
.chip{{padding:2px 10px;border-radius:999px;background:color-mix(in srgb,var(--accent) 25%,transparent);color:var(--accent);font-weight:700}}
.chip.c2{{background:color-mix(in srgb,var(--accent2) 22%,transparent);color:var(--accent2)}}
.pname{{font:600 39px Outfit;letter-spacing:.5px;color:var(--ink);margin-top:2px;text-shadow:0 0 16px color-mix(in srgb,var(--accent) 35%,transparent)}}
.cols{{display:grid;grid-template-columns:168px 176px 1fr;gap:0;height:390px}}
.col{{padding:8px 8px 8px 10px;border-right:1px solid color-mix(in srgb,var(--ink) 10%,transparent);position:relative}}
.col:last-child{{border-right:0}}
.chead{{font:700 14px Barlow;letter-spacing:3px;color:var(--dim);padding:6px 8px 8px;display:flex;justify-content:space-between}}
.chead span{{font-weight:600;letter-spacing:1px}}
.row{{height:41px;display:flex;align-items:center;gap:10px;padding:0 10px;border-radius:10px;font:600 20px Barlow;letter-spacing:.8px;color:color-mix(in srgb,var(--ink) 82%,transparent)}}
.row.sel{{background:linear-gradient(90deg,color-mix(in srgb,var(--accent) 38%,transparent),color-mix(in srgb,var(--accent) 12%,transparent));
  color:var(--ink);box-shadow:inset 3px 0 0 var(--accent)}}
.prow{{font:500 22px Outfit;letter-spacing:.2px}}
.prow b{{font:600 15px Barlow;color:var(--dim);width:24px}}
.prow em{{margin-left:auto;font-style:normal;color:var(--accent2);font-size:18px}}
.dot{{width:11px;height:11px;border-radius:50%;flex:none}}
.d0{{background:var(--ink)}} .d1{{background:#e8a33d}} .d2{{background:#b06cff}} .d3{{background:#ff3b4f}}
.d4{{background:#ffd23f}} .d5{{background:#2fa84f}} .d6{{background:#ff5d8f}}
.scroll{{position:absolute;right:4px;top:52px;bottom:12px;width:5px;border-radius:3px;background:color-mix(in srgb,var(--ink) 10%,transparent)}}
.scroll i{{position:absolute;left:0;right:0;top:0;height:58%;border-radius:3px;background:color-mix(in srgb,var(--ink) 40%,transparent)}}
.sound{{padding:6px 22px 0}}
.wave{{width:668px;height:80px;display:block}}
.wl{{fill:none;stroke:var(--accent2);stroke-width:3;stroke-linejoin:round}}
.wl2{{fill:none;stroke:var(--accent2);stroke-width:12;opacity:.15}}
.layers{{}}
.layer{{display:flex;flex-direction:column;gap:8px;margin-top:8px;border-radius:14px;padding:9px 12px 10px 14px;background:color-mix(in srgb,var(--ink) 7%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 14%,transparent)}}
.layer.on{{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 70%,transparent)}}
.linfo{{display:flex;align-items:center;justify-content:space-between}}
.lbtns{{display:flex;gap:8px}}
.sbtn{{width:{BTN_W}px;height:{BTN_H}px;border-radius:12px;display:grid;place-items:center;font:700 17px Barlow;letter-spacing:2px;color:var(--ink);
  background:color-mix(in srgb,var(--ink) 8%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 16%,transparent)}}
.sbtn.lit{{background:color-mix(in srgb,var(--accent) 85%,#000 5%);color:#140b05;box-shadow:0 0 12px color-mix(in srgb,var(--accent) 55%,transparent)}}
.sbtn.lit2{{background:var(--accent2);color:#04110f}}
.lh{{font:600 22px Outfit;color:var(--ink);white-space:nowrap}}
.lh b{{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:8px;background:var(--accent);color:#000;font:700 18px Barlow;margin-right:8px;vertical-align:2px}}
.lmeta{{font:600 15px Barlow;letter-spacing:1.5px;color:var(--dim)}}
.desc{{font:400 18px Outfit;line-height:1.38;color:color-mix(in srgb,var(--ink) 82%,transparent);margin-top:12px}}
.btn{{position:absolute;border-radius:12px;display:flex;align-items:center;justify-content:center;gap:6px;
  font:700 17px Barlow;letter-spacing:2px;color:var(--ink);
  background:linear-gradient(180deg,color-mix(in srgb,var(--panel) 80%,#fff 14%),color-mix(in srgb,var(--panel) 92%,#000 8%));
  box-shadow:0 4px 0 rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.12), inset 0 0 0 1px color-mix(in srgb,var(--ink) 12%,transparent)}}
.btn.on{{background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 92%,#fff 8%),color-mix(in srgb,var(--accent) 80%,#000 20%));
  color:#140b05;box-shadow:0 4px 0 rgba(0,0,0,.45),0 0 16px color-mix(in srgb,var(--accent) 60%,transparent)}}
.hib{{position:absolute;width:26px;height:26px;opacity:.9;background:url({hib}) center/contain no-repeat}}
.sett{{position:absolute;left:284px;top:74px;width:712px;height:486px;border-radius:20px;padding:18px 22px;
  background:linear-gradient(180deg, color-mix(in srgb,var(--glass) 80%,var(--bg2) 20%), var(--glass));
  box-shadow:inset 0 0 0 2px rgba(0,0,0,.6), inset 0 0 0 4px color-mix(in srgb,var(--ink) 10%,transparent),0 10px 24px rgba(0,0,0,.45)}}
.sgrid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.sbox{{border-radius:14px;padding:10px 16px;background:color-mix(in srgb,var(--ink) 6%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 12%,transparent)}}
.sbox h4{{font:700 14px Barlow;letter-spacing:3px;color:var(--accent);margin-bottom:4px}}
.opt{{display:flex;justify-content:space-between;align-items:center;font:600 20px Barlow;letter-spacing:1px;height:36px}}
.opt{{border-radius:10px;padding:0 6px;margin:0 -6px}}
.opt span:last-child{{font:600 21px Outfit;color:var(--accent2)}}
.opt i{{font-style:normal;color:var(--dim);margin-left:10px}}
.cwrow{{display:flex;align-items:center;gap:10px}}
.cwname{{width:150px;text-align:center;font:600 24px Outfit;color:var(--ink)}}
.cw .swatches{{margin:0 0 0 auto}}
.swatches{{display:flex;gap:10px;margin-top:6px}}
.sw{{width:36px;height:36px;border-radius:12px;box-shadow:inset 0 0 0 2px rgba(255,255,255,.15)}}
.sw.on{{box-shadow:0 0 0 3px var(--ink)}}
.about{{font:400 16px Outfit;line-height:1.4;color:var(--dim);margin-top:10px}}
</style></head><body>
<div class="chassis"></div><div class="grain"></div>
<div class="palm" style="left:-38px;top:430px;transform:rotate(12deg)"></div>
<div class="palm" style="left:1170px;top:-30px;transform:scaleX(-1) rotate(10deg)"></div>
<svg class="layer0" viewBox="0 0 {W} {H}">
  <defs>
    <radialGradient id="capgrad" cx="40%" cy="30%" r="80%"><stop offset="0" stop-color="color-mix(in srgb, var(--cap) 60%, #fff 40%)"/>
      <stop offset=".55" stop-color="var(--cap)"/><stop offset="1" stop-color="#05040a"/></radialGradient>
    <radialGradient id="facegrad" cx="45%" cy="35%" r="75%"><stop offset="0" stop-color="rgba(255,255,255,.10)"/><stop offset="1" stop-color="rgba(0,0,0,.25)"/></radialGradient>
  </defs>
  {left}{right}
</svg>
<div class="top"><div class="logo">Tropix<small>ISLAND &amp; AFRO SOUNDS</small></div>
  <div class="status">MIDI<i class="led"></i><span style="margin-left:14px">CPU</span><i class="cpu"></i></div></div>
<div class="wavebar"></div>
{center}
</body></html>"""


def settings_center(t, theme):
    sw = "".join(f'<div class="sw{" on" if k == theme else ""}" style="background:linear-gradient(135deg,{v["accent"]},{v["bg2"]} 55%,{v["accent2"]})"></div>'
                 for k, v in THEMES.items())

    def opt(label, value):
        return f'<div class="opt"><span>{label}</span><span>{value}<i>›</i></span></div>'
    return f"""
<div class="sett">
  <div class="sgrid">
    <div class="sbox"><h4>TUNING</h4>{opt("A4 REFERENCE", "440 Hz")}{opt("TRANSPOSE", "0")}{opt("BEND RANGE", "2 st")}</div>
    <div class="sbox"><h4>PLAYING</h4>{opt("POLYPHONY", "24")}{opt("VELOCITY CURVE", "NORMAL")}{opt("MOD WHEEL", "VIBRATO")}</div>
    <div class="sbox"><h4>DISPLAY</h4>{opt("WAVE ANIMATION", "SMOOTH")}{opt("PRESET LIST", "BY GENRE")}</div>
    <div class="sbox"><h4>OUTPUT</h4>{opt("STEREO SPREAD", "60%")}{opt("OUTPUT LEVEL", "0 dB")}</div>
    <div class="sbox cw" style="grid-column:1 / span 2"><h4>COLORWAY</h4>
      <div class="cwrow"><div class="sbtn">◀</div><div class="cwname">{THEMES[theme]["label"].title()}</div><div class="sbtn">▶</div>
      <div class="swatches">{sw}</div></div></div>
  </div>
  <div class="about">Tropix 0.1 · 64 instruments from open recordings (CC0, CC BY 3.0, University of Iowa MIS) and
    original synthesis. Full credits in LICENSES.md.</div>
</div>
<div class="btnrow">{button(284, 571, "BROWSE")}{button(400, 571, "SOUND")}{button(516, 571, "★ FAV")}{button(632, 571, "★ LIST")}{button(772, 571, "SETTINGS", True)}{button(888, 571, "INIT")}</div>"""


def render(outdir, pages, themes):
    os.makedirs(outdir, exist_ok=True)
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport=dict(width=W, height=H), device_scale_factor=1)
        for th in themes:
            for view in pages:
                pg.set_content(page_html(th, view))
                pg.evaluate("document.fonts.ready")
                pg.wait_for_timeout(250)
                path = os.path.join(outdir, f"{view}_{th}.png")
                pg.screenshot(path=path)
                out.append(path)
        b.close()
    return out


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "docs", "ui")
    pages = sys.argv[2:] or ["browse", "sound", "settings"]
    for p in render(outdir, pages, list(THEMES)):
        print(p)
