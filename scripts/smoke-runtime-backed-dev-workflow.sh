#!/usr/bin/env bash
# scripts/smoke-runtime-backed-dev-workflow.sh
set -e

echo "=== SAC66 Smoke: Runtime-Backed Dev Workflow ==="

# Check scripts
if [ ! -f "scripts/seed-saz66-runtime-binding.sh" ]; then
    echo "[FAIL] Missing seed script"
    exit 1
fi
echo "[PASS] Seed script present"

# Check JS modifications
HUB_JS="solace-hub/src/hub-app.js"
if ! grep -q "/api/v1/backoffice/solace-dev-manager/assignments" "$HUB_JS"; then
    echo "[FAIL] hub-app.js missing assignments endpoint fetch"
    exit 1
fi
echo "[PASS] Hub JS fetches assignments from Back Office"

if ! grep -q "/api/v1/backoffice/solace-dev-manager/requests" "$HUB_JS"; then
    echo "[FAIL] hub-app.js missing requests endpoint fetch"
    exit 1
fi
echo "[PASS] Hub JS fetches requests from Back Office"

if ! grep -q "runtime-backed dynamic API (SAC66)" "$HUB_JS"; then
    echo "[FAIL] Hub JS missing basis flag"
    exit 1
fi
echo "[PASS] Hub JS explicitly demarcates runtime vs fallback"

if ! grep -q "/api/v1/backoffice/solace-dev-manager/artifacts" "$HUB_JS"; then
    echo "[FAIL] hub-app.js missing artifacts endpoint fetch"
    exit 1
fi
echo "[PASS] Hub JS fetches assignment-linked artifacts from Back Office"

if ! grep -q "/api/v1/backoffice/solace-dev-manager/approvals" "$HUB_JS"; then
    echo "[FAIL] hub-app.js missing approvals endpoint fetch"
    exit 1
fi
echo "[PASS] Hub JS fetches assignment-linked approvals from Back Office"

# Check diagram
DIAGRAM="specs/solace-dev/diagrams/runtime-backed-dev-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid diagram"
    exit 1
fi
echo "[PASS] Prime Mermaid diagram present"

echo "=== SAC66 Smoke COMPLETE: all checks passed ==="
exit 0
