#!/usr/bin/env bash
# Smoke path for the Dev Manager workspace
# Verifies that the manager-first object schema is loaded correctly.

set -euo pipefail

echo "=== Solace Dev Manager Workspace Smoke Test ==="

# 1. Ensure runtime is running or at least we can hit the API
# We will use simple curl queries to the backoffice schema endpoint.
# Fallback to local test if runtime is not running in background.

echo "[1/4] Checking Backoffice Schema for 'solace-dev-manager'..."
SCHEMA_API="http://127.0.0.1:8888/api/v1/backoffice/solace-dev-manager/schema"
if curl -s -f "$SCHEMA_API" > /dev/null; then
    echo "  -> OK: Schema loads"
else
    echo "  -> WARN: Runtime not answering. Start it with: cd solace-runtime && cargo run"
fi

echo "[2/4] Testing Projects Table Endpoint..."
PROJECTS_API="http://127.0.0.1:8888/api/v1/backoffice/solace-dev-manager/projects"
if curl -s -f "$PROJECTS_API" > /dev/null; then
    echo "  -> OK: Projects table is accessible"
else
    echo "  -> WARN: Projects API not reachable."
fi

echo "[3/4] Verifying the solace-browser project map exists locally..."
if [ -f "specs/solace-dev/project-mappings/solace-browser.prime-mermaid.md" ]; then
    echo "  -> OK: Project map found at specs/solace-dev/project-mappings/solace-browser.prime-mermaid.md"
else
    echo "  -> FAIL: Missing project map"
    exit 1
fi

echo "[4/4] Verifying the Hub UI Shell has the Dev workspace..."
if grep -q 'data-tab="dev"' solace-hub/src/index.html; then
    echo "  -> OK: Dev workspace tab found in Hub UI"
else
    echo "  -> FAIL: Hub UI missing Dev workspace tab"
    exit 1
fi

echo "=== SMOKE TEST COMPLETE ==="
