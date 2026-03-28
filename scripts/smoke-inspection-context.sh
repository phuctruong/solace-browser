#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Inspection Context Smoke Test ==="

echo "[1/6] Checking inspection-context panel source artifact..."
test -f "specs/solace-dev/diagrams/inspection-context-panel.prime-mermaid.md"
echo "  -> OK: inspection-context diagram exists"

echo "[2/6] Checking native panel wiring..."
grep -q 'dev-inspection-context-card' "solace-hub/src/index.html"
grep -q 'dev-context-source-pill' "solace-hub/src/index.html"
grep -q 'Inspection Context' "solace-hub/src/index.html"
echo "  -> OK: inspection-context panel exists in the workspace"

echo "[3/6] Checking copy-link affordance..."
grep -q '__solaceCopyInspectionLink' "solace-hub/src/hub-app.js"
grep -q 'dev-copy-link-btn' "solace-hub/src/hub-app.js"
grep -q 'dev-context-link' "solace-hub/src/hub-app.js"
echo "  -> OK: copy-link affordance exists"

echo "[4/6] Checking honest source visibility..."
grep -q "'deep-link'" "solace-hub/src/hub-app.js"
grep -q "'restored'" "solace-hub/src/hub-app.js"
grep -q "'selected'" "solace-hub/src/hub-app.js"
grep -q "'fallback'" "solace-hub/src/hub-app.js"
grep -q "'invalid'" "solace-hub/src/hub-app.js"
grep -q "Requested deep link was invalid" "solace-hub/src/hub-app.js"
echo "  -> OK: source and invalid/fallback messaging are explicit"

echo "[5/6] Checking invalid deep-link path labels the context honestly..."
grep -q "invalidDeepLink ? 'invalid' : (staleSelection ? 'fallback' : 'selected')" "solace-hub/src/hub-app.js"
echo "  -> OK: invalid deep-link fallback is not mislabeled as a normal selection"

echo "[6/6] Checking prior deep-link regression path..."
bash "scripts/smoke-deep-link-inspection.sh" >/dev/null
echo "  -> OK: deep-link inspection smoke still passes"

echo "=== INSPECTION CONTEXT SMOKE TEST COMPLETE ==="
