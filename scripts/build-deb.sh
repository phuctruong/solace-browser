#!/usr/bin/env bash

set -eu

SOURCE_DIR=$(dirname "$(readlink -f "$0")")
REPO_ROOT=$(dirname "$SOURCE_DIR")
version=$(cat "$REPO_ROOT/VERSION")

PKG_ROOT=${PKG_ROOT:-/tmp/solace-browser-pkg}
OUTPUT_DIR=${OUTPUT_DIR:-$REPO_ROOT/dist}
OUTPUT_DEB=${OUTPUT_DEB:-$OUTPUT_DIR/solace-browser_${version}_amd64.deb}
BUNDLE_SCRIPT=${BUNDLE_SCRIPT:-$SOURCE_DIR/build-linux-release.sh}
BUNDLE_DIR=${BUNDLE_DIR:-$REPO_ROOT/dist/solace-browser-release}
DESKTOP_FILE=${DESKTOP_FILE:-$SOURCE_DIR/solace-browser.desktop}

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_file() {
  if [ ! -f "$1" ]; then
    fail "required file not found: $1"
  fi
}

if ! command -v dpkg-deb >/dev/null 2>&1; then
  fail "dpkg-deb not found"
fi

require_file "$BUNDLE_SCRIPT"
require_file "$DESKTOP_FILE"

rm -rf "$BUNDLE_DIR"
"$BUNDLE_SCRIPT" >/dev/null
require_file "$BUNDLE_DIR/chrome"
require_file "$BUNDLE_DIR/solace-hub"

rm -rf "$PKG_ROOT"
mkdir -p \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/lib/solace-browser" \
  "$PKG_ROOT/usr/share/applications"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: solace-browser
Version: ${version}
Section: web
Priority: optional
Architecture: amd64
Depends: python3 (>=3.10), libgtk-3-0, libx11-xcb1, libwebkit2gtk-4.0-37
Maintainer: Solace AI <hello@solaceagi.com>
Description: Solace Browser + Solace Hub portable runtime
 Solace Browser ships the real Chromium runtime together with Solace Hub.
 Hub starts first, owns localhost:8888, launches the Browser second, and
 keeps the Yinyang assistant local-first.
EOF

cp -a "$BUNDLE_DIR" "$PKG_ROOT/usr/lib/solace-browser/"

cat > "$PKG_ROOT/usr/bin/solace-browser" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /usr/lib/solace-browser/solace-browser-release/solace-hub "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/solace-browser"

cat > "$PKG_ROOT/usr/bin/solace-hub" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /usr/lib/solace-browser/solace-browser-release/solace-hub "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/solace-hub"

install -m 644 "$DESKTOP_FILE" "$PKG_ROOT/usr/share/applications/solace-browser.desktop"

mkdir -p "$OUTPUT_DIR"
dpkg-deb -Zgzip -z1 --build "$PKG_ROOT" "$OUTPUT_DEB"

sha256sum "$OUTPUT_DEB" > "${OUTPUT_DEB}.sha256"

echo "$OUTPUT_DEB"
echo "${OUTPUT_DEB}.sha256"
