#!/usr/bin/env bash
# scripts/smoke-manager-run-artifact-binding.sh
set -e

echo "=== SAC71 Smoke: Manager Run Artifact Binding ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "get('/api/v1/apps/' + boundRun.appId + '/runs')" "$HUB_JS"; then
    echo "[FAIL] Missing run endpoints fetching loop in bind mapping"
    exit 1
fi
echo "[PASS] Native runs artifact API call mapped"

if ! grep -q "/artifact/report.html" "$HUB_JS"; then
    echo "[FAIL] Missing direct link binding to report.html logic"
    exit 1
fi
echo "[PASS] Explicit URL link generator to final report detected"

if ! grep -q "/runs/' + boundRun.runId + '/events" "$HUB_JS"; then
    echo "[FAIL] Missing direct link binding to events API logic"
    exit 1
fi
echo "[PASS] Explicit URL link generator to events API detected"

if ! grep -q "/artifact/events.jsonl" "$HUB_JS"; then
    echo "[FAIL] Missing direct link binding to events artifact file logic"
    exit 1
fi
echo "[PASS] Explicit URL link generator to events artifact file detected"

if ! grep -q "(SAC70/71)" "$HUB_JS"; then
    echo "[FAIL] Missing explicitly stated run basis for SAC71 linkage logs"
    exit 1
fi
echo "[PASS] UI explicitly boundaries trace context locally"

DIAGRAM="specs/solace-dev/diagrams/manager-run-artifact-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact diagram"
    exit 1
fi
echo "[PASS] Manager Execution Artifact Linkage Prime Mermaid artifact present"

echo "=== SAC71 Smoke COMPLETE: all checks passed ==="
exit 0
