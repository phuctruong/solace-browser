#!/bin/sh
# Diagram: 29-chromium-build-pipeline
# install-chromium.sh — One-shot installer for the Solace Browser portable release
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
echo "[1/4] Downloading portable release..."
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
rm -rf "${INSTALL_DIR}/solace-browser-release"
tar -xzf "/tmp/${TARBALL}" -C "${INSTALL_DIR}"
rm -f "/tmp/${TARBALL}" "/tmp/${TARBALL}.sha256"

# Create launcher
cat > "${BIN_DIR}/solace-browser" << 'LAUNCHER'
#!/bin/sh
# Solace Browser launcher — Hub first, Browser second
INSTALL_DIR="${HOME}/.local/lib/solace-browser/solace-browser-release"
clean_ld_library_path=""
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
  old_ifs="$IFS"
  IFS=':'
  for entry in ${LD_LIBRARY_PATH}; do
    if [ -n "${entry}" ] && [ "${entry#"/snap/"}" = "${entry}" ]; then
      if [ -n "${clean_ld_library_path}" ]; then
        clean_ld_library_path="${clean_ld_library_path}:${entry}"
      else
        clean_ld_library_path="${entry}"
      fi
    fi
  done
  IFS="$old_ifs"
fi
runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
path_value="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
if [ -d "${HOME}/.local/bin" ]; then
  path_value="${HOME}/.local/bin:${path_value}"
fi
exec env -i \
  HOME="${HOME}" \
  USER="${USER:-$(id -un)}" \
  LOGNAME="${LOGNAME:-${USER:-$(id -un)}}" \
  SHELL="${SHELL:-/bin/sh}" \
  LANG="${LANG:-C.UTF-8}" \
  DISPLAY="${DISPLAY:-:0}" \
  XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}" \
  XDG_RUNTIME_DIR="${runtime_dir}" \
  DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
  PATH="${path_value}" \
  LD_LIBRARY_PATH="${clean_ld_library_path}" \
  "${INSTALL_DIR}/solace-hub" "$@"
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
Icon=${INSTALL_DIR}/solace-browser-release/yinyang-logo.png
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
echo "Solace Hub starts first and owns localhost:8888."
echo "Then use the Open Solace Browser action inside Hub."
echo ""
echo "Agent guide: http://localhost:8888/agents"
echo "Account setup: https://solaceagi.com/register"
echo "Auth: 65537 | FSL-1.1-Apache-2.0"
