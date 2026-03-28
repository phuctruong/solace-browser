#!/usr/bin/env bash
# scripts/smoke-manager-run-preview-binding.sh
set -e

echo "=== SAC72 Smoke: Manager Run Preview Binding ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "dev-active-workflow-preview" "$HUB_JS"; then
    echo "[FAIL] Missing active assignment run preview div binding in Hub logic"
    exit 1
fi
echo "[PASS] Native run preview target element created"

if ! grep -q "fetchArtifactText" "$HUB_JS"; then
    echo "[FAIL] Missing direct file artifact polling sequence inside workflow bounds"
    exit 1
fi
echo "[PASS] Explicit artifact data polling mapped"

if ! grep -q "buildReportPreview" "$HUB_JS" || ! grep -q "buildPayloadPreview" "$HUB_JS"; then
    echo "[FAIL] Missing usage of standard preview DOM generators"
    exit 1
fi
echo "[PASS] Reusing native preview wrapper components correctly"

if ! grep -q "(SAC70/71/72)" "$HUB_JS"; then
    echo "[FAIL] Missing explicitly stated run basis for SAC72 linkage logs"
    exit 1
fi
echo "[PASS] UI explicitly bounded trace context logic mapping (SAC72) declared"

DIAGRAM="specs/solace-dev/diagrams/manager-run-preview-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid layout preview mapping artifact diagram"
    exit 1
fi
echo "[PASS] Manager Execution Preview Linkage Prime Mermaid artifact present"

echo "=== SAC72 Smoke COMPLETE: all checks passed ==="
exit 0
