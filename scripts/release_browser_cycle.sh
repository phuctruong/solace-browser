#!/usr/bin/env bash
# release_browser_cycle.sh — Build Solace Browser native binary for a single platform
# Auth: 65537 | Legacy debug port permanently banned | "Companion App": BANNED
#
# Environment:
#   TARGET_OS        linux | macos | windows  (default: auto-detect)
#   UPLOAD_ENABLED   0 | 1                    (default: 0)
#   DOWNLOAD_ENABLED 0 | 1                    (default: 0, unused here)
#   RUN_SMOKE        0 | 1                    (default: 0)
#
# Outputs:
#   dist/solace-browser-{linux-x86_64 | macos-universal | windows-x86_64.msi}
#   dist/solace-browser-{...}.sha256
#   scratch/release-cycle/<timestamp>/{pyinstaller.log, metrics.json, report.md}

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${REPO_ROOT}/scratch/release-cycle/${TIMESTAMP}"
DIST_DIR="${REPO_ROOT}/dist"

TARGET_OS="${TARGET_OS:-}"
UPLOAD_ENABLED="${UPLOAD_ENABLED:-0}"
RUN_SMOKE="${RUN_SMOKE:-0}"

# Auto-detect OS if not set
if [ -z "${TARGET_OS}" ]; then
  case "$(uname -s)" in
    Linux*)   TARGET_OS="linux" ;;
    Darwin*)  TARGET_OS="macos" ;;
    MINGW*|MSYS*|CYGWIN*) TARGET_OS="windows" ;;
    *)        echo "ERROR: Cannot detect OS. Set TARGET_OS=linux|macos|windows" >&2; exit 1 ;;
  esac
fi

echo "=== Solace Browser Release Cycle ==="
echo "TARGET_OS:        ${TARGET_OS}"
echo "UPLOAD_ENABLED:   ${UPLOAD_ENABLED}"
echo "RUN_SMOKE:        ${RUN_SMOKE}"
echo "REPO_ROOT:        ${REPO_ROOT}"
echo "RUN_DIR:          ${RUN_DIR}"
echo ""

mkdir -p "${RUN_DIR}" "${DIST_DIR}"

ENTRY_POINT="${REPO_ROOT}/yinyang_server.py"
if [ ! -f "${ENTRY_POINT}" ]; then
  echo "ERROR: entry point not found: ${ENTRY_POINT}" >&2
  exit 1
fi

# Verify PyInstaller is available
if ! command -v pyinstaller &>/dev/null; then
  echo "ERROR: pyinstaller not found. Install with: pip install pyinstaller" >&2
  exit 1
fi

echo "pyinstaller: $(pyinstaller --version)"
echo "python:      $(python3 --version)"

# ---------- Platform-specific build ----------

