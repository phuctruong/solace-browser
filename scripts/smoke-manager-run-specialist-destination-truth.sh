#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-truth.sh
set -e

echo "=== SAC86 Smoke: Manager Run Specialist Destination Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Destination Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC86 destination truth block"
    exit 1
fi
echo "[PASS] SAC86 destination truth block exists"

if ! grep -q "window.__solaceRouteWorkflowNextStep" "$HUB_JS"; then
    echo "[FAIL] Missing destination routing function"
    exit 1
fi
echo "[PASS] Destination routing function exists"

if ! grep -q "Source Assignment ID:" "$HUB_JS"; then
    echo "[FAIL] Missing source assignment context in destination block"
    exit 1
fi
echo "[PASS] Source assignment context exists"

if ! grep -q "Destination Mutation Mode:" "$HUB_JS"; then
    echo "[FAIL] Missing destination mutation mode"
    exit 1
fi
echo "[PASS] Destination mutation mode exists"

if ! grep -q "Exact launched-workflow destination branch tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact destination truth state"
    exit 1
fi
echo "[PASS] Exact destination truth state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC86 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC86 Prime Mermaid artifact exists"

echo "=== SAC86 Smoke COMPLETE: all checks passed ==="
exit 0
