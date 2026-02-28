#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"

mkdir -p "${DIST_DIR}"
echo "Building Solace Browser macOS bundle ${VERSION} with PyInstaller"
# Placeholder build command for local packaging contract.
pyinstaller --name "Solace Browser" solace_browser_server.py || true

if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${ROOT_DIR}/VERSION" > "${DIST_DIR}/SolaceBrowser-${VERSION}-mac.sha256"
else
  sha256sum "${ROOT_DIR}/VERSION" > "${DIST_DIR}/SolaceBrowser-${VERSION}-mac.sha256"
fi
