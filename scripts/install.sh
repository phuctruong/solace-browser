#!/bin/sh
# Diagram: 29-chromium-build-pipeline

set -eu

STATE_DIR="${HOME}/.solace"
LIB_DIR="${HOME}/.local/lib/solace"
BIN_DIR="${HOME}/.local/bin"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "$1 not found"
  fi
}

resolve_repo_root() {
  repo_candidate=$(CDPATH= cd "${SCRIPT_DIR}/.." 2>/dev/null && pwd)
  if [ -f "${repo_candidate}/yinyang-server.py" ]; then
    printf '%s\n' "${repo_candidate}"
    return 0
  fi

  if [ -f "${STATE_DIR}/repo-root" ]; then
    repo_root=$(sed -n '1p' "${STATE_DIR}/repo-root")
    if [ -n "${repo_root}" ] && [ -f "${repo_root}/yinyang-server.py" ]; then
      printf '%s\n' "${repo_root}"
      return 0
    fi
  fi

  fail "unable to locate repository root containing yinyang-server.py"
}

require_cmd cp
require_cmd chmod
require_cmd ln
require_cmd mkdir
require_cmd systemctl

repo_root=$(resolve_repo_root)

mkdir -p "${STATE_DIR}" "${LIB_DIR}" "${BIN_DIR}" "${SYSTEMD_DIR}"

cp "${SCRIPT_DIR}/launch-yinyang.sh" "${LIB_DIR}/launch-yinyang.sh"
cp "${SCRIPT_DIR}/stop-yinyang.sh" "${LIB_DIR}/stop-yinyang.sh"
cp "${SCRIPT_DIR}/install.sh" "${LIB_DIR}/install.sh"
cp "${SCRIPT_DIR}/yinyang.service" "${LIB_DIR}/yinyang.service"
chmod 755 "${LIB_DIR}/launch-yinyang.sh" "${LIB_DIR}/stop-yinyang.sh" "${LIB_DIR}/install.sh"
ln -sf "${repo_root}/scripts/solace" "${BIN_DIR}/solace"

printf '%s\n' "${repo_root}" > "${STATE_DIR}/repo-root"
cp "${SCRIPT_DIR}/yinyang.service" "${SYSTEMD_DIR}/yinyang.service"

systemctl --user daemon-reload
systemctl --user enable yinyang

## Icons and desktop entry
ICON_DIR="${HOME}/.local/share/icons/hicolor/128x128/apps"
APP_DIR="${HOME}/.local/share/applications"
mkdir -p "${ICON_DIR}" "${APP_DIR}"

if [ -f "${SCRIPT_DIR}/../solace-hub/src-tauri/icons/solace-hub-icon-128.png" ]; then
  cp "${SCRIPT_DIR}/../solace-hub/src-tauri/icons/solace-hub-icon-128.png" "${ICON_DIR}/solace-hub.png"
  echo "Installed solace-hub icon to ${ICON_DIR}/solace-hub.png"
fi

if [ -f "${SCRIPT_DIR}/../solace-hub/src-tauri/icons/solace-browser-icon-128.png" ]; then
  cp "${SCRIPT_DIR}/../solace-hub/src-tauri/icons/solace-browser-icon-128.png" "${ICON_DIR}/solace-browser.png"
  echo "Installed solace-browser icon to ${ICON_DIR}/solace-browser.png"
fi

if [ -f "${SCRIPT_DIR}/solace-hub.desktop" ]; then
  cp "${SCRIPT_DIR}/solace-hub.desktop" "${APP_DIR}/solace-hub.desktop"
  echo "Installed desktop entry to ${APP_DIR}/solace-hub.desktop"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APP_DIR}" 2>/dev/null || true
fi

echo "Installed Yinyang launcher to ${LIB_DIR}"
echo "Installed solace CLI to ${BIN_DIR}/solace"
echo "Systemd user unit installed at ${SYSTEMD_DIR}/yinyang.service"
echo "Next step: start Solace Hub first via ./scripts/start-hub.sh"
echo "Then verify the runtime with: curl http://127.0.0.1:8888/api/status"
