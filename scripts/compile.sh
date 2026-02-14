#!/bin/bash
# Solace Browser: Compile Ungoogled Chromium
# Runs the actual gn/ninja build commands

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_ROOT="$PROJECT_ROOT/source"
BUILD_OUT="$PROJECT_ROOT/out/Release"

echo "🔨 Compiling Solace Browser..."
echo "=============================="
echo ""
echo "Source: $SOURCE_ROOT"
echo "Output: $BUILD_OUT"
echo ""

# Check prerequisites
if [ ! -d "$SOURCE_ROOT" ]; then
    echo "❌ Source not found. Run: ./scripts/init-thorium.sh"
    exit 1
fi

if ! command -v gn >/dev/null 2>&1; then
    echo "❌ gn not found in PATH"
    echo "   Please install depot_tools and add to PATH"
    exit 1
fi

# Step 1: Generate build files
echo "Step 1/3: Generating build configuration..."
cd "$SOURCE_ROOT"
gn gen "$BUILD_OUT"
echo "✅ Build configuration generated"
echo ""

# Step 2: Compile
echo "Step 2/3: Compiling (this may take 20-60 minutes)..."
echo "  Running: ninja -C $BUILD_OUT chrome"
echo ""

# Get CPU count for parallel builds
CPU_COUNT=$(nproc || echo 4)
echo "  Using $CPU_COUNT parallel jobs"
echo ""

ninja -C "$BUILD_OUT" -j "$CPU_COUNT" chrome

echo ""
echo "✅ Compilation complete!"
echo ""

# Step 3: Verify binary
echo "Step 3/3: Verifying binary..."
if [ -f "$BUILD_OUT/chrome" ]; then
    SIZE=$(du -h "$BUILD_OUT/chrome" | cut -f1)
    echo "✅ Binary created: $BUILD_OUT/chrome ($SIZE)"
    echo ""
    echo "To test:"
    echo "  $BUILD_OUT/chrome"
    echo ""
else
    echo "⚠️  Binary not found at expected location"
    echo "   Check output above for compilation errors"
    exit 1
fi
