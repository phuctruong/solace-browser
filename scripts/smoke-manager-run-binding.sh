#!/usr/bin/env bash
# scripts/smoke-manager-run-binding.sh
set -e

echo "=== SAC70 Smoke: Manager Run Binding ==="

HUB_HTML="solace-hub/src/index.html"
HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "dev-active-workflow-result" "$HUB_HTML"; then
    echo "[FAIL] Missing active assignment run binding UI card in DOM"
    exit 1
fi
echo "[PASS] Active workflow run binding result UI framework present"

if ! grep -q "hydrateActiveWorkflowResult" "$HUB_JS"; then
    echo "[FAIL] Missing run binding rendering function hook"
    exit 1
fi
echo "[PASS] Native run binding evaluation function mapped"

if ! grep -q "saveWorkflowLaunchBinding" "$HUB_JS"; then
    echo "[FAIL] Missing explicit workflow launch binding persistence"
    exit 1
fi
echo "[PASS] Workflow launch binding persistence present"

if ! grep -q "Run execution explicitly bound to workflow launch session state (SAC70)" "$HUB_JS"; then
    echo "[FAIL] Explicit workflow launch binding basis missing from UI string payload"
    exit 1
fi
echo "[PASS] UI explicitly bounds workflow launch execution contexts"

if ! grep -q "Fallback to selected run only; not durable workflow launch proof" "$HUB_JS"; then
    echo "[FAIL] Missing honest fallback basis for non-launch-bound selected runs"
    exit 1
fi
echo "[PASS] Honest fallback basis present"

DIAGRAM="specs/solace-dev/diagrams/manager-run-binding-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid binding artifact diagram"
    exit 1
fi
echo "[PASS] Manager Execution Result Binding Prime Mermaid artifact present"

echo "=== SAC70 Smoke COMPLETE: all checks passed ==="
exit 0
