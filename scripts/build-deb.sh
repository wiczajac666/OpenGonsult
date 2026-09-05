#!/usr/bin/env bash
# Build the OpenGonsult .deb from the debian-build staging tree.
#
# Deterministic, self-contained: re-syncs live modules (so the .deb never
# ships drift or .pyc), refreshes Installed-Size, and packs with
# --root-owner-group for reproducible ownership.
#
# Usage: scripts/build-deb.sh [output_dir]   (default: releases/)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$REPO_ROOT/debian-build"
OUT="${1:-$REPO_ROOT/releases}"

# 1. Sync live modules into the staging tree. Nothing ships .pyc.
for m in ecu gui protocol serial graphs dashboard sessionrec; do
    cp -r "$REPO_ROOT/$m"/* "$STAGE/usr/share/opengonsult/$m/" 2>/dev/null || true
done
find "$STAGE" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
find "$STAGE" -name "*.pyc" -delete

# 2. Refresh Installed-Size (KiB of installed files, excluding DEBIAN/).
SIZE="$(find "$STAGE" -path "$STAGE/DEBIAN" -prune -o -type f -printf '%s\n' \
    | awk '{s+=$1} END{print int((s + 1023) / 1024)}')"
sed -i "s/^Installed-Size: .*/Installed-Size: $SIZE/" "$STAGE/DEBIAN/control"

# 3. Pack. Output name follows OpenGonsult_<version>_all.deb.
VERSION="$(sed -n 's/^Version: //p' "$STAGE/DEBIAN/control" | head -1)"
mkdir -p "$OUT"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT/OpenGonsult_${VERSION}_all.deb"
echo "Built: $OUT/OpenGonsult_${VERSION}_all.deb"