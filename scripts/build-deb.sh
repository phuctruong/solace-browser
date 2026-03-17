#!/usr/bin/env bash
# Diagram: 29-chromium-build-pipeline

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
require_file "$BUNDLE_DIR/solace"
require_file "$BUNDLE_DIR/solace-hub"

rm -rf "$PKG_ROOT"
mkdir -p \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/lib/solace-browser" \
  "$PKG_ROOT/usr/share/applications" \
  "$PKG_ROOT/usr/share/metainfo" \
  "$PKG_ROOT/usr/share/pixmaps"

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

# Install Hub desktop file + icons
HUB_DESKTOP="${SOURCE_DIR}/solace-hub.desktop"
if [ -f "$HUB_DESKTOP" ]; then
  install -m 644 "$HUB_DESKTOP" "$PKG_ROOT/usr/share/applications/solace-hub.desktop"
fi
mkdir -p "$PKG_ROOT/usr/share/icons/hicolor/128x128/apps"
for icon_pair in "solace-hub-icon-128.png:solace-hub.png" "solace-browser-icon-128.png:solace-browser.png"; do
  src="${icon_pair%%:*}"
  dst="${icon_pair##*:}"
  if [ -f "$BUNDLE_DIR/$src" ]; then
    install -m 644 "$BUNDLE_DIR/$src" "$PKG_ROOT/usr/share/icons/hicolor/128x128/apps/$dst"
  fi
done

# AppStream metadata + pixmap icon (for software center display)
APPDATA="${SOURCE_DIR}/com.solaceagi.hub.appdata.xml"
if [ -f "$APPDATA" ]; then
  install -m 644 "$APPDATA" "$PKG_ROOT/usr/share/metainfo/com.solaceagi.hub.appdata.xml"
fi
if [ -f "$BUNDLE_DIR/solace-hub-icon-128.png" ]; then
  install -m 644 "$BUNDLE_DIR/solace-hub-icon-128.png" "$PKG_ROOT/usr/share/pixmaps/solace-browser.png"
fi

mkdir -p "$OUTPUT_DIR"
dpkg-deb -Zgzip -z1 --build "$PKG_ROOT" "$OUTPUT_DEB"

sha256sum "$OUTPUT_DEB" > "${OUTPUT_DEB}.sha256"

echo "$OUTPUT_DEB"
echo "${OUTPUT_DEB}.sha256"
