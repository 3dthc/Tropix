#!/usr/bin/env bash
# The GitHub Actions build (.github/workflows/release.yml): packs the instruments from library/ (committed), builds
# the plugin and stamps the skin's version (as make_release.sh does).
#   VERSION=0.1.0 MPC_VST=../mpc-vst-plugins bash tools/ci_build.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if ! ls "$REPO"/engine/*.tpx >/dev/null 2>&1; then
  python3 -m pip install -q numpy soundfile
  python3 "$REPO/tools/pack_tropix.py"
fi
cp "$REPO/library/LICENSES.md" "$REPO/engine/LICENSES.md"
bash "$REPO/vst/build.sh"
B="$REPO/vst/build"
SKIN_VER="$(echo "${VERSION:?set VERSION}" | awk -F. '{printf "%d.%d.%d.0", $1, $2, $3}')"
sed -i "s|<version>[^<]*</version>|<version>$SKIN_VER</version>|" "$B/skin/3dthc - VST - Tropix/version.xml"
grep -q "<version>$SKIN_VER</version>" "$B/skin/3dthc - VST - Tropix/version.xml" || { echo "could not stamp the skin version" >&2; exit 1; }
