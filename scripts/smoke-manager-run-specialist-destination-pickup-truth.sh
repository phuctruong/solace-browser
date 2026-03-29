#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-pickup-truth.sh
set -e

echo "=== SAC88 Smoke: Manager Run Specialist Destination Pickup Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Destination Pickup Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC88 destination pickup truth block"
    exit 1
fi
echo "[PASS] Destination pickup truth block exists"

if ! grep -q "nestedEventsExist" "$HUB_JS"; then
    echo "[FAIL] Missing nested destination pickup event tracking"
    exit 1
fi
echo "[PASS] Nested destination pickup event tracking exists"

if ! grep -q "exactNestedLaunchTruth" "$HUB_JS"; then
    echo "[FAIL] Missing exact nested launch truth basis"
    exit 1
fi
echo "[PASS] Exact nested launch truth basis exists"

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

if ! grep -q "Exact launched-workflow destination pickup tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact destination pickup truth label"
    exit 1
fi
echo "[PASS] Exact destination pickup truth label exists"

if ! grep -q "Awaiting destination specialist pickup evidence" "$HUB_JS"; then
    echo "[FAIL] Missing honest awaiting destination pickup state"
    exit 1
fi
echo "[PASS] Honest awaiting destination pickup state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-pickup-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] Prime Mermaid artifact exists"

echo "=== SAC88 Smoke COMPLETE: all checks passed ==="
exit 0
