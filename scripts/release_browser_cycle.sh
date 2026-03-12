#!/usr/bin/env bash
# release_browser_cycle.sh — Build real downloadable Solace Browser artifacts.
# Auth: 65537 | Hub first | Port 8888 only

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_OS="${TARGET_OS:-}"

if [ -z "${TARGET_OS}" ]; then
  case "$(uname -s)" in
    Linux*) TARGET_OS="linux" ;;
    Darwin*) TARGET_OS="macos" ;;
    MINGW*|MSYS*|CYGWIN*) TARGET_OS="windows" ;;
    *) echo "ERROR: Cannot detect OS. Set TARGET_OS explicitly." >&2; exit 1 ;;
  esac
fi

case "${TARGET_OS}" in
  linux)
    "${REPO_ROOT}/scripts/build-linux-release.sh"
    "${REPO_ROOT}/scripts/build-deb.sh"
    ;;
  macos)
    "${REPO_ROOT}/scripts/build-macos-release.sh"
    ;;
  windows)
    if command -v pwsh >/dev/null 2>&1; then
      pwsh -File "${REPO_ROOT}/scripts/build-windows-release.ps1"
    elif command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -File "${REPO_ROOT}/scripts/build-windows-release.ps1"
    else
      echo "ERROR: Windows release requires pwsh or powershell.exe on PATH." >&2
      exit 1
    fi
    ;;
  *)
    echo "ERROR: Unknown TARGET_OS=${TARGET_OS}" >&2
    exit 1
    ;;
esac
