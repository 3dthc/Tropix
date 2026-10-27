#!/usr/bin/env bash
# One command from source to an installable MPC zip:
#   ./make_release.sh [version]        (default: the version below)
# Builds the plugin (vst/build.sh, Docker), then packages it with mpc-vst-plugins' release tool into
# dist/Tropix-<version>-mpc-armv7.zip, with the instruments (engine/*.tpx) next to the .so.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MPC_VST="${MPC_VST:-$HERE/../mpc-vst-plugins}"
VERSION="${1:-0.1.0}"
B="$HERE/vst/build"

bash "$HERE/vst/build.sh"
[ -f "$B/tropix.so" ] || { echo "build failed: no $B/tropix.so" >&2; exit 1; }

# The skin tools write version 1.0.0.0 into the skin's version.xml; stamp the real one so MPC sees each release as new
# and replaces its copy of the faceplate.
SKIN_VER="$(echo "$VERSION" | awk -F. '{printf "%d.%d.%d.0", $1, $2, $3}')"
sed -i "s|<version>[^<]*</version>|<version>$SKIN_VER</version>|" "$B/skin/3dthc - VST - Tropix/version.xml"
grep -q "<version>$SKIN_VER</version>" "$B/skin/3dthc - VST - Tropix/version.xml" || { echo "could not stamp the skin version" >&2; exit 1; }
cp "$HERE/library/LICENSES.md" "$HERE/engine/LICENSES.md"

python3 "$MPC_VST/tools/release.py" \
  --so "$B/tropix.so" \
  --skin "$B/skin/3dthc - VST - Tropix" \
  --entry "$B/pluginlist-entry.xml" \
  --version "$VERSION" \
  --repo 3dthc/Tropix --id tropix --license MIT \
  --extra "$HERE/engine:engine" \
  --about "Island and afro sounds: 128 presets and 65 instruments for afrobeat, amapiano, kompa, soca, reggae and Hawaiian music - steel pans, log drums, saxes and trumpets, kompa and slack-key guitars, steels, keys, mallets, basses and percussion. Two layers, glide, scoop, vibrato, filter, drive, chorus, delay, reverb, nine colorways." \
  -o "$HERE/dist"

echo
echo "Release zip:"
ls -la "$HERE/dist/"*.zip
