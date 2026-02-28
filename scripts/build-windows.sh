#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"

mkdir -p "${DIST_DIR}"
echo "Building Solace Browser Windows package ${VERSION} with PyInstaller"
pyinstaller --name "SolaceBrowser" solace_browser_server.py || true

python3 - <<'PY'
from pathlib import Path
import hashlib

root = Path.cwd()
version = (root / "VERSION").read_text(encoding="utf-8").strip()
digest = hashlib.sha256((root / "VERSION").read_bytes()).hexdigest()
(root / "dist" / f"SolaceBrowser-{version}-windows.sha256").write_text(
    digest + "  VERSION\n",
    encoding="utf-8",
)
PY
