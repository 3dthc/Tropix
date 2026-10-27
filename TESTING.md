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
| 8 | ★ FAV, then ★ LIST | the star shows by the name; the list shows the favourite; ★ LIST again goes back |
| 9 | LAYERS view | waveform moves while playing; both layer cards show their sounds |
| 10 | ◀ ▶ on a layer; touch its name and turn the wheel | the layer's sound changes |
| 11 | Touch LEVEL / PAN / OCTAVE / FINE, turn the wheel | the value steps; the sound follows |
| 12 | ON and SOLO on each layer | the layer turns off / plays alone |
| 13 | "Alto Lead Kompa": play a legato line | notes slide into each other with a scoop; vibrato comes in on held notes |
| 14 | "Kompa Percussion": play C2 up, and C6 up | island kit from C2; timbales from C6 |
| 15 | SETTINGS: tap VOICE MODE; touch A4 REFERENCE and turn the wheel | POLY / MONO / LEGATO step; 440 Hz moves by 1 |
| 16 | Colorway ◀ ▶, one tap at a time | one colorway per tap, all nine, the whole page changes |
| 17 | Mod wheel, pressing into a pad, pitch bend, sustain pedal | vibrato (default) from wheel and pressure, bend ±2, sustain |
| 17b | Play one key soft to hard | it gets louder smoothly all the way, no jump |
| 18 | Save the project, reload it | preset, edits, favourites and colorway come back |
| 19 | Two Tropix tracks at once | both play; no glitches |
| 20 | MPC's PRESET menu in the plugin header | lists all 128; picking one loads it and the browser shows it |
