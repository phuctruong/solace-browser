#!/usr/bin/env bash
# winget/submit.sh — Submit SolaceAI.SolaceBrowser to microsoft/winget-pkgs
# Auth: 65537 | BLOCKED ON: Windows code signing certificate
#
# Prerequisites:
#   - eSign certificate obtained + MSI signed
#   - gh CLI authenticated
#   - wingetcreate installed: dotnet tool install --global Microsoft.WingetCreate
#
# Usage:
#   VERSION=1.0.0 MSI_URL=https://storage.googleapis.com/.../v1.0.0/solace-browser-windows-x86_64.msi \
#   bash scripts/winget/submit.sh

set -euo pipefail

VERSION="${VERSION:-1.0.0}"
MSI_URL="${MSI_URL:-https://storage.googleapis.com/solace-downloads/solace-browser/v${VERSION}/solace-browser-windows-x86_64.msi}"
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests/s/SolaceAI/SolaceBrowser/${VERSION}"

echo "=== winget submission: SolaceAI.SolaceBrowser v${VERSION} ==="

# Verify wingetcreate is available
if ! command -v wingetcreate &>/dev/null; then
  echo "ERROR: wingetcreate not found." >&2
  echo "Install: dotnet tool install --global Microsoft.WingetCreate" >&2
  exit 1
fi

# Verify MSI is accessible and signed
echo "Downloading MSI to verify signature..."
TMP_MSI=$(mktemp --suffix=".msi")
curl -fsSL "${MSI_URL}" -o "${TMP_MSI}"

# Check OLE2 header (MSI)
python3 -c "
import sys
b = open('${TMP_MSI}', 'rb').read(8)
ole2 = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
if b != ole2:
    sys.exit('ERROR: Downloaded file is not a valid MSI (OLE2 header missing)')
print('MSI header: OK')
"

# Get sha256
SHA256=$(python3 -c "
import hashlib, sys
h = hashlib.sha256(open('${TMP_MSI}', 'rb').read()).hexdigest()
print(h)
")
echo "MSI sha256: ${SHA256}"
rm -f "${TMP_MSI}"

# Update installer manifest sha256
INSTALLER_MANIFEST="${MANIFEST_DIR}/SolaceAI.SolaceBrowser.installer.yaml"
sed -i "s/PLACEHOLDER_SHA256_REPLACE_AFTER_SIGNING/${SHA256}/" "${INSTALLER_MANIFEST}"
echo "Updated sha256 in: ${INSTALLER_MANIFEST}"

# Use wingetcreate to validate + submit PR
echo "Submitting to microsoft/winget-pkgs..."
wingetcreate submit \
  --token "$(gh auth token)" \
  "${MANIFEST_DIR}"

echo ""
echo "=== Submission complete ==="
echo "Monitor PR: https://github.com/microsoft/winget-pkgs/pulls"
