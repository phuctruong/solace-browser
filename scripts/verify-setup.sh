#!/bin/bash
# Solace Browser: Verify Phase 1 Setup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔍 Verifying Solace Browser Phase 1 Setup"
echo "=========================================="
echo ""

# Check directories
echo "Directory Structure:"
echo "  project root: $PROJECT_ROOT"
[ -d "$PROJECT_ROOT/source" ] && echo "  ✅ source/" || echo "  ❌ source/ (not yet cloned)"
[ -d "$PROJECT_ROOT/src/solace" ] && echo "  ✅ src/solace/" || echo "  ❌ src/solace/"
[ -d "$PROJECT_ROOT/build" ] && echo "  ✅ build/" || echo "  ❌ build/"
[ -d "$PROJECT_ROOT/out" ] && echo "  ✅ out/" || echo "  ❌ out/"
echo ""

# Check files
echo "Configuration Files:"
[ -f "$PROJECT_ROOT/build/args.gn" ] && echo "  ✅ build/args.gn" || echo "  ❌ build/args.gn"
[ -f "$PROJECT_ROOT/README.md" ] && echo "  ✅ README.md" || echo "  ❌ README.md"
[ -f "$PROJECT_ROOT/ROADMAP.md" ] && echo "  ✅ ROADMAP.md" || echo "  ❌ ROADMAP.md"
echo ""

# Check tools
echo "Build Tools:"
command -v git >/dev/null 2>&1 && echo "  ✅ git" || echo "  ❌ git"
command -v python3 >/dev/null 2>&1 && echo "  ✅ python3" || echo "  ❌ python3"
command -v gn >/dev/null 2>&1 && echo "  ✅ gn" || echo "  ❌ gn (need depot_tools)"
command -v ninja >/dev/null 2>&1 && echo "  ✅ ninja" || echo "  ❌ ninja (need depot_tools)"
echo ""

# Git status
echo "Git Status:"
cd "$PROJECT_ROOT"
if [ -d ".git" ]; then
    echo "  ✅ Git repository initialized"
    echo "  Remote: $(git remote get-url origin 2>/dev/null || echo 'not set')"
    echo "  Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
else
    echo "  ❌ Not a git repository"
fi
echo ""

# Summary
echo "=========================================="
if [ -d "$PROJECT_ROOT/source" ]; then
    echo "✅ Phase 1 Setup: COMPLETE"
    echo ""
    echo "Next steps:"
    echo "  1. Build: ./scripts/compile.sh"
    echo "  2. Or manual:"
    echo "     cd source && gn gen ../out/Release && ninja -C ../out/Release chrome"
else
    echo "⚠️  Phase 1 Setup: PARTIAL"
    echo ""
    echo "Next steps:"
    echo "  1. Initialize: ./scripts/init-thorium.sh"
    echo "  2. Then build: ./scripts/compile.sh"
fi
echo ""
