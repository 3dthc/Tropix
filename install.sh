#!/usr/bin/env bash
# Tropix: one-step build, from a clone of this repo to a zip ready for the MPC.
#
#   bash ~/Tropix/install.sh
#
# What it does:
#   1. checks Docker is running and that mpc-vst-plugins is next to this folder (clones it if not)
#   2. packs the instruments into engine/ from library/ (first time only, a few minutes, in a Docker container)
#   3. builds the plugin and packages dist/Tropix-<version>-mpc-armv7.zip
#   4. copies that zip to your Windows Downloads, ready to put on the MPC
# Safe to run again: each step skips what is already done.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VERSION="0.1.0"
LIBRARY_VERSION="$(sed -n 's/^LIBRARY_VERSION = "\(.*\)".*/\1/p' "$HERE/tools/pack_tropix.py")"
MPC_VST="${MPC_VST:-$HERE/../mpc-vst-plugins}"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }
INSTRUMENTS="$(sed -n 's/^    "\([a-z0-9_]*\)",$/\1/p' "$HERE/src/instruments.h" | head -n "$(sed -n 's/#define NINST //p' "$HERE/src/instruments.h")")"

# ---- 1. tools
step "1/4  Checking tools"
command -v python3 >/dev/null || fail "python3 is missing:  sudo apt install python3"
command -v docker  >/dev/null || fail "Docker is not available in WSL. Start Docker Desktop (with WSL integration on) and run this again."
docker info >/dev/null 2>&1   || fail "Docker is not running. Start Docker Desktop, wait until it says running, then run this again."
echo "docker ok"
if [ ! -f "$MPC_VST/tools/build_port.sh" ]; then
  command -v git >/dev/null || fail "mpc-vst-plugins not found at $MPC_VST and git is missing (sudo apt install git)"
  echo "mpc-vst-plugins not found, cloning it to $MPC_VST"
  git clone --depth 1 https://github.com/sd88me/mpc-vst-plugins.git "$MPC_VST"
fi
echo "toolchain: $(cd "$MPC_VST" && pwd)"
export MPC_VST

# ---- 2. instruments
step "2/4  Instruments"
missing() { local m=""; for f in $INSTRUMENTS; do [ -f "$HERE/engine/$f.tpx" ] || m="$m $f"; done; echo "$m"; }
mkdir -p "$HERE/engine"
if [ "$(cat "$HERE/engine/LIBRARY_VERSION" 2>/dev/null)" != "$LIBRARY_VERSION" ]; then
  rm -f "$HERE"/engine/*.tpx "$HERE/engine/LIBRARY_VERSION"
fi
if [ -n "$(missing)" ]; then
  echo "packing the 65 instruments from library/ (first time only: a few minutes)"
  docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$HERE":/w -w /w python:3.11-slim sh -c \
    "pip install -q --no-warn-script-location --target /tmp/p numpy soundfile >/dev/null 2>&1 && PYTHONPATH=/tmp/p python3 tools/pack_tropix.py" \
    || fail "packing the instruments failed (see above)"
fi
m="$(missing)"
[ -z "$m" ] || fail "still missing in engine/:$m"
echo "all $(echo $INSTRUMENTS | wc -w) instrument files present ($(du -sh "$HERE/engine" | cut -f1))"

# ---- 3. build
step "3/4  Building Tropix (the first build can take a few minutes)"
rm -f "$HERE"/dist/Tropix-*-mpc-armv7.zip
bash "$HERE/make_release.sh" "$VERSION"
out="$HERE/dist/Tropix-$VERSION-mpc-armv7.zip"
[ -f "$out" ] || fail "build finished without $out"

# ---- 4. hand it over
step "4/4  Done"
copied=""
for d in /mnt/c/Users/*/Downloads; do
  [ -d "$d" ] && [ -w "$d" ] || continue
  rm -f "$d"/Tropix-*-mpc-armv7.zip          # older Tropix builds only, so the newest can't be mixed up with them
  cp "$out" "$d/" && { copied="$d/$(basename "$out")"; break; }
done
echo "MPC install zip: $out"
if [ -n "$copied" ]; then
  echo "also copied to Windows: $copied"
  echo "  (in Windows Explorer: Downloads\\$(basename "$out"))"
fi
echo
echo "Install it on the MPC the same way as your other plugins (see TESTING.md)."
