#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-approval-truth.sh
set -e

echo "=== SAC91 Smoke: Manager Run Specialist Destination Approval Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Destination Approval Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC91 destination approval truth block"
    exit 1
fi
echo "[PASS] Destination approval truth block exists"

if ! grep -q "var nestedTargetApproval = approvals.find" "$HUB_JS"; then
    echo "[FAIL] Missing nested destination approval lookup"
    exit 1
fi
echo "[PASS] Nested destination approval lookup exists"

if ! grep -q "Nested Source Request ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested source request context"
    exit 1
fi
echo "[PASS] Nested source request context exists"

if ! grep -q "Nested Source Assignment ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested source assignment context"
    exit 1
fi
echo "[PASS] Nested source assignment context exists"

if ! grep -q "Nested Source Role:" "$HUB_JS"; then
    echo "[FAIL] Missing nested source role context"
    exit 1
fi
echo "[PASS] Nested source role context exists"

if ! grep -q "Nested Source Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested source run context"
    exit 1
fi
echo "[PASS] Nested source run context exists"

if ! grep -q "Nested Target Assignment ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested target assignment context"
    exit 1
fi
echo "[PASS] Nested target assignment context exists"

if ! grep -q "Nested Approval Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested approval run context"
    exit 1
fi
echo "[PASS] Nested approval run context exists"

if ! grep -q "Exact launched-workflow destination approval tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact destination approval truth label"
    exit 1
fi
echo "[PASS] Exact destination approval truth label exists"

if ! grep -q "Awaiting destination approval truth" "$HUB_JS"; then
    echo "[FAIL] Missing honest awaiting destination approval state"
    exit 1
fi
echo "[PASS] Honest awaiting destination approval state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-approval-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] Prime Mermaid artifact exists"

echo "=== SAC91 Smoke COMPLETE: all checks passed ==="
exit 0
