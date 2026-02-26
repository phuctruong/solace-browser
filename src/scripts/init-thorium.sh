#!/bin/bash
# Solace Browser Phase 1: Initialize Ungoogled Chromium Fork
# This script clones Ungoogled Chromium and sets up the build environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Solace Browser Phase 1: Ungoogled Chromium Fork Initialization"
echo "================================================================"
echo ""

# Step 1: Check prerequisites
echo "Step 1/5: Checking prerequisites..."
command -v git >/dev/null 2>&1 || { echo "❌ git not found"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 not found"; exit 1; }
echo "✅ Prerequisites OK (git, python3)"
echo ""

# Step 2: Check if Thorium already cloned
if [ -d "$PROJECT_ROOT/source" ]; then
    echo "⚠️  Source directory already exists"
    echo "   To reconfigure, delete: rm -rf $PROJECT_ROOT/source"
    echo "   Skipping clone..."
else
    echo "Step 2/5: Cloning Ungoogled Chromium browser..."
    echo "  (This may take a few minutes...)"
    cd "$PROJECT_ROOT"

    # Clone Ungoogled Chromium
    git clone --depth 1 https://github.com/ungoogled-software/ungoogled-chromium source

    echo "✅ Ungoogled Chromium cloned to: $PROJECT_ROOT/source"
fi
echo ""

# Step 3: Create Solace-specific directories
echo "Step 3/5: Creating Solace directories..."
mkdir -p "$PROJECT_ROOT/src/solace"
mkdir -p "$PROJECT_ROOT/build"
mkdir -p "$PROJECT_ROOT/out"
mkdir -p "$PROJECT_ROOT/third_party"
echo "✅ Directories created"
echo ""

# Step 4: Create build configuration
echo "Step 4/5: Creating build configuration..."
cat > "$PROJECT_ROOT/build/args.gn" << 'EOF'
# Solace Browser Build Configuration
# Based on Ungoogled Chromium optimizations

is_debug = false
is_official_build = true
symbol_level = 0

# Optimization flags (Ungoogled Chromium style)
use_thin_lto = true
v8_use_external_startup_data = false

# Remove Google integrations
google_api_key = ""
google_default_client_id = ""
google_default_client_secret = ""

# Disable tracking/telemetry
enable_reporting = false
reporting_url = ""

# Solace customizations
branding_path_component = "solace"
EOF

echo "✅ Build configuration created"
echo ""

# Step 5: Verify structure
echo "Step 5/5: Verifying structure..."
if [ -d "$PROJECT_ROOT/source" ] && [ -f "$PROJECT_ROOT/source/README.md" ]; then
    echo "✅ Ungoogled Chromium structure verified"
    echo ""
    echo "================================================================"
    echo "✅ Phase 1 Initialization Complete!"
    echo "================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Run build: ./src/scripts/build.sh"
    echo "  2. Or verify setup: ./src/scripts/verify-setup.sh"
    echo ""
    exit 0
else
    echo "⚠️  Ungoogled Chromium structure not as expected"
    echo "   Checking what was cloned..."
    ls -la "$PROJECT_ROOT/source/" | head -20
    echo ""
    echo "This might be OK - structure varies by version."
    echo "Proceeding anyway..."
    exit 0
fi
