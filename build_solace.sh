#!/bin/bash
# Build Solace Browser from source_full (Chromium)
set -e

PROJECT_ROOT="$HOME/projects/solace-browser"
SOURCE_ROOT="$PROJECT_ROOT/source_full"
BUILD_OUT="$PROJECT_ROOT/out/Release"

echo "🔨 Building Solace Browser from Chromium source..."
echo "=================================================="

# Step 1: Find or setup chromium src
if [ ! -d "$SOURCE_ROOT/src" ]; then
    echo "Setting up Chromium source in source_full..."
    cd "$SOURCE_ROOT"
    gclient sync --with_branch_heads || true
fi

# Step 2: Generate build files
if [ -d "$SOURCE_ROOT/src" ]; then
    cd "$SOURCE_ROOT/src"
    gn gen "$BUILD_OUT" --args='is_debug=false is_official_build=true'
    echo "✅ Build configuration generated"
else
    echo "⚠️  Chromium src not found, using source/ instead"
    cd "$PROJECT_ROOT/source"
    gn gen "$BUILD_OUT"
fi

# Step 3: Start compilation (background with nohup)
echo "🔨 Starting compilation (this will run in background)..."
echo "   Output: $BUILD_OUT/compile.log"
nohup ninja -C "$BUILD_OUT" -j $(nproc) chrome > "$BUILD_OUT/compile.log" 2>&1 &
PID=$!
echo "   Process PID: $PID"
echo "   To monitor: tail -f $BUILD_OUT/compile.log"
echo ""
echo "Build started in background. This may take 20-60 minutes..."
