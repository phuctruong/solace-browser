#!/bin/bash
# Diagram: 29-chromium-build-pipeline
# build-chromium.sh — Build Solace Browser (Chromium fork)
# Auth: 65537 | Task 001: Build Verification
# Port 9222 is PERMANENTLY BANNED. This script never references it.

set -euo pipefail

DEPOT_TOOLS_DIR="$(dirname "$(realpath "$0")")/../depot_tools"
SOURCE_DIR="$(dirname "$(realpath "$0")")/../source/src"
OUT_DIR="${SOURCE_DIR}/out/Solace"

# Step 1: Add depot_tools to PATH
export PATH="${DEPOT_TOOLS_DIR}:${PATH}"

# Verify autoninja is available
if ! command -v autoninja &>/dev/null; then
    echo "ERROR: autoninja not found in ${DEPOT_TOOLS_DIR}"
    echo "Fix: ensure depot_tools is populated (run: git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git)"
    exit 1
fi

echo "INFO: depot_tools PATH: ${DEPOT_TOOLS_DIR}"
echo "INFO: autoninja: $(which autoninja)"

# Step 2: Configure GN if not already done
if [ ! -f "${OUT_DIR}/args.gn" ]; then
    echo "INFO: Configuring GN..."
    cd "${SOURCE_DIR}"
    gn gen out/Solace --args='is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true proprietary_codecs=false'
    echo "INFO: GN configured at ${OUT_DIR}/args.gn"
else
    echo "INFO: GN already configured at ${OUT_DIR}/args.gn"
fi

# Step 3: Build
echo "INFO: Starting autoninja build..."
cd "${SOURCE_DIR}"
autoninja -C out/Solace solace

echo "INFO: Build complete."
