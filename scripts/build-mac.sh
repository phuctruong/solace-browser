#!/usr/bin/env bash
set -euo pipefail

# solace-browser macOS build script
# Rung: 641 | Belt: Yellow | Channel: [3]
#
# Builds a macOS universal binary (x86_64 + arm64) using PyInstaller.
# Uses solace-browser-macos.spec for macOS-specific configuration.
# Applies ad-hoc code signing via codesign_identity='-' in the spec.
#
# Upload target:
#   gs://solace-downloads/solace-browser/v1.0.0/solace-browser-macos-universal

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"
SPEC_FILE="${ROOT_DIR}/solace-browser-macos.spec"
BINARY_NAME="solace-browser"
GCS_BUCKET="gs://solace-downloads/solace-browser/v${VERSION}"

# ---- Platform check ----
UNAME_S="$(uname -s)"
if [ "${UNAME_S}" != "Darwin" ]; then
    echo "ERROR: build-mac.sh must run on macOS (detected: ${UNAME_S})" >&2
    exit 1
fi

# ---- Architecture detection ----
UNAME_M="$(uname -m)"
echo "Detected architecture: ${UNAME_M}"
echo "Building Solace Browser macOS universal binary v${VERSION} with PyInstaller"

# ---- Verify spec file exists ----
if [ ! -f "${SPEC_FILE}" ]; then
    echo "ERROR: macOS spec file not found: ${SPEC_FILE}" >&2
    exit 1
fi

# ---- Build ----
mkdir -p "${DIST_DIR}"
cd "${ROOT_DIR}"
pyinstaller "${SPEC_FILE}" --distpath "${DIST_DIR}" --workpath "${ROOT_DIR}/build" --clean

# ---- Verify binary was created ----
BINARY_PATH="${DIST_DIR}/${BINARY_NAME}"
if [ ! -f "${BINARY_PATH}" ]; then
    echo "ERROR: Build failed — binary not found at ${BINARY_PATH}" >&2
    exit 1
fi

echo "Binary built: ${BINARY_PATH}"
echo "Binary size: $(du -h "${BINARY_PATH}" | cut -f1)"

# ---- Ad-hoc code signing verification ----
if command -v codesign >/dev/null 2>&1; then
    echo "Verifying ad-hoc code signature..."
    codesign --verify --verbose "${BINARY_PATH}" 2>&1 || echo "WARNING: codesign verify returned non-zero (ad-hoc signing may need re-sign)"
fi

# ---- SHA-256 checksum ----
if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${BINARY_PATH}" > "${DIST_DIR}/${BINARY_NAME}-${VERSION}-macos-universal.sha256"
else
    sha256sum "${BINARY_PATH}" > "${DIST_DIR}/${BINARY_NAME}-${VERSION}-macos-universal.sha256"
fi

echo "SHA-256 checksum written to: ${DIST_DIR}/${BINARY_NAME}-${VERSION}-macos-universal.sha256"

# ---- Upload to GCS (if gsutil available) ----
if command -v gsutil >/dev/null 2>&1; then
    echo "Uploading to ${GCS_BUCKET}/..."
    gsutil cp "${BINARY_PATH}" "${GCS_BUCKET}/${BINARY_NAME}-macos-universal"
    gsutil cp "${DIST_DIR}/${BINARY_NAME}-${VERSION}-macos-universal.sha256" \
        "${GCS_BUCKET}/${BINARY_NAME}-macos-universal.sha256"
    echo "Upload complete."
else
    echo "gsutil not found — skipping GCS upload."
    echo "Manual upload target: ${GCS_BUCKET}/${BINARY_NAME}-macos-universal"
fi

echo "macOS build complete: v${VERSION} universal binary"
