#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-approval-action-truth.sh
set -e

echo "=== SAC84 Smoke: Manager Run Specialist Approval Action Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Approval Action:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC84 approval action block"
    exit 1
fi
echo "[PASS] SAC84 approval action block exists"

if ! grep -q "window.__solaceSignoffWorkflow" "$HUB_JS"; then
    echo "[FAIL] Missing approval action mutation function"
    exit 1
fi
echo "[PASS] Approval action mutation function exists"

if ! grep -q "Action Target Assignment ID:" "$HUB_JS"; then
    echo "[FAIL] Missing action target assignment context"
    exit 1
fi
echo "[PASS] Action target assignment context exists"

if ! grep -q "Action Target Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing action target run context"
    exit 1
fi
echo "[PASS] Action target run context exists"

if ! grep -q "Approval action will " "$HUB_JS"; then
    echo "[FAIL] Missing approval action basis language"
    exit 1
fi
echo "[PASS] Approval action basis language exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-approval-action-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC84 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC84 Prime Mermaid artifact exists"

echo "=== SAC84 Smoke COMPLETE: all checks passed ==="
exit 0
