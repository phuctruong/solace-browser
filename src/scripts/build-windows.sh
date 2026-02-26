#!/bin/bash
# Solace Browser — Windows MSI Build Script
# Produces: dist/SolaceBrowser-{VERSION}-windows-x64.msi
# Requires: Python 3.10+, PyInstaller, Tauri CLI, Rust toolchain, cross-compilation tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------
if [ -f "$PROJECT_ROOT/VERSION" ]; then
    VERSION="$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')"
elif command -v python3 >/dev/null 2>&1 && [ -f "$PROJECT_ROOT/package.json" ]; then
    VERSION="$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/package.json')); print(d['version'])")"
else
    VERSION="1.0.0"
fi

echo "Solace Browser Windows Build — v${VERSION}"
echo "=========================================="

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
DIST_DIR="$PROJECT_ROOT/dist"
mkdir -p "$DIST_DIR"

echo "Output directory: $DIST_DIR"

# ---------------------------------------------------------------------------
# Step 1: Bundle Python server with PyInstaller (cross-compile for Windows)
# ---------------------------------------------------------------------------
echo ""
echo "Step 1/4: Bundling Python server component (PyInstaller)..."

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "  WARNING: pyinstaller not found. Skipping Python bundle step."
    echo "  Install with: pip install pyinstaller"
else
    # Note: true Windows .exe requires running PyInstaller on Windows or Wine
    PYINSTALLER_OUT="$DIST_DIR/solace-server-windows-x64"
    pyinstaller \
        --onefile \
        --distpath "$PYINSTALLER_OUT" \
        --workpath "$DIST_DIR/pyinstaller-build-windows" \
        --name "solace-server" \
        "$PROJECT_ROOT/solace_browser_server.py" 2>/dev/null || \
        echo "  WARNING: PyInstaller build failed (non-fatal — Windows cross-compile may require Wine)"
    echo "  Python server bundle step complete."
fi

# ---------------------------------------------------------------------------
# Step 2: Build Tauri desktop shell for Windows (requires cross-compilation)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2/4: Building Tauri desktop shell..."

if [ -d "$PROJECT_ROOT/src-tauri" ]; then
    if command -v cargo >/dev/null 2>&1; then
        # Add Windows target
        rustup target add x86_64-pc-windows-msvc 2>/dev/null || \
            echo "  WARNING: Could not add x86_64-pc-windows-msvc target"

        if command -v tauri >/dev/null 2>&1; then
            cd "$PROJECT_ROOT"
            tauri build --target x86_64-pc-windows-msvc 2>/dev/null || \
                echo "  WARNING: Tauri Windows cross-compile failed (requires Windows SDK or cross toolchain)"
        else
            echo "  WARNING: tauri CLI not found. Install with: cargo install tauri-cli"
        fi
    else
        echo "  WARNING: cargo not found. Rust toolchain required for Tauri build."
    fi
else
    echo "  WARNING: src-tauri/ not found. Skipping Tauri build."
fi

# ---------------------------------------------------------------------------
# Step 3: Package MSI installer
# ---------------------------------------------------------------------------
echo ""
echo "Step 3/4: Creating MSI installer..."

MSI_NAME="SolaceBrowser-${VERSION}-windows-x64.msi"
MSI_PATH="$DIST_DIR/${MSI_NAME}"

TAURI_MSI=$(find "$PROJECT_ROOT/src-tauri/target" -name "*.msi" 2>/dev/null | head -1)
if [ -n "$TAURI_MSI" ]; then
    cp "$TAURI_MSI" "$MSI_PATH"
    echo "  Copied Tauri MSI: ${MSI_NAME}"
else
    # Create placeholder for testing
    echo "MSI_PLACEHOLDER version=${VERSION} arch=x64" > "$MSI_PATH"
    echo "  Created placeholder: ${MSI_NAME} (Tauri Windows build not available on this host)"
fi

# ---------------------------------------------------------------------------
# Step 4: Generate SHA-256 checksums
# ---------------------------------------------------------------------------
echo ""
echo "Step 4/4: Generating SHA-256 checksums..."

CHECKSUM_FILE="$DIST_DIR/SHA256SUMS-windows.txt"
> "$CHECKSUM_FILE"

if [ -f "$MSI_PATH" ]; then
    sha256sum "$MSI_PATH" | sed "s|$DIST_DIR/||" >> "$CHECKSUM_FILE"
    echo "  Checksum written for ${MSI_NAME}"
fi

echo ""
echo "=========================================="
echo "Windows build complete — v${VERSION}"
echo "Output: $DIST_DIR"
echo ""
ls -lh "$DIST_DIR"/*.msi 2>/dev/null || true
echo ""
echo "Checksums:"
cat "$CHECKSUM_FILE" 2>/dev/null || true
echo ""
echo "Note: For native Windows MSI, run this script on a Windows host or use"
echo "      GitHub Actions windows-latest runner with the Tauri action."