case "${TARGET_OS}" in
  linux)
    BINARY_NAME="solace-browser-linux-x86_64"
    echo ">>> Building Linux x86_64 ELF..."
    pyinstaller \
      --onefile \
      --name "${BINARY_NAME}" \
      --distpath "${DIST_DIR}" \
      --workpath "${RUN_DIR}/build" \
      --specpath "${RUN_DIR}" \
      --log-level INFO \
      "${ENTRY_POINT}" \
      2>&1 | tee "${RUN_DIR}/pyinstaller.log"
    ;;

  macos)
    BINARY_NAME="solace-browser-macos-universal"
    echo ">>> Building macOS universal (arm64 + x86_64)..."
    pyinstaller \
      --onefile \
      --name "${BINARY_NAME}" \
      --distpath "${DIST_DIR}" \
      --workpath "${RUN_DIR}/build" \
      --specpath "${RUN_DIR}" \
      --target-arch universal2 \
      --log-level INFO \
      "${ENTRY_POINT}" \
      2>&1 | tee "${RUN_DIR}/pyinstaller.log"
    ;;

  windows)
    BINARY_NAME_EXE="solace-browser-windows-x86_64.exe"
    BINARY_NAME_MSI="solace-browser-windows-x86_64.msi"
    echo ">>> Building Windows x86_64 EXE..."
    pyinstaller \
      --onefile \
      --name "solace-browser-windows-x86_64" \
      --distpath "${DIST_DIR}" \
      --workpath "${RUN_DIR}/build" \
      --specpath "${RUN_DIR}" \
      --log-level INFO \
      --icon "${REPO_ROOT}/solace-hub/src-tauri/icons/icon.ico" \
      "${ENTRY_POINT}" \
      2>&1 | tee "${RUN_DIR}/pyinstaller.log"

    echo ">>> Building Windows MSI installer..."
    WXS="${REPO_ROOT}/scripts/windows/solace-browser.wxs"
    if [ ! -f "${WXS}" ]; then
      echo "ERROR: WiX source not found: ${WXS}" >&2
      exit 1
    fi

    # Build MSI with WiX v4
    wix build \
      -src "${WXS}" \
      -out "${DIST_DIR}/${BINARY_NAME_MSI}" \
      -d "ExeDir=${DIST_DIR}" \
      2>&1 | tee -a "${RUN_DIR}/pyinstaller.log"

    BINARY_NAME="${BINARY_NAME_MSI}"
    ;;

  *)
    echo "ERROR: Unknown TARGET_OS=${TARGET_OS}. Must be linux|macos|windows" >&2
    exit 1
    ;;
esac

# ---------- SHA256 ----------

echo ">>> Generating sha256..."
BINARY_PATH="${DIST_DIR}/${BINARY_NAME}"
if [ ! -f "${BINARY_PATH}" ]; then
  echo "ERROR: expected binary not found: ${BINARY_PATH}" >&2
  exit 1
fi

python3 -c "
import hashlib, sys
from pathlib import Path
p = Path('${BINARY_PATH}')
digest = hashlib.sha256(p.read_bytes()).hexdigest()
sha_path = Path('${DIST_DIR}/${BINARY_NAME}.sha256')
sha_path.write_text(f'{digest}  ${BINARY_NAME}\n', encoding='utf-8')
size = p.stat().st_size
print(f'sha256: {digest}')
print(f'size:   {size:,} bytes ({round(size/1024/1024,2)} MB)')
"

# ---------- Smoke test ----------

if [ "${RUN_SMOKE}" = "1" ]; then
  echo ">>> Running smoke test..."
  "${BINARY_PATH}" --version 2>&1 || true
fi

# ---------- metrics.json ----------

BINARY_SIZE_BYTES=$(python3 -c "import os; print(os.path.getsize('${BINARY_PATH}'))")
BINARY_SHA256=$(python3 -c "
import hashlib
from pathlib import Path
print(hashlib.sha256(Path('${BINARY_PATH}').read_bytes()).hexdigest())
")

cat > "${RUN_DIR}/metrics.json" <<METRICS
{
  "timestamp": "${TIMESTAMP}",
  "target_os": "${TARGET_OS}",
  "binary_name": "${BINARY_NAME}",
  "binary_path": "${BINARY_PATH}",
  "binary_size_bytes": ${BINARY_SIZE_BYTES},
  "binary_sha256": "${BINARY_SHA256}",
  "upload_enabled": ${UPLOAD_ENABLED},
  "smoke_run": ${RUN_SMOKE}
}
METRICS

# ---------- report.md ----------

cat > "${RUN_DIR}/report.md" <<REPORT
# Solace Browser Release Cycle Report

- **Timestamp**: ${TIMESTAMP}
- **Target OS**: ${TARGET_OS}
- **Binary**: ${BINARY_NAME}
- **SHA256**: ${BINARY_SHA256}
- **Size**: ${BINARY_SIZE_BYTES} bytes
- **Upload**: ${UPLOAD_ENABLED}
REPORT

echo ""
echo "=== Build complete ==="
echo "Binary:  ${BINARY_PATH}"
echo "SHA256:  ${BINARY_SHA256}"
echo "Size:    ${BINARY_SIZE_BYTES} bytes"
echo "Run dir: ${RUN_DIR}"
