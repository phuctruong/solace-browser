#!/usr/bin/env bash
# build-deb.sh — Build a .deb package for Solace Browser
# Auth: 65537 | Port 9222: PERMANENTLY BANNED
#
# Prerequisites:
#   - dist/solace-browser-linux-x86_64 must exist (run release_browser_cycle.sh first)
#   - dpkg-deb installed (apt-get install dpkg)
#
# Output:
#   dist/solace-browser_1.0.0_amd64.deb
#   dist/solace-browser_1.0.0_amd64.deb.sha256

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${REPO_ROOT}/VERSION")"
BINARY="${REPO_ROOT}/dist/solace-browser-linux-x86_64"
DEB_NAME="solace-browser_${VERSION}_amd64"
PKG_DIR="${REPO_ROOT}/scratch/deb-build/${DEB_NAME}"
DIST_DIR="${REPO_ROOT}/dist"

echo "=== Building .deb: ${DEB_NAME} ==="

if [ ! -f "${BINARY}" ]; then
  echo "ERROR: Binary not found: ${BINARY}" >&2
  echo "Run: TARGET_OS=linux bash scripts/release_browser_cycle.sh" >&2
  exit 1
fi

if ! command -v dpkg-deb &>/dev/null; then
  echo "ERROR: dpkg-deb not found. Install with: sudo apt-get install dpkg" >&2
  exit 1
fi

# --- Build directory structure ---
rm -rf "${PKG_DIR}"
install -d "${PKG_DIR}/DEBIAN"
install -d "${PKG_DIR}/usr/bin"
install -d "${PKG_DIR}/usr/share/doc/solace-browser"
install -d "${PKG_DIR}/usr/share/applications"

# --- Control file (inject version) ---
sed "s/^Version: .*/Version: ${VERSION}/" \
  "${REPO_ROOT}/scripts/debian/control" \
  > "${PKG_DIR}/DEBIAN/control"

# --- postinst ---
install -m 755 "${REPO_ROOT}/scripts/debian/postinst" "${PKG_DIR}/DEBIAN/postinst"

# --- Binary ---
install -m 755 "${BINARY}" "${PKG_DIR}/usr/bin/solace-browser"

# --- .desktop file ---
cat > "${PKG_DIR}/usr/share/applications/solace-browser.desktop" <<DESKTOP
[Desktop Entry]
Name=Solace Browser
Comment=AI automation backend for Solace Browser
Exec=solace-browser --head
Icon=solace-browser
Terminal=false
Type=Application
Categories=Network;WebBrowser;
DESKTOP

# --- Copyright ---
cat > "${PKG_DIR}/usr/share/doc/solace-browser/copyright" <<COPYRIGHT
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: solace-browser
Upstream-Contact: hello@solaceagi.com
Source: https://solaceagi.com

Files: *
Copyright: $(date +%Y) Solace AI
License: FSL-1.1
 Functional Source License, Version 1.1
 See LICENSE file for full text.
COPYRIGHT

# --- Build .deb ---
DEB_OUT="${DIST_DIR}/${DEB_NAME}.deb"
dpkg-deb --build --root-owner-group "${PKG_DIR}" "${DEB_OUT}"

# --- SHA256 ---
SHA=$(python3 -c "
import hashlib
from pathlib import Path
p = Path('${DEB_OUT}')
print(hashlib.sha256(p.read_bytes()).hexdigest())
")
echo "${SHA}  ${DEB_NAME}.deb" > "${DEB_OUT}.sha256"

SIZE=$(stat -c%s "${DEB_OUT}")
echo ""
echo "=== .deb build complete ==="
echo "Output:  ${DEB_OUT}"
echo "SHA256:  ${SHA}"
echo "Size:    ${SIZE} bytes ($(python3 -c "print(round(${SIZE}/1024/1024, 2))")  MB)"
