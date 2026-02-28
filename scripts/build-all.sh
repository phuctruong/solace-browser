#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

mkdir -p "${DIST_DIR}"
"${ROOT_DIR}/scripts/build-mac.sh"
"${ROOT_DIR}/scripts/build-linux.sh"
"${ROOT_DIR}/scripts/build-windows.sh"
