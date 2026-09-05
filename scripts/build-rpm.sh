#!/usr/bin/env bash
# Build the OpenGonsult RPM locally with rpmbuild.
#
# Produces a real PEP 517 sdist (so the tarball carries packaging/ and
# icons/ via MANIFEST.in), then runs rpmbuild against the packaged spec.
#
# Usage: scripts/build-rpm.sh [output_dir]   (default: releases/)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(grep -m1 '__version__' "$REPO_ROOT/gui/__init__.py" \
    | sed -E "s/.*=\\s*[\"']([^\"']+)[\"'].*/\\1/")"
OUT="${1:-$REPO_ROOT/releases}"
WORK="$(mktemp -d /tmp/opengonsult-rpm.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

# 1. Build the sdist, falling back to a scratch venv when the 'build' module
#    is not importable on this host.
mkdir -p "$WORK/sdist"
if python3 -m build --help >/dev/null 2>&1; then
    python3 -m build --sdist --outdir "$WORK/sdist" "$REPO_ROOT" >/dev/null
else
    python3 -m venv "$WORK/venv"
    "$WORK/venv/bin/pip" -q install build
    "$WORK/venv/bin/python" -m build --sdist --outdir "$WORK/sdist" "$REPO_ROOT" >/dev/null
fi

# 2. rpmbuild tree and build.
RPMTOPDIR="$WORK/rpmbuild"
mkdir -p "$RPMTOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
cp "$WORK"/sdist/*.tar.gz "$RPMTOPDIR/SOURCES/"
cp "$REPO_ROOT/packaging/rpm/opengonsult.spec" "$RPMTOPDIR/SPECS/"

rpmbuild -bb \
    --define "_topdir $RPMTOPDIR" \
    "$RPMTOPDIR/SPECS/opengonsult.spec" >/dev/null

mkdir -p "$OUT"
cp "$RPMTOPDIR"/RPMS/noarch/opengonsult-${VERSION}-1.noarch.rpm "$OUT/"
echo "Built: $OUT/opengonsult-${VERSION}-1.noarch.rpm"