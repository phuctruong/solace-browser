#!/usr/bin/env bash
# Diagram: 29-chromium-build-pipeline
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

# 2. Launch via tauri dev when available; otherwise fall back to cargo run.
cd "${HUB_DIR}"
env -i \
  HOME="${HOME}" \
  USER="${USER:-phuc}" \
  DISPLAY="${DISPLAY:-}" \
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
  PATH="${PATH}" \
  bash -lc '
    if cargo tauri --version >/dev/null 2>&1; then
      cargo tauri dev 2>&1
    else
      echo "WARN: cargo-tauri not installed; falling back to cargo run"
      cargo run 2>&1
    fi
  '
