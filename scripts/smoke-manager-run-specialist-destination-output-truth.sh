#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-output-truth.sh
set -e

echo "=== SAC90 Smoke: Manager Run Specialist Destination Output Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Destination Output Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC90 destination output truth block"
    exit 1
fi
echo "[PASS] Destination output truth block exists"

if ! grep -q "fetchArtifactText(nestedLaunchAction.appId, nestedLaunchAction.runId, 'report.html')" "$HUB_JS"; then
    echo "[FAIL] Missing nested output artifact fetch"
    exit 1
fi
echo "[PASS] Nested output artifact fetch exists"

if ! grep -q "nestedLaunchMatchesCurrentBranch" "$HUB_JS"; then
    echo "[FAIL] Missing exact nested branch gate"
    exit 1
fi
echo "[PASS] Exact nested branch gate exists"

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

if ! grep -q "Nested Output Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested output run context"
    exit 1
fi
echo "[PASS] Nested output run context exists"

if ! grep -q "Exact launched-workflow destination output tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact destination output truth label"
    exit 1
fi
echo "[PASS] Exact destination output truth label exists"

if ! grep -q "Awaiting destination output truth" "$HUB_JS"; then
    echo "[FAIL] Missing honest awaiting destination output state"
    exit 1
fi
echo "[PASS] Honest awaiting destination output state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-output-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] Prime Mermaid artifact exists"

echo "=== SAC90 Smoke COMPLETE: all checks passed ==="
exit 0
