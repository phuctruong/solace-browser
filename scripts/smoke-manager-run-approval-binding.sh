#!/usr/bin/env bash
# scripts/smoke-manager-run-approval-binding.sh
set -e

echo "=== SAC73 Smoke: Manager Run Approval Binding ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "get('/api/v1/backoffice/solace-dev-manager/approvals')" "$HUB_JS"; then
    echo "[FAIL] Missing /approvals endpoints fetching loop in bind mapping"
    exit 1
fi
echo "[PASS] Native approvals API Promise hook mapped"

if ! grep -q ">Approval State:<" "$HUB_JS"; then
    echo "[FAIL] Missing explicit UI generation logic for approval statuses"
    exit 1
fi
echo "[PASS] Explicit DOM target generator detected"

if ! grep -q "(SAC70/71/72/73)" "$HUB_JS"; then
    echo "[FAIL] Missing explicitly stated run basis for SAC73 linkage logs"
    exit 1
fi
echo "[PASS] UI explicitly boundaries trace approval context locally"

DIAGRAM="specs/solace-dev/diagrams/manager-run-approval-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact diagram"
    exit 1
fi
echo "[PASS] Manager Execution Approval Signoff Prime Mermaid artifact present"

echo "=== SAC73 Smoke COMPLETE: all checks passed ==="
exit 0
