#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-approval-action-truth.sh
set -e

echo "=== SAC92 Smoke: Manager Run Specialist Destination Approval Action Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Target Assignment Destination Approval Action:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC92 destination approval action block"
    exit 1
fi
echo "[PASS] Destination approval action block exists"

if ! grep -E -q "window.__solaceSignoffWorkflow.*nestedLaunchAction\.targetAssignmentId" "$HUB_JS"; then
    echo "[FAIL] Missing nested destination approval action wiring"
    exit 1
fi
echo "[PASS] Nested destination approval action wiring exists"

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

if ! grep -q "Nested Action Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested action run context"
    exit 1
fi
echo "[PASS] Nested action run context exists"

if ! grep -q "nested approval already resolved as" "$HUB_JS"; then
    echo "[FAIL] Missing resolved destination approval action lock state"
    exit 1
fi
echo "[PASS] Resolved destination approval action lock state exists"

if ! grep -q "Approval action will " "$HUB_JS"; then
    echo "[FAIL] Missing create-vs-update destination action basis"
    exit 1
fi
echo "[PASS] Create-vs-update destination action basis exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-approval-action-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] Prime Mermaid artifact exists"

echo "=== SAC92 Smoke COMPLETE: all checks passed ==="
exit 0
