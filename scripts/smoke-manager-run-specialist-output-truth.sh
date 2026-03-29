#!/usr/bin/env bash
# scripts/smoke-manager-run-specialist-output-truth.sh
set -e

echo "=== SAC82 Smoke: Manager Run Specialist Output Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Specialist Output Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC82 output truth block"
    exit 1
fi
echo "[PASS] SAC82 output truth block exists"

if ! grep -q "dev-output-fetch-target" "$HUB_JS"; then
    echo "[FAIL] Missing output preview target"
    exit 1
fi
echo "[PASS] Output preview target exists"

if ! grep -q "Exact launched-workflow output tracked" "$HUB_JS"; then
    echo "[FAIL] Missing exact output truth state"
    exit 1
fi
echo "[PASS] Exact output truth state exists"

if ! grep -q "Fallback output tracked" "$HUB_JS"; then
    echo "[FAIL] Missing fallback output truth state"
    exit 1
fi
echo "[PASS] Fallback output truth state exists"

if ! grep -q "Awaiting specialist output truth" "$HUB_JS"; then
    echo "[FAIL] Missing pending output truth state"
    exit 1
fi
echo "[PASS] Pending output truth state exists"

if ! grep -q "request, assignment, role, and run remain aligned" "$HUB_JS"; then
    echo "[FAIL] Missing exact output basis language"
    exit 1
fi
echo "[PASS] Exact output basis language exists"

DIAGRAM="specs/solace-dev/diagrams/manager-run-specialist-output-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing SAC82 Prime Mermaid artifact"
    exit 1
fi
echo "[PASS] SAC82 Prime Mermaid artifact exists"

echo "=== SAC82 Smoke COMPLETE: all checks passed ==="
exit 0
