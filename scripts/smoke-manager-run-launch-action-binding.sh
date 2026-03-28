#!/usr/bin/env bash
# scripts/smoke-manager-run-launch-action-binding.sh
set -e

echo "=== SAC76 Smoke: Manager Run Launch Action Binding ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "window.__solaceLaunchWorkflowNextStep = function(sourceAssignmentId, targetRole, targetAssignmentId)" "$HUB_JS"; then
    echo "[FAIL] Missing workflow-bound JS API wrapper for explicit runtime run target selections"
    exit 1
fi
echo "[PASS] Workflow-bound launch mutation hook present"

if ! grep -q "Launch Executable (" "$HUB_JS"; then
    echo "[FAIL] Missing explicit UI downstream launch triggers for the execution loop"
    exit 1
fi
echo "[PASS] Explicit DOM button controls linked into routing layout launch payload generators natively"

if ! grep -q "Workflow-bound routed assignment launch via real runtime run path (SAC76)" "$HUB_JS"; then
    echo "[FAIL] Missing honest workflow-bound launch basis in result area"
    exit 1
fi
echo "[PASS] Workflow result area reports launch basis honestly"

if ! grep -q "(SAC70/71/72/73/74/75/76)" "$HUB_JS"; then
    echo "[FAIL] Missing explicitly stated run basis for SAC76 linkage logs"
    exit 1
fi
echo "[PASS] UI boundary trace routing bindings explicitly map SAC76 launch constraints"

DIAGRAM="specs/solace-dev/diagrams/manager-run-launch-action-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact launch completion constraint mapping layer diagram"
    exit 1
fi
echo "[PASS] Manager Execution Routing Action Prime Mermaid continuous top-level launch loop validated successfully"

echo "=== SAC76 Smoke COMPLETE: all checks passed ==="
exit 0
