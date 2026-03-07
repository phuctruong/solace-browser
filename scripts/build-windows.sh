#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"
UNAME_S="$(uname -s 2>/dev/null || echo unknown)"

mkdir -p "${DIST_DIR}"

case "$UNAME_S" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    ;;
  *)
    echo "ERROR: scripts/build-windows.sh must run on a Windows host (detected: $UNAME_S)" >&2
    echo "Use GitHub Actions windows-latest or native Windows CI for official artifacts." >&2
    exit 1
    ;;
esac

echo "Building Solace Browser Windows package ${VERSION} with PyInstaller"
cd "${ROOT_DIR}"
pyinstaller --noconfirm --name "solace-browser" solace_browser_server.py

ARTIFACT="${DIST_DIR}/solace-browser.exe"
if [ ! -f "${ARTIFACT}" ]; then
  echo "ERROR: expected Windows artifact missing at ${ARTIFACT}" >&2
  exit 1
fi

INSTALLER_ARTIFACT="${DIST_DIR}/solace-browser-windows-x86_64.msi"
echo "Packaging Windows installer (MSI)"
powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -File "${ROOT_DIR}/scripts/package-windows-msi.ps1" \
  -InputBinary "${ARTIFACT}" \
  -OutputMsi "${INSTALLER_ARTIFACT}" \
  -AppVersion "${VERSION}"

if [ ! -f "${INSTALLER_ARTIFACT}" ]; then
  echo "ERROR: expected Windows installer missing at ${INSTALLER_ARTIFACT}" >&2
  exit 1
fi

if [ "${WINDOWS_SIGNING_REQUIRED:-0}" = "1" ]; then
  echo "Signing Windows MSI (required)"
  powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File "${ROOT_DIR}/scripts/sign-windows-msi.ps1" \
    -InputMsi "${INSTALLER_ARTIFACT}" \
    -RequireSigning
else
  echo "Signing Windows MSI (best-effort)"
  powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File "${ROOT_DIR}/scripts/sign-windows-msi.ps1" \
    -InputMsi "${INSTALLER_ARTIFACT}"
fi

python3 - <<'PY'
from pathlib import Path
import hashlib

root = Path.cwd()
version = (root / "VERSION").read_text(encoding="utf-8").strip()
artifact = root / "dist" / "solace-browser-windows-x86_64.msi"
digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
(root / "dist" / f"solace-browser-{version}-windows-x86_64.sha256").write_text(
    digest + "  solace-browser-windows-x86_64.msi\n",
    encoding="utf-8",
)
PY
