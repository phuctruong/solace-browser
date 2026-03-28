#!/usr/bin/env bash
# scripts/smoke-manager-assignment-routing.sh
set -e

echo "=== SAC68 Smoke: Manager Assignment Routing ==="

HUB_HTML="solace-hub/src/index.html"
HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "dev-active-workflow-routing" "$HUB_HTML"; then
    echo "[FAIL] Missing active assignment routing UI card"
    exit 1
fi
echo "[PASS] Active workflow routing UI present"

if ! grep -q "__solaceRouteActiveRequest" "$HUB_JS"; then
    echo "[FAIL] Missing routing action hook"
    exit 1
fi
echo "[PASS] Native assignment routing POST hook mapped"

if ! grep -q "method = 'PUT'" "$HUB_JS"; then
    echo "[FAIL] Missing assignment activation/update path"
    exit 1
fi
echo "[PASS] Existing assignment activation path mapped"

if grep -A 20 "__solaceCreateSac67Request" "$HUB_JS" | grep -q 'target_role:.*coder'; then
    echo "[FAIL] Request creation is still hardcoding an assignment fallback"
    exit 1
fi
echo "[PASS] Automatic hardcoded coder assignment generation removed"

DIAGRAM="specs/solace-dev/diagrams/manager-routing-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid diagram"
    exit 1
fi
echo "[PASS] Manager Routing Prime Mermaid artifact present"

echo "=== SAC68 Smoke COMPLETE: all checks passed ==="
exit 0
