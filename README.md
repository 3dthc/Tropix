# Tropix

A ROMpler instrument plugin for Akai MPC standalone devices, built around Afrobeat, amapiano, Haitian kompa, soca,
reggae and Hawaiian sounds. Work in progress.

## Status

- Steel pan engine (`tools/pan.py`): modal synthesis of tenor, double second, cello and bass pans. Listening demos in
  `docs/demos/`, rendered by `tools/pan_demo.py`; measurements by `tools/pan_check.py`.
- Amapiano log drum engine (`tools/logdrum.py`): five variations (classic, deep, knock, talking, gritty) with pitch
  drop, glide, saturation and a woody knock. Demos rendered by `tools/logdrum_demo.py`.
- Horns (`tools/build_horns.py`): trumpet (open, vibrato, stabs, harmon mute), trombone (sustain, stabs, falls),
  tenor sax (straight, vibrato, stabs) from VSCO 2 CE and VCSL, tuned per note and looped. Played by the
  offline sampler (`tools/sampler.py`) with scoops, falls and vibrato; demos by `tools/horn_demo.py`, checks by
  `tools/check_library.py`.
- Iowa horns: alto sax, soprano sax and a second trumpet (straight and vibrato, pp/mf/ff), split from the University
  of Iowa chromatic runs by `tools/split_runs.py`; slow-swelling soft notes get a tightened attack.
- Guitars (`tools/build_guitars.py`): Gretsch and Höfner hollow-body electrics (p/mf/f plus palm mutes) from
  Karoryfer's Black And Green Guitars, and Meta Open Sound steel-string (slack-key) and nylon (palm-wine) acoustics.
  Demos by `tools/guitar_demo.py` (strums, chorus, kompa/highlife/reggae/slack-key/palm-wine patterns).
- Keys (`tools/build_keys.py`): Kawai grand and Yamaha upright (VCSL), Wurlitzer, CP80 and Pianet (Greg Sullivan,
  CC BY 3.0), TX81Z FM keys. Basses (`tools/build_bass.py`): flatwound and roundwound electric bass (Karoryfer).
- Percussion and mallets (`tools/build_perc.py`): the island percussion kit (congas, bongos, shakers, bells,
  claves, guiro, slit drum, frame drums, siren), the bobobo and cajon kit, marimba, balafon, vibraphone, kalimba
  and mbira. Demos by `tools/band_demo.py`.
- Engines rendered to multisamples by `tools/build_engines.py`: tine piano (`tools/tine.py`), tonewheel organ in three
  registrations (`tools/organ.py`), the four pans and a seamlessly looping roll, the five log drums, modeled
  timbales, ipu and melodica (`tools/perc_model.py`), and six synth voices (`tools/synths.py`) whose loops repeat
  exactly; VCSL chromatic harmonica sits with them. Pedal and lap steel (`tools/build_steels.py`) are the Black And
  Green guitars reshaped into swelled, sustained steel tones. Demos by `tools/engine_demo.py`.

## UI

Mockups of the plugin area (1280 x 628) in six colorways are in `docs/ui/`, drawn by `tools/ui_mockup.py` (HTML
rendered by headless Chromium): BROWSE (genre, type and preset lists), SOUND (layers A and B) and SETTINGS.
Fonts: Pacifico (logo), Outfit and Barlow Semi Condensed, all SIL Open Font License (`vst/fonts/`).

## Sound sources

Every sampled sound comes from recordings that allow redistribution in a public plugin (CC0, CC BY, or "without
restrictions"); sounds with no good free source are synthesized from scratch. The full sourcing plan and licenses
will be listed in `library/LICENSES.md`.
