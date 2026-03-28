#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-evidence-truth.sh
set -e

echo "=== SAC81 Smoke: Manager Run Specialist Evidence Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Specialist Execution Evidence Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC81 execution evidence truth block"
    exit 1
fi
echo "[PASS] SAC81 execution evidence block exists"

if ! grep -q "dev-active-workflow-evidence-preview" "$HUB_JS"; then
    echo "[FAIL] Missing execution evidence preview target"
    exit 1
fi
echo "[PASS] Execution evidence preview target exists"

if ! grep -q "Exact launched-workflow execution evidence tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact execution evidence truth state"
    exit 1
fi
echo "[PASS] Exact execution evidence truth state exists"

if ! grep -q "Fallback execution evidence tracked" "$HUB_JS"; then
    echo "[FAIL] Missing fallback execution evidence truth state"
    exit 1
fi
echo "[PASS] Fallback execution evidence truth state exists"

if ! grep -q "Awaiting specialist execution evidence" "$HUB_JS"; then
    echo "[FAIL] Missing pending execution evidence truth state"
    exit 1
fi
echo "[PASS] Pending execution evidence truth state exists"

if ! grep -q "request, assignment, role, and run remain aligned" "$HUB_JS"; then
    echo "[FAIL] Missing exact execution evidence basis language"
    exit 1
fi
echo "[PASS] Exact execution evidence basis language exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-evidence-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC81 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC81 Prime Mermaid artifact exists"

echo "=== SAC81 Smoke COMPLETE: all checks passed ==="
exit 0
