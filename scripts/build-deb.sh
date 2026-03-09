#!/usr/bin/env bash

set -eu

SOURCE_DIR=$(dirname "$(readlink -f "$0")")
REPO_ROOT=$(dirname "$SOURCE_DIR")
version=$(cat "$SOURCE_DIR/VERSION")

PKG_ROOT=${PKG_ROOT:-/tmp/solace-browser-pkg}
OUTPUT_DIR=${OUTPUT_DIR:-$REPO_ROOT/dist}
OUTPUT_DEB=${OUTPUT_DEB:-$OUTPUT_DIR/solace-browser_${version}_amd64.deb}

BROWSER_BINARY=${BROWSER_BINARY:-$REPO_ROOT/dist/solace-browser-linux-x86_64}
SERVER_SCRIPT=${SERVER_SCRIPT:-$REPO_ROOT/yinyang-server.py}
LAUNCH_SCRIPT=${LAUNCH_SCRIPT:-$SOURCE_DIR/launch-yinyang.sh}
SERVICE_FILE=${SERVICE_FILE:-$SOURCE_DIR/yinyang.service}
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

require_file "$BROWSER_BINARY"
require_file "$SERVER_SCRIPT"
require_file "$LAUNCH_SCRIPT"
require_file "$SERVICE_FILE"
require_file "$DESKTOP_FILE"

rm -rf "$PKG_ROOT"
mkdir -p \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/lib/solace-browser" \
  "$PKG_ROOT/usr/lib/systemd/user" \
  "$PKG_ROOT/usr/share/applications"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: solace-browser
Version: ${version}
Section: web
Priority: optional
Architecture: amd64
Depends: python3 (>=3.10), libgtk-3-0, libx11-xcb1
Maintainer: Solace AI <hello@solaceagi.com>
Description: AI-Native browser with Yinyang sidebar
 AI-Native browser with Yinyang sidebar.
EOF

install -m 755 "$BROWSER_BINARY" "$PKG_ROOT/usr/bin/solace-browser"
install -m 755 "$SERVER_SCRIPT" "$PKG_ROOT/usr/lib/solace-browser/yinyang-server.py"

sed '2i\
SOLACE_REPO_ROOT=${SOLACE_REPO_ROOT:-/usr/lib/solace-browser}
' "$LAUNCH_SCRIPT" > "$PKG_ROOT/usr/lib/solace-browser/launch-yinyang.sh"
chmod 755 "$PKG_ROOT/usr/lib/solace-browser/launch-yinyang.sh"

sed 's#ExecStart=/bin/sh %h/.local/lib/solace/launch-yinyang.sh#ExecStart=/bin/sh /usr/lib/solace-browser/launch-yinyang.sh#' \
  "$SERVICE_FILE" > "$PKG_ROOT/usr/lib/systemd/user/yinyang.service"
chmod 644 "$PKG_ROOT/usr/lib/systemd/user/yinyang.service"

install -m 644 "$DESKTOP_FILE" "$PKG_ROOT/usr/share/applications/solace-browser.desktop"

mkdir -p "$OUTPUT_DIR"
dpkg-deb --build "$PKG_ROOT" "$OUTPUT_DEB"

sha256sum "$OUTPUT_DEB" > "${OUTPUT_DEB}.sha256"

echo "$OUTPUT_DEB"
echo "${OUTPUT_DEB}.sha256"
