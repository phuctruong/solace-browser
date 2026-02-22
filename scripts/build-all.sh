#!/bin/bash
# Solace Browser — Cross-Platform Build Orchestrator
# Runs all three platform build scripts sequentially
# Produces: dist/ with macOS DMG, Linux .deb/.AppImage, Windows MSI + checksums

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------
if [ -f "$PROJECT_ROOT/VERSION" ]; then
    VERSION="$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')"
elif command -v python3 >/dev/null 2>&1 && [ -f "$PROJECT_ROOT/package.json" ]; then
    VERSION="$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/package.json')); print(d['version'])")"
else
    VERSION="1.0.0"
fi

echo "Solace Browser — Cross-Platform Build All"
echo "Version: v${VERSION}"
echo "=========================================="

DIST_DIR="$PROJECT_ROOT/dist"
mkdir -p "$DIST_DIR"

ERRORS=0

# ---------------------------------------------------------------------------
# Run each platform build
# ---------------------------------------------------------------------------

echo ""
echo ">>> Building macOS..."
if bash "$SCRIPT_DIR/build-mac.sh"; then
    echo "macOS build: DONE"
else
    echo "macOS build: FAILED (continuing)"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo ">>> Building Linux..."
if bash "$SCRIPT_DIR/build-linux.sh"; then
    echo "Linux build: DONE"
else
    echo "Linux build: FAILED (continuing)"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo ">>> Building Windows..."
if bash "$SCRIPT_DIR/build-windows.sh"; then
    echo "Windows build: DONE"
else
    echo "Windows build: FAILED (continuing)"
    ERRORS=$((ERRORS + 1))
fi

# ---------------------------------------------------------------------------
# Combine checksums into single manifest
# ---------------------------------------------------------------------------
echo ""
echo "Combining checksums into SHA256SUMS.txt..."

COMBINED="$DIST_DIR/SHA256SUMS.txt"
> "$COMBINED"

for PLATFORM_CHECKSUM in \
    "$DIST_DIR/SHA256SUMS-mac.txt" \
    "$DIST_DIR/SHA256SUMS-linux.txt" \
    "$DIST_DIR/SHA256SUMS-windows.txt"
do
    if [ -f "$PLATFORM_CHECKSUM" ]; then
        cat "$PLATFORM_CHECKSUM" >> "$COMBINED"
    fi
done

echo "Combined checksums:"
cat "$COMBINED" 2>/dev/null || echo "  (empty)"

# ---------------------------------------------------------------------------
# Build manifest JSON
# ---------------------------------------------------------------------------
echo ""
echo "Writing build manifest..."

MANIFEST="$DIST_DIR/manifest.json"
BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

python3 - <<EOF
import json, os, hashlib
from pathlib import Path

dist_dir = Path("$DIST_DIR")
version = "$VERSION"
build_date = "$BUILD_DATE"

artifacts = []
for f in sorted(dist_dir.iterdir()):
    if f.suffix in (".dmg", ".deb", ".AppImage", ".msi"):
        sha256 = hashlib.sha256(f.read_bytes()).hexdigest()
        artifacts.append({
            "filename": f.name,
            "size": f.stat().st_size,
            "sha256": sha256,
        })

manifest = {
    "version": version,
    "build_date": build_date,
    "artifacts": artifacts,
}

with open("$MANIFEST", "w") as fh:
    json.dump(manifest, fh, indent=2)

print(f"  Manifest written: {len(artifacts)} artifacts")
EOF

echo ""
echo "=========================================="
echo "All builds complete — v${VERSION}"
echo "Errors: ${ERRORS}"
echo "Output: $DIST_DIR"
echo ""
ls -lh "$DIST_DIR" 2>/dev/null || true

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "WARNING: ${ERRORS} platform build(s) failed. Check output above."
    exit 1
fi
