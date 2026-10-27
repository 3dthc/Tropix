"""The Tropix factory presets: 128 sounds, in the browser's type order. tools/tropix_params.py writes them into
vst/params.json (the PRESET list MPC shows) and src/presets.h (what the engine sets when one is picked).

Each preset has a type (the browser's TYPE column), one or more genres (its first genre is the one its header chip
shows; the GENRE column lists it under every one), a name, a description (two lines on the LAYERS view), up to two
layers and the sound settings. Values are written in musical units here and converted to the engine's knob
positions below. The global settings (volume, tuning, playing, colorway) are not part of a preset.

Kits (one sound per key): a layer's OCTAVE moves the kit up or down the keyboard instead of retuning it."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack_tropix import ORDER, TYPES  # noqa: E402

INST = [n for n, _, _ in ORDER]
GENRES = ["ALL", "AFROBEAT", "AMAPIANO", "KOMPA", "SOCA", "REGGAE", "HAWAIIAN"]
G = dict(AF="AFROBEAT", AM="AMAPIANO", KO="KOMPA", SO="SOCA", RE="REGGAE", HA="HAWAIIAN")


# ---- the engine's knob curves, inverted (src/engine.c)
def clip(x):
    return round(min(1.0, max(0.0, x)), 3)


def attack(sec):                   # 1 ms .. 10 s
    return clip(math.log10(sec / 0.001) / 4)


def dr(sec):                       # decay and release: 5 ms .. 10 s
    return clip(math.log(sec / 0.005) / math.log(2000))


def cutoff(hz):                    # 20 Hz .. 20 kHz
    return clip(math.log(hz / 20) / math.log(1000))


def lfo(hz):                       # 0.05 .. 20 Hz
    return clip(math.log(hz / 0.05) / math.log(400))


def level(db):                     # layer level: gain (level / 0.8)^2
    return clip(0.8 * 10 ** (db / 40))


def glide(sec):                    # 0 = off; 10 ms .. 2 s
    return 0.0 if sec <= 0 else clip(0.02 + 0.98 * math.log(sec / 0.01) / math.log(200))


def vib(cents):                    # vibrato depth: 60 ct x knob^2
    return clip(math.sqrt(cents / 60))


def bright(db):                    # tilt: +/- 12 dB of treble around the centre
    return clip(0.5 + db / 24)


BASE = dict(cutoff=1.0, resonance=0.0, bright=0.5, drive=0.0, attack=attack(0.001), decay=0.5, sustain=1.0,
            release=dr(0.5), glide=0.0, vibrato=0.0, lfo_rate=lfo(5.0), lfo_depth=0.0, chorus=0.0, delay=0.0,
            reverb=0.2, env_amt=0.5, key_track=0.0, voice_mode="Poly", lfo_target="Tremolo", scoop="Off",
            delay_time="1/8.", delay_fb=0.4, delay_tone=0.55, delay_width=0.8, rev_size=0.6, rev_damp=0.4,
            rev_predelay=0.1, rev_width=1.0, trim=0.0)
PRESETS = []
# per-preset output trims in dB, measured by tools/balance.py so the presets play at a similar loudness
_TRIM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preset_trim.json")
TRIMS = {} if os.environ.get("TROPIX_NO_TRIM") or not os.path.exists(_TRIM_PATH) else __import__("json").load(open(_TRIM_PATH))


def L(inst, db=0.0, pan=0.0, octave=0, fine=0):
    assert inst in INST, inst
    return (inst, level(db), pan, octave, fine)


def P(typ, genres, name, desc, layers, **kw):
    gs = [G[g] for g in genres.split()]
    assert typ in TYPES and gs and len(name) <= 22 and len(desc) <= 125 and 1 <= len(layers) <= 2, (name, desc)
    for k in kw:
        assert k in BASE, k
    v = dict(BASE, **kw)
    v["trim"] = float(TRIMS.get(name, 0.0))
    for i, l in enumerate("ab"):
        if i < len(layers):
            inst, lvl, pan, octv, fine = layers[i] if isinstance(layers[i], tuple) else L(layers[i])
            v.update({"layer_" + l: 1, "inst_" + l: INST.index(inst), "level_" + l: lvl, "pan_" + l: pan,
                      "octave_" + l: octv, "fine_" + l: fine})
        else:
            v.update({"layer_" + l: 0, "inst_" + l: 0, "level_" + l: 0.8, "pan_" + l: 0.0, "octave_" + l: 0, "fine_" + l: 0})
    PRESETS.append(dict(type=typ, genres=gs, name=name, desc=desc, values=v))


# =============================================================== KEYS
P("KEYS", "AM", "Amapiano Keys", "Soft tine e-piano chords in a warm haze of chorus, echo and room. Lay down log "
  "drum grooves under it.", ["tine_piano"],
  cutoff=cutoff(4500), release=dr(0.7), chorus=0.25, delay=0.15, delay_time="1/8.", delay_fb=0.3, reverb=0.35,
  rev_size=0.7)
P("KEYS", "AM", "Private School Piano", "A mellow, jazzy grand for private school amapiano: soft hammers, long "
  "room, gentle sustain.", ["grand_piano"],
  cutoff=cutoff(6000), key_track=0.3, release=dr(0.9), reverb=0.4, rev_size=0.75, rev_damp=0.55)
P("KEYS", "AM AF", "Deep House Reed", "Reed e-piano with a slow tremolo and a quiet pad underneath, for deep, "
  "late-night chords.", [L("wurlitzer"), L("island_pad", -14)],
  lfo_rate=lfo(4.5), lfo_depth=0.22, release=dr(0.6), chorus=0.15, reverb=0.3)
P("KEYS", "KO", "Kompa Piano", "A bright, close grand that cuts through a kompa band. Montunos and fast "
  "chord stabs.", ["grand_piano"],
  bright=bright(3), release=dr(0.45), reverb=0.2, rev_size=0.45)
P("KEYS", "KO", "Gouyad E-Piano", "Tine e-piano with chorus and a lazy tremolo, made for slow gouyad grooves.",
  ["tine_piano"],
  chorus=0.35, lfo_rate=lfo(4.0), lfo_depth=0.15, release=dr(0.6), reverb=0.25)
P("KEYS", "KO RE", "Kompa Organ", "Full drawbar organ through a spinning speaker, driven a little. Holds the "
  "chords behind the horns.", ["organ_full"],
  drive=0.15, attack=attack(0.006), release=dr(0.12), reverb=0.2)
P("KEYS", "RE", "Bubble Organ", "The reggae organ shuffle: short, percussive organ chops. Play the bubble rhythm "
  "between the guitar skanks.", ["organ_bubble"],
  attack=attack(0.003), release=dr(0.07), reverb=0.12, rev_size=0.4)
P("KEYS", "RE", "Skank Piano", "Upright piano clipped short for offbeat skanks: tight, woody and dry.",
  ["upright_piano"],
  cutoff=cutoff(3500), decay=dr(0.35), sustain=0.3, release=dr(0.1), reverb=0.12)
P("KEYS", "RE", "Dub Organ", "Percussive organ thrown into a long echo. Hit one chord and ride the delay.",
  ["organ_perc"],
  release=dr(0.15), delay=0.35, delay_time="1/4.", delay_fb=0.55, delay_tone=0.4, reverb=0.3, rev_size=0.75)
P("KEYS", "RE", "Pluck E-Piano Skank", "A plucky reed e-piano with a short echo. Snappy offbeat chords for roots "
  "and lovers rock.", ["pianet"],
  release=dr(0.12), delay=0.15, delay_time="1/8", delay_fb=0.25, reverb=0.18)
P("KEYS", "AF", "Highlife Upright", "An honest upright piano in a small room, for highlife chord rolls and "
  "afrobeat vamps.", ["upright_piano"],
  release=dr(0.5), reverb=0.18, rev_size=0.45)
P("KEYS", "AF", "Lagos Reed Piano", "Reed e-piano pushed into a little grit with tremolo, the classic afrobeat "
  "keyboard bite.", ["wurlitzer"],
  drive=0.2, lfo_rate=lfo(5.5), lfo_depth=0.25, release=dr(0.35), reverb=0.2)
P("KEYS", "AF", "Afrobeat Combo Organ", "Percussive organ with drive for long, hypnotic afrobeat vamps.",
  ["organ_perc"],
  drive=0.28, bright=bright(2), release=dr(0.1), reverb=0.18)
P("KEYS", "AF AM", "Afro Electric Grand", "Electric grand piano with chorus: shimmering, bell-like chords for "
  "modern afrobeats.", ["cp80"],
  chorus=0.3, release=dr(0.55), reverb=0.25)
P("KEYS", "SO", "Soca Piano", "A bright grand with a touch of FM shine on top, for driving soca piano riffs.",
  [L("grand_piano"), L("fm_keys", -12)],
  bright=bright(4), release=dr(0.4), reverb=0.2)
P("KEYS", "SO", "Carnival Organ", "Bright full organ, a little dirty, for road march chords and big intros.",
  ["organ_full"],
  bright=bright(3), drive=0.1, release=dr(0.15), reverb=0.22)
P("KEYS", "SO AF", "Island FM Keys", "Glassy FM electric piano with chorus and echo, very 80s island pop.",
  ["fm_keys"],
  chorus=0.3, delay=0.2, delay_time="1/8.", reverb=0.25)
P("KEYS", "HA", "Aloha Piano", "A soft, warm upright in a wide room. Easy-listening island ballads.",
  ["upright_piano"],
  cutoff=cutoff(5000), release=dr(0.8), reverb=0.35, rev_size=0.7)
P("KEYS", "HA", "Tiki Lounge Keys", "Tine e-piano with vibes doubling the attack and a slow tremolo: exotica "
  "lounge chords.", [L("tine_piano"), L("vibraphone", -10)],
  lfo_rate=lfo(4.0), lfo_depth=0.2, release=dr(0.8), reverb=0.35)
P("KEYS", "KO RE", "Sunday Gospel Organ", "Full organ with a grand piano tucked behind it, for slow praise "
  "songs and big endings.", [L("organ_full"), L("grand_piano", -8)],
  attack=attack(0.01), release=dr(0.4), reverb=0.32, rev_size=0.75)

# =============================================================== GUITARS
P("GUITARS", "KO", "Kompa Lead Guitar", "Hollow-body electric drenched in chorus with a short echo: the singing "
  "kompa lead guitar.", ["gretsch"],
  bright=bright(2), chorus=0.45, delay=0.15, delay_time="1/8.", delay_fb=0.3, release=dr(0.35), reverb=0.2)
P("GUITARS", "KO", "Kompa Rhythm Mute", "Palm-muted hollow-body with chorus, for the tight kompa rhythm "
  "guitar pattern.", ["gretsch_mute"],
  chorus=0.35, release=dr(0.08), reverb=0.15)
P("GUITARS", "KO", "Twoubadou Guitar", "Nylon-string guitar for twoubadou serenades: warm, fingerpicked, "
  "close.", ["palm_wine"],
  release=dr(0.4), reverb=0.2)
P("GUITARS", "KO AF", "Mini-Jazz Chorus", "Archtop electric through a deep chorus, the mini-jazz sound of "
  "the 70s.", ["hofner"],
  chorus=0.6, delay=0.1, delay_time="1/8", release=dr(0.35), reverb=0.22)
P("GUITARS", "AF", "Highlife Lead", "Bright archtop electric with a little echo, for looping highlife lead "
  "lines.", ["hofner"],
  bright=bright(2), delay=0.1, delay_time="1/8", release=dr(0.3), reverb=0.18)
P("GUITARS", "AF", "Afrobeat Scratch", "Muted archtop scratch, dry and percussive. The rhythm guitar that "
  "locks with the drums.", ["hofner_mute"],
  drive=0.1, release=dr(0.06), reverb=0.08)
P("GUITARS", "AF", "Palm-Wine Guitar", "Nylon guitar for gentle palm-wine picking, sweet and woody.",
  ["palm_wine"],
  release=dr(0.4), reverb=0.2, rev_size=0.5)
P("GUITARS", "AF", "Soukous Sebene", "Bright hollow-body with chorus and a fast echo, for the high, running "
  "sebene guitar.", ["gretsch"],
  bright=bright(4), chorus=0.3, delay=0.18, delay_time="1/16", delay_fb=0.3, release=dr(0.3), reverb=0.2)
P("GUITARS", "AF", "Afro Interlock", "Two muted guitars, one hollow and one archtop, spread left and right for "
  "interlocking riffs.", [L("gretsch_mute", 0, -0.45), L("hofner_mute", -4, 0.45)],
  release=dr(0.07), reverb=0.12)
P("GUITARS", "AM", "Amapiano Guitar Pluck", "A darkened archtop pluck with a dotted echo and a big room, for "
  "sparse amapiano melodies.", ["hofner"],
  cutoff=cutoff(3000), delay=0.3, delay_time="1/8.", delay_fb=0.45, release=dr(0.4), reverb=0.35, rev_size=0.75)
P("GUITARS", "RE", "Reggae Skank Guitar", "Muted, trebly chops for the offbeat skank, with a short slap echo.",
  ["gretsch_mute"],
  cutoff=cutoff(4500), bright=bright(2), release=dr(0.05), delay=0.12, delay_time="1/8", delay_fb=0.2, reverb=0.15)
P("GUITARS", "RE", "Lovers Rock Guitar", "Warm archtop electric with chorus and room, for smooth lovers rock "
  "licks.", ["hofner"],
  cutoff=cutoff(5000), chorus=0.3, release=dr(0.4), reverb=0.3)
P("GUITARS", "SO", "Soca Strum", "Bright steel-string acoustic for driving soca strums.", ["slack_key"],
  bright=bright(3), release=dr(0.35), reverb=0.15)
P("GUITARS", "SO HA", "Calypso Cuatro", "Ukulele doubled with a nylon guitar: the bright, chattering cuatro "
  "strum of calypso and parang.", [L("ukulele"), L("palm_wine", -6)],
  release=dr(0.3), reverb=0.18)
P("GUITARS", "HA", "Slack Key Sunset", "Steel-string acoustic for open-tuned slack key ballads, in a soft room.",
  ["slack_key"],
  release=dr(0.6), reverb=0.3, rev_size=0.65)
P("GUITARS", "HA", "Island Ukulele", "A soprano ukulele, plucked or strummed, bright and happy.", ["ukulele"],
  release=dr(0.35), reverb=0.18)
P("GUITARS", "HA", "Hawaiian Steel", "Lap steel that slides between notes (mono, with glide) and sings with "
  "vibrato. Play legato.", ["lap_steel"],
  voice_mode="Legato", glide=glide(0.18), vibrato=vib(22), release=dr(0.4), reverb=0.35, rev_size=0.7)
P("GUITARS", "HA RE", "Pedal Steel Swell", "Pedal steel with a soft, swelling attack and a long room. Chords "
  "bloom in.", ["pedal_steel"],
  attack=attack(0.25), release=dr(0.7), reverb=0.35, rev_size=0.75)
P("GUITARS", "HA", "Aloha Steel Duo", "Lap steel over a slack key guitar: the classic Hawaiian pairing.",
  [L("lap_steel"), L("slack_key", -6)],
  vibrato=vib(14), release=dr(0.5), reverb=0.32)

# =============================================================== HORNS
P("HORNS", "KO", "Alto Lead Kompa", "A warm alto lead that scoops into notes and sings with vibrato. Made for "
  "kompa melodies and gala hooks.", ["alto_sax_vib"],
  voice_mode="Legato", glide=glide(0.06), scoop="Light", release=dr(0.25), reverb=0.25)
P("HORNS", "KO", "Sax & Trumpet Section", "Alto sax with a trumpet tucked in quietly: the two-horn front line "
  "of a kompa band.", [L("alto_sax"), L("trumpet_bright", -5)],
  scoop="Light", release=dr(0.2), reverb=0.22)
P("HORNS", "KO SO", "Kompa Brass Hits", "Trumpet stabs with trombone an octave down. Short, punchy section "
  "hits.", [L("trumpet_stab"), L("trombone_stab", -3, 0, -1)],
  release=dr(0.12), reverb=0.2)
P("HORNS", "KO", "Twoubadou Sax", "Breathy tenor with vibrato and a soft scoop, for slow, romantic lines.",
  ["tenor_sax_vib"],
  scoop="Light", release=dr(0.3), reverb=0.3, rev_size=0.65)
P("HORNS", "KO", "Gala Horns", "Trumpet and alto in unison: the bright horn sound of a big kompa gala.",
  [L("trumpet"), L("alto_sax", -3)],
  scoop="Light", release=dr(0.2), reverb=0.25)
P("HORNS", "KO", "Kompa Soprano", "Soprano sax with vibrato, sweet and smooth, gliding between notes.",
  ["soprano_sax_vib"],
  voice_mode="Legato", glide=glide(0.05), scoop="Light", release=dr(0.25), reverb=0.28)
P("HORNS", "AF", "Afrobeat Horn Section", "Tenor sax and trumpet in unison, a little driven: the afrobeat "
  "horn line, big and raw.", [L("tenor_sax"), L("trumpet", -3)],
  drive=0.12, scoop="Light", release=dr(0.15), reverb=0.2)
P("HORNS", "AF", "Afro Tenor Solo", "Tenor sax for long solos: deep scoops, legato glide and a slow vibrato "
  "on held notes.", ["tenor_sax"],
  voice_mode="Legato", glide=glide(0.07), scoop="Deep", vibrato=vib(18), release=dr(0.25), reverb=0.25)
P("HORNS", "AF", "Highlife Trumpet", "Open trumpet with vibrato, bright and singing, for highlife melodies.",
  ["trumpet_bright_vib"],
  scoop="Light", release=dr(0.25), reverb=0.25)
P("HORNS", "AF SO", "Afro Brass Stabs", "Trumpet and tenor stabs together: tight accents for afrobeat and "
  "afro-soca.", [L("trumpet_stab"), L("tenor_sax_stab", -2)],
  release=dr(0.1), reverb=0.18)
P("HORNS", "AM AF", "Harmon Night", "Harmon-muted trumpet in a dark room with a soft echo, for late-night "
  "jazzy amapiano.", ["trumpet_harmon"],
  delay=0.25, delay_time="1/4.", delay_fb=0.4, delay_tone=0.4, release=dr(0.35), reverb=0.4, rev_size=0.75)
P("HORNS", "AM", "Amapiano Sax", "Alto sax with vibrato, wrapped in echo and a big room: the soulful sax of "
  "private school amapiano.", ["alto_sax_vib"],
  voice_mode="Legato", glide=glide(0.05), scoop="Light", delay=0.2, delay_time="1/8.", release=dr(0.35),
  reverb=0.4, rev_size=0.75)
P("HORNS", "SO", "Soca Horn Riff", "Bright trumpet and trombone together, for fast soca horn riffs.",
  [L("trumpet_bright"), L("trombone", -4)],
  bright=bright(2), release=dr(0.15), reverb=0.2)
P("HORNS", "SO", "Soca Brass Blast", "Trumpet and trombone stabs, driven hard. Big carnival brass hits.",
  [L("trumpet_stab"), L("trombone_stab", -2)],
  drive=0.12, bright=bright(2), release=dr(0.1), reverb=0.2)
P("HORNS", "SO", "Carnival Trombone Fall", "A trombone that falls off every note: drop it at the end of a "
  "phrase.", ["trombone_fall"],
  release=dr(0.2), reverb=0.22)
P("HORNS", "SO", "Calypso Trumpet", "Open trumpet with a light scoop, warm and round, for calypso lines.",
  ["trumpet"],
  scoop="Light", release=dr(0.2), reverb=0.22)
P("HORNS", "RE", "Ska Horns", "Trumpet with trombone an octave below, for ska and rocksteady horn lines.",
  [L("trumpet"), L("trombone", -2, 0, -1)],
  release=dr(0.15), reverb=0.25)
P("HORNS", "RE", "Rockers Trombone", "Mellow trombone with a gentle scoop and vibrato, for roots melodies.",
  ["trombone"],
  scoop="Light", vibrato=vib(12), release=dr(0.25), reverb=0.3)
P("HORNS", "RE", "Roots Melodica", "Reedy melodica floating in echo and room: the far-east roots sound.",
  ["melodica"],
  delay=0.3, delay_time="1/4.", delay_fb=0.45, release=dr(0.2), reverb=0.35, rev_size=0.7)
P("HORNS", "RE", "Dub Trumpet Echo", "Trumpet sent into a long, dark echo. One phrase, then let it repeat.",
  ["trumpet"],
  delay=0.45, delay_time="1/4.", delay_fb=0.58, delay_tone=0.35, release=dr(0.25), reverb=0.3)
P("HORNS", "RE", "Reggae Sax Lead", "Tenor sax with vibrato, smoky and warm, for reggae solos.",
  ["tenor_sax_vib"],
  scoop="Light", release=dr(0.25), reverb=0.3)
P("HORNS", "HA", "Harmonica Breeze", "Harmonica with vibrato in a soft room, for easy island tunes.",
  ["harmonica_vib"],
  release=dr(0.2), reverb=0.28)
P("HORNS", "RE", "Melodica & Organ", "Melodica over a soft bubble organ: a one-man roots band.",
  [L("melodica"), L("organ_bubble", -9)],
  release=dr(0.18), delay=0.15, delay_time="1/4.", reverb=0.3)
P("HORNS", "SO KO", "Brass Swell", "Trumpet and trombone that swell in slowly and fade out long: brass "
  "pads behind a chorus.", [L("trumpet"), L("trombone", -3)],
  attack=attack(0.35), release=dr(0.6), reverb=0.32, rev_size=0.7)

# =============================================================== STEEL PAN
P("STEEL PAN", "SO", "Tenor Pan", "The lead steel pan: bright, ringing and sweet. Play melodies with two "
  "hands.", ["pan_tenor"],
  release=dr(0.7), reverb=0.25)
P("STEEL PAN", "SO", "Double Seconds", "Double second pans, a little lower and rounder than the tenor, for "
  "strums and counter-melodies.", ["pan_double_second"],
  release=dr(0.7), reverb=0.25)
P("STEEL PAN", "SO", "Cello Pan Strum", "Cello pans for chord strums in the middle of the steelband.",
  ["pan_cello"],
  release=dr(0.6), reverb=0.25)
P("STEEL PAN", "SO", "Bass Pan", "The deep booming bass pans that drive a steelband.", ["pan_bass"],
  release=dr(0.4), reverb=0.15)
P("STEEL PAN", "SO", "Steelband Section", "Tenor pan with cello pan an octave below, a whole section under "
  "your fingers.", [L("pan_tenor"), L("pan_cello", -4, 0, -1)],
  release=dr(0.7), reverb=0.3)
P("STEEL PAN", "SO HA", "Pan Roll Pad", "Sustained pan rolls that hold as long as you do, soft and shimmering.",
  ["pan_roll"],
  attack=attack(0.06), release=dr(0.5), reverb=0.35, rev_size=0.7)
P("STEEL PAN", "SO", "Pan & Roll", "A struck tenor pan with a quiet roll sustaining behind it.",
  [L("pan_tenor"), L("pan_roll", -8)],
  release=dr(0.6), reverb=0.3)
P("STEEL PAN", "RE SO", "Island Pan Echo", "Tenor pan with a dotted echo, for laid-back reggae melodies.",
  ["pan_tenor"],
  delay=0.3, delay_time="1/8.", delay_fb=0.4, release=dr(0.6), reverb=0.3)
P("STEEL PAN", "AM", "Pan Over Pads", "Double seconds over a warm pad in a big room: dreamy amapiano "
  "chords.", [L("pan_double_second"), L("island_pad", -12)],
  release=dr(0.8), reverb=0.4, rev_size=0.8)
P("STEEL PAN", "SO", "Calypso Pan", "A brighter tenor pan for fast calypso runs.", ["pan_tenor"],
  bright=bright(3), release=dr(0.5), reverb=0.2)
P("STEEL PAN", "HA", "Tiki Pan", "Tenor pan with vibes in a big room: exotica in the tiki bar.",
  [L("pan_tenor"), L("vibraphone", -8)],
  release=dr(0.8), reverb=0.4, rev_size=0.75)
P("STEEL PAN", "AF", "Afro Pan Melody", "Tenor pan doubled with kalimba, for bright afro-fusion hooks.",
  [L("pan_tenor"), L("kalimba", -8)],
  release=dr(0.6), reverb=0.25)

# =============================================================== MALLETS
P("MALLETS", "AF", "Afro Marimba", "A warm marimba for interlocking afro patterns.", ["marimba"],
  release=dr(0.4), reverb=0.22)
P("MALLETS", "AF", "Balafon Griot", "The West African balafon: woody, buzzing, alive.", ["balafon"],
  release=dr(0.3), reverb=0.2)
P("MALLETS", "AF", "Balafon & Marimba", "Balafon with marimba underneath, a rounder, fuller wooden sound.",
  [L("balafon"), L("marimba", -6)],
  release=dr(0.35), reverb=0.22)
P("MALLETS", "AM", "Amapiano Marimba", "Marimba with a dotted echo and room, the plucky amapiano mallet line.",
  ["marimba"],
  delay=0.25, delay_time="1/8.", delay_fb=0.35, release=dr(0.4), reverb=0.3)
P("MALLETS", "AM HA", "Kalimba Dream", "Kalimba floating in echo and a long room.", ["kalimba"],
  delay=0.3, delay_time="1/4T", delay_fb=0.4, release=dr(0.5), reverb=0.4, rev_size=0.8)
P("MALLETS", "AF", "Mbira Spirit", "Zimbabwean mbira with its natural buzz, in a soft room.", ["mbira"],
  release=dr(0.6), reverb=0.3)
P("MALLETS", "HA", "Vibes Lounge", "Vibraphone with the motor on, for lounge chords and exotica.",
  ["vibraphone"],
  lfo_rate=lfo(5.0), lfo_depth=0.3, release=dr(0.9), reverb=0.35)
P("MALLETS", "HA", "Exotica Vibes", "Vibraphone and marimba together, bright and round.",
  [L("vibraphone"), L("marimba", -8)],
  lfo_rate=lfo(4.5), lfo_depth=0.15, release=dr(0.8), reverb=0.35)
P("MALLETS", "KO", "Kompa Vibes", "Vibraphone with chorus, for smooth kompa intros.", ["vibraphone"],
  chorus=0.2, release=dr(0.7), reverb=0.28)
P("MALLETS", "RE", "Reggae Mallets", "Short marimba with a quarter-note echo, for dub melodies.", ["marimba"],
  decay=dr(0.3), sustain=0.0, release=dr(0.2), delay=0.3, delay_time="1/4", delay_fb=0.45, reverb=0.25)
P("MALLETS", "SO", "Soca Marimba Bell", "Bright marimba with kalimba on top, a ringing bell melody.",
  [L("marimba"), L("kalimba", -6)],
  bright=bright(4), release=dr(0.4), reverb=0.22)
P("MALLETS", "AF", "Thumb Piano Duo", "Kalimba and mbira together, a shimmering cloud of tines.",
  [L("kalimba"), L("mbira", -4)],
  release=dr(0.5), reverb=0.3)

# =============================================================== BASS
P("BASS", "AM", "Log Drum Classic", "The amapiano log drum: a pitched, sliding thud. Program the bass line on "
  "it.", ["logdrum_classic"],
  release=dr(0.25), reverb=0.0)
P("BASS", "AM", "Log Drum Deep", "A deeper, longer log drum with more sub.", ["logdrum_deep"],
  release=dr(0.3), reverb=0.0)
P("BASS", "AM", "Log Drum Knock", "A short, knocking log drum that punches through the mix.", ["logdrum_knock"],
  release=dr(0.15), reverb=0.0)
P("BASS", "AM", "Log Drum Talking", "A log drum that bends like a talking drum.", ["logdrum_talking"],
  release=dr(0.25), reverb=0.0)
P("BASS", "AM", "Log Drum Gritty", "A distorted, gritty log drum for harder grooves.", ["logdrum_gritty"],
  drive=0.2, release=dr(0.2), reverb=0.0)
P("BASS", "AM", "Log Drum & Sub", "Classic log drum with a pure sub bass under it, for big systems.",
  [L("logdrum_classic"), L("sub_bass", -6)],
  release=dr(0.2), reverb=0.0)
P("BASS", "KO", "Kompa Bass", "Round finger bass for kompa's bouncing bass lines.", ["finger_bass"],
  cutoff=cutoff(2500), release=dr(0.12), reverb=0.0)
P("BASS", "AF", "Afrobeat Finger Bass", "Punchy finger bass for repeating afrobeat riffs.", ["finger_bass"],
  bright=bright(2), release=dr(0.1), reverb=0.0)
P("BASS", "AF", "Highlife Bass", "Flatwound bass, warm and thumpy, for highlife walking lines.", ["flat_bass"],
  release=dr(0.12), reverb=0.05)
P("BASS", "RE", "Reggae Bass", "A deep, round flatwound bass with the top rolled off: the one-drop bass.",
  ["flat_bass"],
  cutoff=cutoff(900), release=dr(0.12), reverb=0.0)
P("BASS", "RE", "Dub Sub", "Sub bass with flatwound bass for definition, dark and heavy.",
  [L("sub_bass"), L("flat_bass", -6)],
  cutoff=cutoff(650), release=dr(0.1), reverb=0.0)
P("BASS", "SO", "Soca Bass", "Short finger bass with a sub under it, for tight soca bass lines.",
  [L("finger_bass_short"), L("sub_bass", -8)],
  release=dr(0.08), reverb=0.0)
P("BASS", "SO", "Power Soca Sub", "A driven sub bass with a little resonance, for power soca drops.",
  ["sub_bass"],
  drive=0.3, cutoff=cutoff(1200), resonance=0.2, release=dr(0.08), reverb=0.0)
P("BASS", "RE", "Lovers Rock Bass", "Warm finger bass with a soft top, for smooth lovers rock.", ["finger_bass"],
  cutoff=cutoff(1400), release=dr(0.15), reverb=0.0)
P("BASS", "HA", "Island Flatwound", "A gentle flatwound bass for island ballads.", ["flat_bass"],
  cutoff=cutoff(1800), release=dr(0.15), reverb=0.08)
P("BASS", "AM", "Amapiano Sub Glide", "A mono sub bass that glides between notes. Overlap notes to slide.",
  ["sub_bass"],
  voice_mode="Mono", glide=glide(0.12), release=dr(0.1), reverb=0.0)

# =============================================================== PERCUSSION
P("PERCUSSION", "SO KO RE", "Island Percussion", "Congas, bongos, shakers, cabasa, agogo, cowbells, claves, "
  "guiro, slit drum and frame drums from C2.", ["island_perc"],
  release=dr(0.3), reverb=0.15)
P("PERCUSSION", "KO", "Kompa Percussion", "The island kit from C2, with timbales from C6 (open, rim, muted and "
  "shell on both drums).", [L("island_perc"), L("timbales", -1, 0, 3)],
  release=dr(0.3), reverb=0.15)
P("PERCUSSION", "AF", "West African Drums", "Bobobo bass, tenor and treble drums from C2, cajon slaps from C3.",
  ["west_africa"],
  release=dr(0.3), reverb=0.15)
P("PERCUSSION", "AF", "Afrobeat Percussion", "West African drums from C2 with the island kit (shakers, bells, "
  "congas) from C4.", [L("west_africa"), L("island_perc", -2, 0, 2)],
  release=dr(0.3), reverb=0.15)
P("PERCUSSION", "KO SO", "Timbales", "Modeled timbales from C2: open, rim and muted hits on both drums, plus "
  "the shells.", ["timbales"],
  release=dr(0.3), reverb=0.18)
P("PERCUSSION", "HA", "Ipu & Hula Perc", "Hawaiian ipu gourd (heel, tip, slap) at C2, with the island kit from "
  "C3.", [L("ipu"), L("island_perc", -3, 0, 1)],
  release=dr(0.3), reverb=0.18)
P("PERCUSSION", "AM", "Amapiano Perc Echo", "The island kit through a dotted echo: shakers and congas that "
  "ripple. From C2.", ["island_perc"],
  delay=0.22, delay_time="1/8.", delay_fb=0.35, release=dr(0.3), reverb=0.25)
P("PERCUSSION", "RE", "Dub Percussion", "The island kit in a long echo and a big room, for dub fills. From C2.",
  ["island_perc"],
  delay=0.32, delay_time="1/4.", delay_fb=0.5, delay_tone=0.4, release=dr(0.3), reverb=0.38, rev_size=0.8)

# =============================================================== SYNTHS & FX
P("SYNTHS & FX", "SO", "Soca Lead", "The big detuned soca lead that leads the road. Play the riff high.",
  ["soca_lead"],
  release=dr(0.2), reverb=0.2, delay=0.12, delay_time="1/8")
P("SYNTHS & FX", "SO", "Power Soca Brass", "Bright synth brass stabs for power soca hooks.", ["soca_brass"],
  release=dr(0.15), reverb=0.2)
P("SYNTHS & FX", "SO", "Soca Saw Stack", "Soca lead and synth brass stacked: the widest, loudest lead in the "
  "box.", [L("soca_lead"), L("soca_brass", -4)],
  chorus=0.2, release=dr(0.2), reverb=0.22)
P("SYNTHS & FX", "AF", "Afro Pluck", "A soft, round synth pluck for afrobeats chords and melodies.",
  ["afro_pluck"],
  release=dr(0.3), reverb=0.25)
P("SYNTHS & FX", "AF", "Afro Pluck Echo", "The afro pluck in a dotted echo, for rippling, bouncing melodies.",
  ["afro_pluck"],
  delay=0.35, delay_time="1/8.", delay_fb=0.45, release=dr(0.3), reverb=0.3)
P("SYNTHS & FX", "AM", "Amapiano Piano Pluck", "A pianoey synth pluck, the bright chord stab of amapiano.",
  ["piano_pluck"],
  release=dr(0.3), reverb=0.28)
P("SYNTHS & FX", "AM", "Yanos Pluck Echo", "The piano pluck with a triplet echo and a long room, for spacey "
  "amapiano hooks.", ["piano_pluck"],
  delay=0.35, delay_time="1/4T", delay_fb=0.45, release=dr(0.35), reverb=0.4, rev_size=0.75)
P("SYNTHS & FX", "HA", "Island Pad", "A warm, slow pad, wide and soft.", ["island_pad"],
  attack=attack(0.3), release=dr(1.2), chorus=0.2, reverb=0.35)
P("SYNTHS & FX", "AM", "Sunset Pad", "A darker pad with chorus and a long room, for deep amapiano.",
  ["island_pad"],
  cutoff=cutoff(3000), attack=attack(0.4), release=dr(1.4), chorus=0.3, reverb=0.45, rev_size=0.8)
P("SYNTHS & FX", "AF", "Afro Pad & Pluck", "A pluck on top of a slow pad, chords that strike and bloom.",
  [L("afro_pluck"), L("island_pad", -8)],
  release=dr(0.7), reverb=0.3)
P("SYNTHS & FX", "SO", "Soca Pluck", "A bright pluck with a steel pan glint on top.",
  [L("afro_pluck"), L("pan_tenor", -10)],
  bright=bright(3), release=dr(0.3), reverb=0.22)
P("SYNTHS & FX", "RE", "Reggae Synth Lead", "A softened lead with vibrato and echo, for dancehall and reggae "
  "melodies.", ["soca_lead"],
  cutoff=cutoff(2500), vibrato=vib(15), delay=0.3, delay_time="1/8.", release=dr(0.2), reverb=0.25)
P("SYNTHS & FX", "RE", "Dancehall Brass Synth", "Driven synth brass for dancehall stabs.", ["soca_brass"],
  drive=0.22, release=dr(0.12), reverb=0.15)
P("SYNTHS & FX", "KO", "Kompa Synth Lead", "A singing mono synth lead with glide and vibrato, for kompa "
  "melodies.", ["soca_lead"],
  voice_mode="Legato", glide=glide(0.1), vibrato=vib(20), cutoff=cutoff(5000), release=dr(0.2), reverb=0.25)
P("SYNTHS & FX", "KO", "Kompa Synth Brass", "Synth brass with a real trumpet blended in, the modern kompa "
  "horn sound.", [L("soca_brass"), L("trumpet", -10)],
  release=dr(0.18), reverb=0.22)
P("SYNTHS & FX", "AM", "Piano Whistle Lead", "A soft, whistly lead that slides and wobbles, with a long echo. "
  "Play it high.", ["soca_lead"],
  voice_mode="Legato", glide=glide(0.15), vibrato=vib(28), cutoff=cutoff(2200), delay=0.3, delay_time="1/4T",
  release=dr(0.3), reverb=0.4)
P("SYNTHS & FX", "HA", "Hula Breeze Pad", "A slow pad with pedal steel swelling inside it.",
  [L("island_pad"), L("pedal_steel", -10)],
  attack=attack(0.4), release=dr(1.2), reverb=0.4, rev_size=0.75)

assert len(PRESETS) == 128, len(PRESETS)
_order = {t: i for i, t in enumerate(TYPES)}
assert [p["type"] for p in PRESETS] == sorted((p["type"] for p in PRESETS), key=_order.get), "keep type order"
assert len({p["name"] for p in PRESETS}) == len(PRESETS), "duplicate preset names"


def desc_lines(desc, width_px=650, size_px=21):
    """Split a description into the LAYERS view's two lines, measured in the font MPC draws them in."""
    from PIL import ImageFont
    font = os.path.join(os.environ.get("MPC_VST", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))), "..", "mpc-vst-plugins")), "tools", "html_art", "fonts", "TitilliumWeb-Regular.ttf")
    f = ImageFont.truetype(font, size_px)
    words = desc.split()
    if f.getlength(desc) <= width_px:
        return [desc, ""]
    best = None
    for k in range(1, len(words)):                       # the break that makes the longer line shortest
        a, b = " ".join(words[:k]), " ".join(words[k:])
        w = max(f.getlength(a), f.getlength(b))
        if f.getlength(a) <= width_px and f.getlength(b) <= width_px and (best is None or w < best[0]):
            best = (w, a, b)
    assert best, ("description too long", desc)
    return [best[1], best[2]]


