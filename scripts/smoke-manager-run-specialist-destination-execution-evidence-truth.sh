#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-destination-execution-evidence-truth.sh
set -e

echo "=== SAC89 Smoke: Manager Run Specialist Destination Execution Evidence Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Destination Execution Evidence Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC89 destination execution evidence truth block"
    exit 1
fi
echo "[PASS] Destination execution evidence truth block exists"

if ! grep -q "fetchArtifactText(nestedLaunchAction.appId, nestedLaunchAction.runId, 'events.jsonl')" "$HUB_JS"; then
    echo "[FAIL] Missing nested execution evidence artifact fetch"
    exit 1
fi
echo "[PASS] Nested execution evidence artifact fetch exists"

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

if ! grep -q "Nested Evidence Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing nested evidence run context"
    exit 1
fi
echo "[PASS] Nested evidence run context exists"

if ! grep -q "Exact launched-workflow destination execution evidence tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact destination execution evidence truth label"
    exit 1
fi
echo "[PASS] Exact destination execution evidence truth label exists"

if ! grep -q "Awaiting destination execution evidence" "$HUB_JS"; then
    echo "[FAIL] Missing honest awaiting destination execution evidence state"
    exit 1
fi
echo "[PASS] Honest awaiting destination execution evidence state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-destination-execution-evidence-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] Prime Mermaid artifact exists"

echo "=== SAC89 Smoke COMPLETE: all checks passed ==="
exit 0
