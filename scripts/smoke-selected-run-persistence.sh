#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Selected Run Persistence Smoke Test ==="

echo "[1/6] Checking selected-run persistence source diagram..."
test -f "specs/solace-dev/diagrams/selected-run-persistence.prime-mermaid.md"
echo "  -> OK: selected-run persistence diagram exists"

echo "[2/6] Checking persisted selection storage..."
grep -q 'SELECTED_RUN_KEY' "solace-hub/src/hub-app.js"
grep -q 'sessionStorage.setItem' "solace-hub/src/hub-app.js"
grep -q 'sessionStorage.getItem' "solace-hub/src/hub-app.js"
echo "  -> OK: selected-run storage exists"

echo "[3/6] Checking honest restore path..."
grep -q 'restoreSelectedRun' "solace-hub/src/hub-app.js"
grep -q "storedRow.querySelector('.sat10-select-run')" "solace-hub/src/hub-app.js"
grep -q "reportExists ? 'exists' : null" "solace-hub/src/hub-app.js"
echo "  -> OK: restore path uses honest row metadata"

echo "[4/6] Checking stale-selection fallback..."
grep -q 'prependStaleFallbackNotice' "solace-hub/src/hub-app.js"
grep -q 'fallback:' "solace-hub/src/hub-app.js"
grep -q 'no longer in the runs list' "solace-hub/src/hub-app.js"
echo "  -> OK: stale-selection fallback exists"

echo "[5/6] Checking hydration prefers stored selection..."
grep -q 'var hashContext = parseInspectionHash()' "solace-hub/src/hub-app.js"
grep -q "var stored = hashContext || loadSelectedRun()" "solace-hub/src/hub-app.js"
grep -q 'if (stored && inspectionPanel)' "solace-hub/src/hub-app.js"
grep -q 'restoreSelectedRun(stored.appId, stored.runId, storedRow, storedSource)' "solace-hub/src/hub-app.js"
echo "  -> OK: hydration restores stored selection first"

echo "[6/6] Checking prior run-selection regressions..."
bash "scripts/smoke-run-selection.sh" >/dev/null
echo "  -> OK: run-selection smoke still passes"

echo "=== SELECTED RUN PERSISTENCE SMOKE TEST COMPLETE ==="
