#!/usr/bin/env bash
# start-hub.sh — Launch Solace Hub (Tauri desktop app) for development
# Lifecycle: yinyang-server FIRST → Solace Hub (Tauri) SECOND
# Port: 8888 ONLY. Extensions: ZERO. Naming: "Solace Hub" ONLY.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_DIR="${REPO_ROOT}/solace-hub/src-tauri"

echo "=== Solace Hub Dev Start ==="
echo "Repo: ${REPO_ROOT}"

# 1. Check cargo/tauri-cli available
if ! command -v cargo &>/dev/null; then
  echo "ERROR: cargo not found. Run scripts/install-rust.sh"
  exit 1
fi

echo "Solace Hub starts first and will launch Yinyang Server on localhost:8888."
echo "After the Hub window appears, verify the runtime with: curl http://127.0.0.1:8888/api/status"

# 2. Launch via tauri dev (spawns yinyang-server via Hub lifecycle)
cd "${HUB_DIR}"
cargo tauri dev 2>&1
