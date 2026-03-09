#!/bin/sh
# install-chromium.sh — One-shot installer for Solace Browser v1.2.0 (Chromium Edition)
# Auth: 65537 | Port 8888 ONLY | No extensions | No port 9222
# Usage: curl -sSL https://github.com/phuctruong/solace-browser/releases/download/v1.2.0/install-chromium.sh | sh

set -eu

RELEASE="v1.2.0"
REPO="phuctruong/solace-browser"
INSTALL_DIR="${HOME}/.local/lib/solace-browser"
BIN_DIR="${HOME}/.local/bin"
TARBALL="solace-browser-chromium-linux-x86_64.tar.gz"
BASE_URL="https://github.com/${REPO}/releases/download/${RELEASE}"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found (install it and retry)"
}

echo "=== Solace Browser ${RELEASE} Installer ==="
echo "Install dir: ${INSTALL_DIR}"
echo ""

require_cmd curl
require_cmd tar
require_cmd python3

# Create directories
mkdir -p "${INSTALL_DIR}" "${BIN_DIR}"

# Download and verify tarball
echo "[1/4] Downloading Chromium build..."
curl -sSL --progress-bar "${BASE_URL}/${TARBALL}" -o "/tmp/${TARBALL}"
curl -sSL "${BASE_URL}/${TARBALL}.sha256" -o "/tmp/${TARBALL}.sha256"

echo "[2/4] Verifying checksum..."
EXPECTED=$(awk '{print $1}' "/tmp/${TARBALL}.sha256")
ACTUAL=$(sha256sum "/tmp/${TARBALL}" | awk '{print $1}')
if [ "${EXPECTED}" != "${ACTUAL}" ]; then
  fail "Checksum mismatch. Expected: ${EXPECTED} Got: ${ACTUAL}"
fi
echo "    Checksum OK (sha256: ${ACTUAL})"

# Extract
echo "[3/4] Extracting to ${INSTALL_DIR}..."
tar -xzf "/tmp/${TARBALL}" -C "${INSTALL_DIR}" --strip-components=1
rm -f "/tmp/${TARBALL}" "/tmp/${TARBALL}.sha256"

# Download Yinyang Server (pure Python, no pip needed)
curl -sSL "${BASE_URL}/yinyang_server.py" -o "${INSTALL_DIR}/yinyang_server.py"
curl -sSL "${BASE_URL}/yinyang-server.py" -o "${INSTALL_DIR}/yinyang-server.py"
chmod +x "${INSTALL_DIR}/chrome"

# Create launcher
cat > "${BIN_DIR}/solace-browser" << 'LAUNCHER'
#!/bin/sh
# Solace Browser launcher — starts Yinyang Server then Chrome
INSTALL_DIR="${HOME}/.local/lib/solace-browser"

# Start Yinyang Server in background (port 8888)
if ! curl -sf http://localhost:8888/api/v1/system/status >/dev/null 2>&1; then
  python3 "${INSTALL_DIR}/yinyang-server.py" &
  YINYANG_PID=$!
  sleep 1
  echo "Yinyang Server started (PID ${YINYANG_PID})"
fi

# Launch Solace Browser
exec "${INSTALL_DIR}/chrome" \
  --user-data-dir="${HOME}/.config/solace-browser" \
  "$@"
LAUNCHER
chmod +x "${BIN_DIR}/solace-browser"

echo "[4/4] Creating desktop entry..."
mkdir -p "${HOME}/.local/share/applications"
cat > "${HOME}/.local/share/applications/solace-browser.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Name=Solace Browser
Comment=AI Browser with Yinyang Sidebar — Local-First, Evidence-Proven
Exec=${BIN_DIR}/solace-browser %U
Icon=${INSTALL_DIR}/resources/accessibility/solace.png
Terminal=false
Type=Application
Categories=Network;WebBrowser;
MimeType=x-scheme-handler/http;x-scheme-handler/https;
DESKTOP

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Launch: ${BIN_DIR}/solace-browser"
echo "  (or search 'Solace Browser' in your app launcher)"
echo ""
echo "Yinyang sidebar: Click the panel icon in browser toolbar → select Yinyang"
echo "Yinyang Server:  ws://localhost:8888/ws/yinyang (starts automatically)"
echo ""
echo "Onboard at: https://solaceagi.com/register"
echo "Auth: 65537 | FSL-1.1-Apache-2.0"
