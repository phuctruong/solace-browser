#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"

mkdir -p "${DIST_DIR}"
echo "Building Solace Browser Linux package ${VERSION} with PyInstaller"
pyinstaller --name "solace-browser" solace_browser_server.py || true
sha256sum "${ROOT_DIR}/VERSION" > "${DIST_DIR}/SolaceBrowser-${VERSION}-linux.sha256"
