# Tropix

A ROMpler instrument plugin for Akai MPC standalone devices, built around Afrobeat, amapiano, Haitian kompa, soca,
reggae and Hawaiian sounds. Work in progress.

## Status

- Steel pan engine (`tools/pan.py`): modal synthesis of tenor, double second, cello and bass pans. Listening demos in
  `docs/demos/`, rendered by `tools/pan_demo.py`; measurements by `tools/pan_check.py`.
- Amapiano log drum engine (`tools/logdrum.py`): five variations (classic, deep, knock, talking, gritty) with pitch
  drop, glide, saturation and a woody knock. Demos rendered by `tools/logdrum_demo.py`.

## Sound sources

Every sampled sound comes from recordings that allow redistribution in a public plugin (CC0, CC BY, or "without
restrictions"); sounds with no good free source are synthesized from scratch. The full sourcing plan and licenses
will be listed in `library/LICENSES.md`.
