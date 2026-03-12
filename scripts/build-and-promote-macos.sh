#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUCKET="${BUCKET:-solace-downloads}"
TAG="${TAG:-v$(cat "${REPO_ROOT}/VERSION")}"

cd "${REPO_ROOT}"
bash scripts/build-macos-release.sh
python3 scripts/promote_native_builds_to_gcs.py \
  --tag "${TAG}" \
  --artifacts-dir dist \
  --bucket "${BUCKET}"
