#!/usr/bin/env bash
# Diagram: 29-chromium-build-pipeline
# upload-chromium-bootstrap.sh — Upload local Chromium build to GCS as bootstrap payload.
# This must be run BEFORE CI can build releases (CI downloads the Chromium binary from GCS).
# Auth: 65537

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROMIUM_OUT="${CHROMIUM_OUT:-${REPO_ROOT}/source/src/out/Solace}"
VERSION="$(cat "${REPO_ROOT}/VERSION")"
GCS_BUCKET="${GCS_BUCKET:-gs://solace-downloads/solace-browser}"
DIST_DIR="${DIST_DIR:-${REPO_ROOT}/dist}"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_file() {
  [ -e "$1" ] || fail "required path not found: $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found"
}

require_cmd gcloud
require_cmd tar
require_cmd sha256sum

# Verify Chromium build exists
require_file "${CHROMIUM_OUT}/solace"
echo "Chromium binary: ${CHROMIUM_OUT}/solace ($(stat -c%s "${CHROMIUM_OUT}/solace") bytes)"

# Build the release tarball using the standard build script
echo "Building full Linux release tarball..."
TARGET_OS=linux bash "${REPO_ROOT}/scripts/release_browser_cycle.sh"

TARBALL="${DIST_DIR}/solace-browser-chromium-linux-x86_64.tar.gz"
require_file "${TARBALL}"
echo "Tarball ready: ${TARBALL} ($(stat -c%s "${TARBALL}") bytes)"

# Verify the tarball contains the solace binary
if ! tar -tzf "${TARBALL}" | grep -q "^solace-browser-release/solace$"; then
  fail "Tarball missing solace-browser-release/solace"
fi
echo "Verified: tarball contains solace-browser-release/solace"

# Upload to GCS versioned + latest
echo "Uploading to ${GCS_BUCKET}/v${VERSION}/..."
gcloud storage cp "${TARBALL}" "${GCS_BUCKET}/v${VERSION}/$(basename "${TARBALL}")"
gcloud storage cp "${TARBALL}.sha256" "${GCS_BUCKET}/v${VERSION}/$(basename "${TARBALL}").sha256"

echo "Uploading to ${GCS_BUCKET}/latest/..."
gcloud storage cp "${TARBALL}" "${GCS_BUCKET}/latest/$(basename "${TARBALL}")"
gcloud storage cp "${TARBALL}.sha256" "${GCS_BUCKET}/latest/$(basename "${TARBALL}").sha256"

echo ""
echo "=== Bootstrap upload complete ==="
echo "Version: v${VERSION}"
echo "GCS: ${GCS_BUCKET}/v${VERSION}/"
echo "GCS: ${GCS_BUCKET}/latest/"
echo ""
echo "CI can now build releases. Tag and push to trigger:"
echo "  git tag -a v${VERSION} -m 'Release v${VERSION}' && git push origin v${VERSION}"
