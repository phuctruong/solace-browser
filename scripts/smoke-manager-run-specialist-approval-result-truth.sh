#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-approval-result-truth.sh
set -e

echo "=== SAC85 Smoke: Manager Run Specialist Approval Result Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Approval Mutation Result:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC85 approval mutation result block"
    exit 1
fi
echo "[PASS] SAC85 approval mutation result block exists"

if ! grep -q "__solaceLastWorkflowSignoffActionResult =" "$HUB_JS"; then
    echo "[FAIL] Missing approval mutation result tracker"
    exit 1
fi
echo "[PASS] Approval mutation result tracker exists"

if ! grep -q "Result Target Role:" "$HUB_JS"; then
    echo "[FAIL] Missing result target role context"
    exit 1
fi
echo "[PASS] Result target role context exists"

if ! grep -q "Result Target Run ID:" "$HUB_JS"; then
    echo "[FAIL] Missing result target run context"
    exit 1
fi
echo "[PASS] Result target run context exists"

if ! grep -q "Exact launched-workflow approval result tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact approval result truth state"
    exit 1
fi
echo "[PASS] Exact approval result truth state exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-approval-result-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC85 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC85 Prime Mermaid artifact exists"

echo "=== SAC85 Smoke COMPLETE: all checks passed ==="
exit 0
