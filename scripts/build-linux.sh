#!/usr/bin/env bash
set -euo pipefail

# solace-browser Linux build script
# Rung: 641 | Belt: Yellow | Channel: [3]
#
# Builds a Linux x86_64 binary using PyInstaller.
# Optionally compresses with UPX if available.
#
# Upload target:
#   gs://solace-downloads/solace-browser/v1.0.0/solace-browser-linux-x86_64

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"
BINARY_NAME="solace-browser"

# ---- Platform check ----
UNAME_S="$(uname -s)"
if [ "${UNAME_S}" != "Linux" ]; then
    echo "ERROR: build-linux.sh must run on Linux (detected: ${UNAME_S})" >&2
    exit 1
fi

# ---- Architecture detection ----
UNAME_M="$(uname -m)"
echo "Detected architecture: ${UNAME_M}"
echo "Building Solace Browser Linux binary v${VERSION} with PyInstaller"

# ---- Build ----
mkdir -p "${DIST_DIR}"
cd "${ROOT_DIR}"
pyinstaller --name "${BINARY_NAME}" solace_browser_server.py \
    --distpath "${DIST_DIR}" \
    --workpath "${ROOT_DIR}/build" \
    --clean

# ---- Verify binary was created ----
BINARY_PATH="${DIST_DIR}/${BINARY_NAME}"
if [ ! -f "${BINARY_PATH}" ]; then
    echo "ERROR: Build failed — binary not found at ${BINARY_PATH}" >&2
    exit 1
fi

echo "Binary built: ${BINARY_PATH}"
echo "Binary size: $(du -h "${BINARY_PATH}" | cut -f1)"

# ---- UPX compression (optional) ----
if command -v upx >/dev/null 2>&1; then
    echo "UPX found — compressing binary..."
    BEFORE_SIZE="$(stat --printf='%s' "${BINARY_PATH}")"
    upx --best --lzma "${BINARY_PATH}"
    AFTER_SIZE="$(stat --printf='%s' "${BINARY_PATH}")"
    echo "UPX compression: ${BEFORE_SIZE} -> ${AFTER_SIZE} bytes"
else
    echo "UPX not found — skipping compression (install with: apt install upx-ucl)"
fi

# ---- SHA-256 checksum ----
sha256sum "${BINARY_PATH}" > "${DIST_DIR}/${BINARY_NAME}-${VERSION}-linux-${UNAME_M}.sha256"
echo "SHA-256 checksum written to: ${DIST_DIR}/${BINARY_NAME}-${VERSION}-linux-${UNAME_M}.sha256"

echo "Verifying SHA-256 checksum..."
sha256sum -c "${DIST_DIR}/${BINARY_NAME}-${VERSION}-linux-${UNAME_M}.sha256"
echo "SHA-256 verification passed."

# ---- Sanity check: binary is executable ----
echo "Running sanity check..."
if file "${BINARY_PATH}" | grep -q "ELF"; then
    echo "Sanity check passed: binary is a valid ELF executable"
else
    echo "ERROR: Binary does not appear to be a valid ELF executable" >&2
    file "${BINARY_PATH}" >&2
    exit 1
fi

echo "Linux build complete: v${VERSION} ${UNAME_M} binary"
