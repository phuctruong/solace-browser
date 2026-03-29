#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-launch-truth.sh
set -e

echo "=== SAC87 Smoke: Manager Run Specialist Destination Launch Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Destination Launch Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC87 destination launch truth block"
    exit 1
fi
echo "[PASS] Destination launch truth block exists"

if ! grep -q "window.__solaceLastWorkflowNestedLaunchAction" "$HUB_JS"; then
    echo "[FAIL] Missing nested launch tracking state"
    exit 1
fi
echo "[PASS] Nested launch tracking state exists"

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

if ! grep -q "Nested Launched Role:" "$HUB_JS"; then
    echo "[FAIL] Missing nested launched role context"
    exit 1
fi
echo "[PASS] Nested launched role context exists"

if ! grep -q "Nested Launched Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested launched run context"
    exit 1
fi
echo "[PASS] Nested launched run context exists"

if ! grep -q "Exact launched-workflow destination launch tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact destination launch truth label"
    exit 1
fi
echo "[PASS] Exact destination launch truth label exists"

if ! grep -q "Awaiting destination launch truth" "$HUB_JS"; then
    echo "[FAIL] Missing honest awaiting destination launch state"
    exit 1
fi
echo "[PASS] Honest awaiting destination launch state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-launch-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] Prime Mermaid artifact exists"

echo "=== SAC87 Smoke COMPLETE: all checks passed ==="
exit 0
