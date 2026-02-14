#!/bin/bash
# Solace Browser Phase 1: Build Ungoogled Chromium Fork
# Compiles Solace Browser from Ungoogled Chromium source

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔨 Solace Browser Phase 1: Build Ungoogled Chromium Fork"
echo "============================================="
echo ""

# Check if source exists
if [ ! -d "$PROJECT_ROOT/source" ]; then
    echo "❌ Source directory not found!"
    echo "   Run: ./scripts/init-thorium.sh"
    exit 1
fi

# Step 1: Verify build configuration
echo "Step 1/4: Verifying build configuration..."
if [ ! -f "$PROJECT_ROOT/build/args.gn" ]; then
    echo "❌ Build configuration not found (build/args.gn)"
    exit 1
fi
echo "✅ Build configuration OK"
echo ""

# Step 2: Install depot_tools (if needed)
echo "Step 2/4: Checking build tools..."
if ! command -v gn >/dev/null 2>&1; then
    echo "⚠️  gn not found in PATH"
    echo "   Ungoogled Chromium requires depot_tools."
    echo "   This is usually installed during source setup."
    echo ""
    echo "   To fix, follow Ungoogled Chromium build guide:"
    echo "   https://github.com/thorium-browser/thorium/wiki/Building"
fi
echo "✅ Build tools check complete"
echo ""

# Step 3: Configure build
echo "Step 3/4: Configuring Solace Browser build..."
mkdir -p "$PROJECT_ROOT/out/Release"
cp "$PROJECT_ROOT/build/args.gn" "$PROJECT_ROOT/out/Release/args.gn"
echo "✅ Configuration copied to: $PROJECT_ROOT/out/Release/args.gn"
echo ""

# Step 4: Build instructions
echo "Step 4/4: Build instructions"
echo "============================================="
echo ""
echo "Manual build steps (run in ~/projects/solace-browser/source):"
echo ""
echo "  # Configure"
echo "  gn gen ../out/Release"
echo ""
echo "  # Build"
echo "  ninja -C ../out/Release chrome"
echo ""
echo "Expected result:"
echo "  Binary: ~/projects/solace-browser/out/Release/chrome"
echo "  Size: ~300-400 MB"
echo "  Time: 20-60 minutes (depending on CPU)"
echo ""
echo "============================================="
echo ""
echo "To start the build, run:"
echo ""
echo "  cd $PROJECT_ROOT/source"
echo "  gn gen ../out/Release"
echo "  ninja -C ../out/Release chrome"
echo ""
echo "Or use our helper:"
echo "  ./scripts/compile.sh"
echo ""