def write_header(params, path):
    import tropix_params as tp
    keys = [p["key"] for p in params if p.get("preset")]
    opts = {p["key"]: p["options"] for p in params if p["kind"] == "option"}
    rows = []
    for pr in PRESETS:
        v = pr["values"]
        vals = []
        for k in keys:
            x = v[k]
            if isinstance(x, str):
                x = opts[k].index(x)
            vals.append(tp.cf(x))
        rows.append("    { " + ", ".join(vals) + " },  /* %s */" % pr["name"])
    d = [desc_lines(p["desc"]) for p in PRESETS]
    masks = [sum(1 << GENRES.index(g) for g in p["genres"]) for p in PRESETS]
    L = ["/* Generated by tools/tropix_params.py from tools/presets.py: the factory presets. */",
         "#define NPRESET %d" % len(PRESETS),
         "#define NPRESET_KEYS %d" % len(keys),
         "static const char *const PRESET_KEYS[NPRESET_KEYS] = { " + ", ".join(tp.c_str(k) for k in keys) + " };",
         "static const char *const PRESET_NAME[NPRESET] = {\n" + "".join("    %s,\n" % tp.c_str(p["name"]) for p in PRESETS) + "};",
         "static const char *const PRESET_DESC1[NPRESET] = {\n" + "".join("    %s,\n" % tp.c_str(a) for a, _ in d) + "};",
         "static const char *const PRESET_DESC2[NPRESET] = {\n" + "".join("    %s,\n" % tp.c_str(b) for _, b in d) + "};",
         "static const unsigned char PRESET_TYPE[NPRESET] = { " + ", ".join(str(TYPES.index(p["type"])) for p in PRESETS) + " };",
         "static const unsigned char PRESET_GENRE[NPRESET] = { " + ", ".join(str(GENRES.index(p["genres"][0])) for p in PRESETS) + " };",
         "static const unsigned char PRESET_GMASK[NPRESET] = { " + ", ".join(str(m) for m in masks) + " };",
         "static const float PRESET_VAL[NPRESET][NPRESET_KEYS] = {\n" + "\n".join(rows) + "\n};"]
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
