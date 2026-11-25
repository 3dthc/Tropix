# Testing Tropix

## Offline (done before every release)

- `tools/render_test.c`: every preset plays, none silent or clipping, worst render block well under 2902 µs.
- mpc-vst-plugins `tools/test_port.sh vst/vst.json`: PASSED under ASan/UBSan (names, set/get, options, stepping,
  programs, chunk round trip, two threads).
- `python3 tools/make_skin.py --mockup <dir>`: every view in every colorway looks right with live text.

## On the MPC

| # | Try | Expect |
| --- | --- | --- |
| 1 | Insert Tropix on a keygroup/plugin track | It opens on BROWSE with "Amapiano Keys"; notes play at once |
| 2 | Tap KOMPA, then HORNS | 7 horn presets; the genre and type rows light |
| 3 | Tap HORNS again | every type in KOMPA, in pages of 8; the heading says the page |
| 4 | Tap a preset, play | it loads ("LOADING SOUNDS..." at most briefly the first time) and plays |
| 5 | ◀ ▶ in the header, the data wheel after touching the name, Q-Link 16 | one preset per step, inside the list |
| 6 | Turn each of the 16 knobs (touch and Q-Links) | the sound changes; the value under the knob updates; header says EDITED; RESET lights |
| 7 | RESET | the preset's own settings come back, EDITED goes away |
| 8 | ★ FAV, then ★ FAVS (under the genres) | the star shows by the name; the list shows the favourite; ★ FAVS again goes back |
| 9 | LAYERS view | waveform moves while playing; both layer cards show their sounds |
| 10 | ◀ ▶ on a layer; touch its name and turn the wheel or drag | the layer's sound changes |
| 11 | Touch LEVEL / PAN / OCTAVE / FINE, then turn the wheel or drag up/down | the value moves; the sound follows |
| 12 | ON and SOLO on each layer | the layer turns off / plays alone |
| 13 | "Alto Lead Kompa": play a legato line | notes slide into each other with a scoop; vibrato comes in on held notes |
| 14 | "Kompa Percussion": play C2 up, and C6 up | island kit from C2; timbales from C6 |
| 15 | SETTINGS: tap VOICE MODE; turn the A4 TUNING knob (drag, or touch it and turn the wheel) | POLY / MONO / LEGATO step; 440 Hz moves by 1 per wheel click |
| 16 | Colorway ◀ ▶, one tap at a time | one colorway per tap, all nine, the whole page changes |
| 17 | Mod wheel, pressing into a pad, pitch bend, sustain pedal | vibrato (default) from wheel and pressure, bend ±2, sustain |
| 17b | Play one key soft to hard | it gets louder smoothly all the way, no jump |
| 18 | Save the project, reload it | preset, edits, favourites and colorway come back |
| 19 | Two Tropix tracks at once, chords on both | both play; no glitches; MPC's CPU meter stays comfortable; an idle Tropix costs almost nothing |
| 20 | MPC's PRESET menu in the plugin header | lists all 128; picking one loads it and the browser shows it |
| 21 | ARP view: MODE ARP, hold a chord, play with the project stopped, then running | notes repeat in time with the project; steps stay on the grid across a loop and a tempo change |
| 22 | STYLE (direction), RATE, OCTAVES, GATE, SWING, LATCH | each changes what you hear; LATCH keeps going after you let go; the sustain pedal holds the notes |
| 23 | MODE PATTERN: hold one key, then a chord; try each STYLE | a phrase on the lowest key; chord hits play every held key |
| 24 | MODE CHORD, STRUM 0 then 40 ms | one key plays the chord; with a strum the notes start in turn; releasing the key ends them |
| 25 | Switch mode with keys held, change preset with the arp on | nothing hangs; the arp settings stay |
