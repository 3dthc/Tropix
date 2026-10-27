#!/usr/bin/env bash
# Build Tropix for MPC OS: the .so, skin and plugin-list entry (the instruments must already be packed in engine/).
#   vst/build.sh            (run from anywhere; needs Docker and python3)
# Expects a checkout of sd88me/mpc-vst-plugins next to this repo (override with MPC_VST=...).
# Output: vst/build/tropix.so, vst/build/skin/...
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
MPC_VST="${MPC_VST:-$REPO/../mpc-vst-plugins}"
[ -f "$MPC_VST/tools/build_port.sh" ] || { echo "mpc-vst-plugins not found at $MPC_VST (set MPC_VST=...)" >&2; exit 1; }

missing=""
for f in $(sed -n 's/^    "\([a-z0-9_]*\)",$/\1/p' "$REPO/src/instruments.h" | head -n "$(sed -n 's/#define NINST //p' "$REPO/src/instruments.h")"); do
  [ -f "$REPO/engine/$f.tpx" ] || missing="$missing $f.tpx"
done
if [ -n "$missing" ]; then
  echo "missing instrument files in $REPO/engine:$missing" >&2
  echo "(run install.sh, or: python3 tools/pack_tropix.py)" >&2
  exit 1
fi

bash "$MPC_VST/tools/build_port.sh" "$HERE/vst.json"
echo "built: $HERE/build/tropix.so  (+ $REPO/engine/ ships next to it)"
