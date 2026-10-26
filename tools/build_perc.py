#!/usr/bin/env python3
"""Build the Tropix percussion kits and mallet / thumb-piano instruments.

    python3 -I tools/build_perc.py [instrument ...]

Kits put one sound per key (with its real velocity layers), starting at C2 (MIDI 36):

  island_perc   congas (tumba, conga, quinto; open and muted), bongos, shakers, cabasa, agogo, cowbells, claves,
                woodblock, guiro, slit drum, frame drums, mark tree, siren. VCSL and VSCO 2 CE (CC0).
  west_africa   Ghanaian bobobo drums and a cajon (Karoryfer Gogodze Phu Vol I, CC0).

Pitched (VCSL, CC0): marimba, balafon (traditional mallets, then hard mallets for the loudest strikes), vibraphone, kalimba (Kenya), mbira
(Mavembe, Zimbabwe). Thumb pianos are tuned by ear to their own scales; each zone is retuned to the nearest
equal-tempered note so they play in tune with the rest of Tropix.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_horns import files, layer  # noqa: E402
from prep import LIB, build_instrument, folder_zones, measured_cents, write_credits  # noqa: E402

RAW = os.path.join(LIB, "raw")
OUT = os.path.join(LIB, "library")
VI = os.path.join(RAW, "VCSL", "Idiophones")
VS = os.path.join(VI, "Struck Idiophones")
VP = os.path.join(VI, "Plucked Idiophones")
VM = os.path.join(RAW, "VCSL", "Membranophones", "Struck Membranophones")
VSCO1 = os.path.join(RAW, "VSCO-2-CE", "VSCO 1 Percussion")
GOG = os.path.join(RAW, "Gogodze", "Samples")


def hit(key, pattern, layer_re=r"_v[l]?(\d)_", max_len=1.5, rr=r"_rr1", order=None):
    """One kit key: the files matching `pattern` (first round robin), their dynamics spread over velocity 1-127."""
    ps = sorted(glob.glob(pattern))
    if rr and any(re.search(rr, os.path.basename(p)) for p in ps):
        ps = [p for p in ps if re.search(rr, os.path.basename(p))]
    by = {}
    for p in ps:
        m = re.search(layer_re, os.path.basename(p)) if layer_re else None
        lab = m.group(1) if m else "0"
        by.setdefault(lab, p)
    labs = [o for o in order if o in by] if order else sorted(by)
    n = len(labs)
    zones = []
    for i, lab in enumerate(labs):
        lo, hi = 1 + round(127 * i / n), round(127 * (i + 1) / n)
        zones.append(dict(path=by[lab], root=key, vel=i + 1, lovel=1 if i == 0 else lo, hivel=hi, max_len=max_len))
    if not zones:
        raise SystemExit(f"no files for key {key}: {pattern}")
    return zones


def island_perc():
    j = os.path.join
    k = []
    for key, pat, kw in [
        (36, j(VM, "Conga", "Tumba_HitN_*"), {}), (37, j(VM, "Conga", "Tumba_HitFM_*"), {}),
        (38, j(VM, "Conga", "Conga_HitN_*"), {}), (39, j(VM, "Conga", "Conga_HitFM_*"), {}),
        (40, j(VM, "Conga", "Quinto_HitN_*"), {}), (41, j(VM, "Conga", "Quinto_HitFM1_*"), {}),
        (42, j(VM, "Bongos", "BongoL_Hit1_*"), {}), (43, j(VM, "Bongos", "BongoL_HitMuted2_*"), {}),
        (44, j(VM, "Bongos", "BongoH_Hit1_*"), {}), (45, j(VM, "Bongos", "BongoH_HitMuted1_*"), {}),
        (46, j(VS, "Shaker, Small", "Mid_ShakerHighFaster_Down_*"), dict(layer_re=None)),
        (47, j(VS, "Shaker, Small", "Mid_ShakerHighFaster_Up_*"), dict(layer_re=None)),
        (48, j(VS, "Shaker, Small", "Mid_Shaker_Slap_*"), dict(layer_re=None)),
        (49, j(VS, "Shaker, Large", "LShaker_Hit_*"), dict(layer_re=None)),
        (50, j(VS, "Shaker, Large", "LShaker_Shake1D_*"), dict(layer_re=None, rr=None)),
        (51, j(VS, "Cabasa", "Cabasa1_Hit_*"), dict(layer_re=None)),
        (52, j(VS, "Cabasa", "Cabasa1_Rub_*"), dict(layer_re=None)),
        (53, j(VS, "Agogo Bells", "Agogo_High_*"), {}), (54, j(VS, "Agogo Bells", "Agogo_Low_*"), {}),
        (55, j(VS, "Cowbells", "Cowbell1_Hit_*"), {}), (56, j(VS, "Cowbells", "Cowbell1_Muted_*"), {}),
        (57, j(VS, "Cowbells", "Cowbell2_Normal_*"), {}),
        (58, j(VS, "Claves", "Claves1_Hit_*"), dict(layer_re=None)),
        (59, j(VS, "Woodblock", "wood_click_*"), dict(layer_re=r"_(pp|mp|f|ff)[_.]", rr=None, order=["pp", "mp", "f", "ff"])),
        (60, j(VS, "Guiro", "Guiro_Hit_*"), dict(layer_re=None)),
        (61, j(VS, "Guiro", "Guiro_Med_rr1_Mid.wav"), dict(layer_re=None, rr=None, max_len=2.5)),
        (62, j(VS, "Slit Drum", "LogDrumHi_*"), {}), (63, j(VS, "Slit Drum", "LogDrumLo_*"), {}),
        (64, j(VM, "Frame Drum", "HDrumL_Hit_*"), {}), (65, j(VM, "Frame Drum", "HDrumL_HitMuted_*"), {}),
        (66, j(VM, "Frame Drum", "HDrumS_Hit_*"), {}), (67, j(VM, "Frame Drum", "HDrumS_HitMuted_*"), {}),
        (68, j(VS, "Mark Trees", "Legacy", "windchimes_slowDesc1.wav"), dict(layer_re=None, rr=None, max_len=4.0)),
        (69, j(VS, "Mark Trees", "Legacy", "windchimes_asc1.wav"), dict(layer_re=None, rr=None, max_len=4.0)),
        (70, j(RAW, "VCSL", "Aerophones", "Free Aerophones", "Siren", "Main_SirenWhistle-005.wav"),
         dict(layer_re=None, rr=None, max_len=4.0)),
    ]:
        k += hit(key, pat, **kw)
    return k


def west_africa():
    j = os.path.join
    k = []
    lay = dict(layer_re=r"_vl(\d)_")
    for key, pat, kw in [
        (36, j(GOG, "bobobo", "bobobo_bass_vl*"), lay),
        (38, j(GOG, "bobobo", "bobobo_tenor_l_vl*"), lay), (39, j(GOG, "bobobo", "bobobo_tenor_s_vl*"), lay),
        (40, j(GOG, "bobobo", "bobobo_tenor_l2_vl*"), lay), (41, j(GOG, "bobobo", "bobobo_tenor_s2_vl*"), lay),
        (43, j(GOG, "bobobo", "bobobo_treble_l_vl*"), lay), (44, j(GOG, "bobobo", "bobobo_treble_s_vl*"), lay),
        (45, j(GOG, "bobobo", "bobobo_treble_l2_vl*"), lay), (46, j(GOG, "bobobo", "bobobo_treble_s2_vl*"), lay),
        (48, j(GOG, "cajon", "dyn", "cajon_sl1_vl*"), lay), (49, j(GOG, "cajon", "dyn", "cajon_sl3_vl*"), lay),
        (50, j(GOG, "cajon", "dyn", "cajon_sl5_vl*"), lay), (51, j(GOG, "cajon", "dyn", "cajon_sl7_vl*"), lay),
        (52, j(GOG, "cajon", "dyn", "cajon_sr1_vl*"), lay), (53, j(GOG, "cajon", "dyn", "cajon_sr2_vl*"), lay),
    ]:
        k += hit(key, pat, **kw)
    return k


def spectral_tune(zones):
    """Thumb pianos: tune from the strongest of the first harmonics (the steady-pitch estimate is thrown by the
    tines' buzz and beating), so every zone lands on its equal-tempered note."""
    for z in zones:
        c = measured_cents(z["audio"], z["root"])
        z["tune"] = -round(c) if abs(c) <= 60 else 0
    return zones


KIT = dict(kit=True, trim=True, fade_s=0.15, floor_db=-50.0, norm="rms", rms_db=-17.0, mono=True)
TONED = dict(fade_s=0.4, floor_db=-55.0, norm="rms", rms_db=-17.0, mono=True, even_keys=6.0)

BUILDS = {
    "island_perc": ("PERCUSSION", "vcsl", island_perc, KIT),
    "west_africa": ("PERCUSSION", "karoryfer_gogodze", west_africa, KIT),
    "marimba": ("MALLETS", "vcsl",
                lambda: folder_zones(files(VS, "Marimba", "*.wav"), r"_([A-G]#?\d)_",
                                     layer(r"_(soft|med|loud)_", ["soft", "med", "loud"]), max_len=3.0,
                                     fine_tune=True),
                TONED),
    "balafon": ("MALLETS", "vcsl",
                lambda: folder_zones([p for p in files(VS, "Balafon", "*Mallet", "*_rr1_*.wav") if "Soft" not in p],
                                     r"_([A-G]#?\d)_",
                                     lambda p: (0 if "Traditional" in p else 1) * 3 + int(re.search(r"_vl(\d)", p).group(1)),
                                     max_len=2.5, fine_tune=True),
                TONED),
    "vibraphone": ("MALLETS", "vcsl",
                   lambda: folder_zones(files(VS, "Vibraphone", "*Mallets", "*_rr1_*.wav"), r"_([A-G]#?\d)_",
                                        lambda p: ("1" if "soft" in p else "2") + re.search(r"_v(\d)_", p).group(1),
                                        max_len=4.0, fine_tune=True),
                   TONED),
    "kalimba": ("MALLETS", "vcsl",
                lambda: spectral_tune(folder_zones(files(VP, "Kalimba, Kenya", "*.wav"), r"_([A-G]#?\d)_k",
                                                   lambda p: 0, max_len=3.0)),
                TONED),
    "mbira": ("MALLETS", "vcsl",
              lambda: spectral_tune(folder_zones(files(VP, "Mbira Mavembe (Gandanga), Zimbabwe, Low G", "*.wav"),
                                                 r"_([A-G]#?\d)_k", lambda p: 0, max_len=3.0)),
              TONED),
}


if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDS)
    for name in names:
        cat, src, zf, kw = BUILDS[name]
        k = build_instrument(name, cat, src, zf(), OUT, **kw)
        roots = sorted({z["root"] for z in k["zones"]})
        print(f"{name:12s} zones={len(k['zones']):3d} layers={len({z['lovel'] for z in k['zones']})} "
              f"keys={roots[0]}-{roots[-1]} ({len(roots)}) {k['total_bytes'] / 1e6:5.1f} MB")
    write_credits(OUT)
