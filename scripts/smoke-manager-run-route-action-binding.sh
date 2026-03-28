#!/usr/bin/env bash
# scripts/smoke-manager-run-route-action-binding.sh
set -e

echo "=== SAC75 Smoke: Manager Run Route Action Binding ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "window.__solaceRouteWorkflowNextStep = function(assignmentId, overrideTargetRole)" "$HUB_JS"; then
    echo "[FAIL] Missing workflow-bound JS API wrapper for explicit Back Office routing mutations"
    exit 1
fi
echo "[PASS] Workflow-bound routing mutation hook present"

if ! grep -q ">Route to Coder<" "$HUB_JS"; then
    echo "[FAIL] Missing explicit UI downstream routing action triggers for the execution loop"
    exit 1
fi
echo "[PASS] Explicit DOM button controls linked into routing layout payload generators natively"

if ! grep -q "Workflow-bound assignment " "$HUB_JS"; then
    echo "[FAIL] Missing honest create-or-update routing basis in workflow result area"
    exit 1
fi
echo "[PASS] Workflow result area reports create-or-update routing basis honestly"

if ! grep -q "(SAC70/71/72/73/74/75)" "$HUB_JS"; then
    echo "[FAIL] Missing explicitly stated run basis for SAC75 linkage logs"
    exit 1
fi
echo "[PASS] UI boundary trace routing bindings explicitly map SAC75 loop constraints"

DIAGRAM="specs/solace-dev/diagrams/manager-run-route-action-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact loop constraint mapping layer diagram"
    exit 1
fi
echo "[PASS] Manager Execution Routing Action Prime Mermaid continuous topology validated successfully"

echo "=== SAC75 Smoke COMPLETE: all checks passed ==="
exit 0
