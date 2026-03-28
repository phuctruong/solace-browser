#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Run Selection Smoke Test ==="

echo "[1/6] Checking run-selection source diagram..."
test -f "specs/solace-dev/diagrams/run-selection-flow.prime-mermaid.md"
echo "  -> OK: run-selection diagram exists"

echo "[2/6] Checking run-history selection controls..."
grep -q 'sat10-select-run' "solace-hub/src/hub-app.js"
grep -q '__solaceSelectRun' "solace-hub/src/hub-app.js"
echo "  -> OK: run-selection controls exist"

echo "[3/6] Checking honest selected-run metadata..."
grep -q 'data-report-exists' "solace-hub/src/hub-app.js"
grep -q 'data-events-exists' "solace-hub/src/hub-app.js"
grep -q 'clickedEl.dataset.reportExists' "solace-hub/src/hub-app.js"
echo "  -> OK: selected-run metadata is used"

echo "[4/6] Checking selected-run highlighting..."
grep -q 'highlightSelectedRun' "solace-hub/src/hub-app.js"
grep -q '● viewing' "solace-hub/src/hub-app.js"
echo "  -> OK: selected-run highlighting exists"

echo "[5/6] Checking selection updates inspection and previews..."
grep -q 'showRunInspection(appId, runId' "solace-hub/src/hub-app.js"
grep -q 'hydrateArtifactPreviews(appId, runId)' "solace-hub/src/hub-app.js"
echo "  -> OK: selection updates inspection and previews"

echo "[6/6] Checking prior artifact-preview regressions..."
bash "scripts/smoke-artifact-preview.sh" >/dev/null
echo "  -> OK: artifact-preview smoke still passes"

echo "=== RUN SELECTION SMOKE TEST COMPLETE ==="
