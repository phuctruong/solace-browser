#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-approval-truth.sh
set -e

echo "=== SAC83 Smoke: Manager Run Specialist Approval Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Specialist Approval Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC83 approval truth block"
    exit 1
fi
echo "[PASS] SAC83 approval truth block exists"

if ! grep -q "dev-active-workflow-approval-preview" "$HUB_JS"; then
    echo "[FAIL] Missing approval preview target"
    exit 1
fi
echo "[PASS] Approval preview target exists"

if ! grep -q "Exact launched-workflow approval branch tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact approval truth state"
    exit 1
fi
echo "[PASS] Exact approval truth state exists"

if ! grep -q "Fallback approval branch tracked" "$HUB_JS"; then
    echo "[FAIL] Missing fallback approval truth state"
    exit 1
fi
echo "[PASS] Fallback approval truth state exists"

if ! grep -q "request, assignment, role, and run remain aligned" "$HUB_JS"; then
    echo "[FAIL] Missing exact approval basis language"
    exit 1
fi
echo "[PASS] Exact approval basis language exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-approval-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC83 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC83 Prime Mermaid artifact exists"

echo "=== SAC83 Smoke COMPLETE: all checks passed ==="
exit 0
