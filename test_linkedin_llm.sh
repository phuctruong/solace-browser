#!/bin/bash

# Test LinkedIn LLM Automation
# This script demonstrates the OpenClaw-style automation

set -e

echo "🚀 LinkedIn LLM Automation Test"
echo "================================"
echo ""
echo "This will:"
echo "  1. Open LinkedIn in visible browser"
echo "  2. Get structured ARIA snapshot (like OpenClaw)"
echo "  3. Analyze page using LLM-like logic"
echo "  4. Update your LinkedIn profile automatically"
echo "  5. Save proof artifacts"
echo ""
echo "⚠️  You may need to log in on first run"
echo "⚠️  After login, the script continues automatically"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "import playwright" 2>/dev/null || {
    echo "❌ Playwright not installed"
    echo "Installing: pip install playwright"
    pip install playwright
    playwright install chromium
}

python3 -c "import aiohttp" 2>/dev/null || {
    echo "❌ aiohttp not installed"
    echo "Installing: pip install aiohttp"
    pip install aiohttp
}

echo "✅ Dependencies OK"
echo ""

# Run automation
echo "🎬 Starting automation..."
python3 linkedin_llm_automation.py

echo ""
echo "✅ Test complete!"
echo "📁 Check artifacts/ for proof files"
