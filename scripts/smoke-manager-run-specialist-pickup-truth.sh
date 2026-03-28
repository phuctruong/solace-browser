#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-pickup-truth.sh
set -e

echo "=== SAC80 Smoke: Manager Run Specialist Pickup Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Specialist Pickup Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC80 pickup truth block"
    exit 1
fi
echo "[PASS] SAC80 pickup truth block exists"

if ! grep -q "Exact launched-workflow pickup tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact launched-workflow pickup truth state"
    exit 1
fi
echo "[PASS] Exact pickup truth state exists"

if ! grep -q "Fallback pickup tracked" "$HUB_JS"; then
    echo "[FAIL] Missing fallback pickup truth state"
    exit 1
fi
echo "[PASS] Fallback pickup truth state exists"

if ! grep -q "Awaiting specialist pickup evidence" "$HUB_JS"; then
    echo "[FAIL] Missing pending pickup truth state"
    exit 1
fi
echo "[PASS] Pending pickup truth state exists"

if ! grep -q "request, assignment, role, and run remain aligned" "$HUB_JS"; then
    echo "[FAIL] Missing exact pickup basis language"
    exit 1
fi
echo "[PASS] Exact pickup basis language exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-pickup-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC80 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC80 Prime Mermaid artifact exists"

echo "=== SAC80 Smoke COMPLETE: all checks passed ==="
exit 0
