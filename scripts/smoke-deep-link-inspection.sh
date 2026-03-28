#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Deep-Link Inspection Smoke Test ==="

echo "[1/6] Checking deep-link source diagram..."
test -f "specs/solace-dev/diagrams/deep-link-inspection.prime-mermaid.md"
echo "  -> OK: deep-link diagram exists"

echo "[2/6] Checking URL-backed inspection context..."
grep -q 'parseInspectionHash' "solace-hub/src/hub-app.js"
grep -q 'setInspectionHash' "solace-hub/src/hub-app.js"
grep -q '#inspect=' "solace-hub/src/hub-app.js"
echo "  -> OK: URL-backed inspection context exists"

echo "[3/6] Checking explicit precedence rule in code..."
grep -q 'var hashContext = parseInspectionHash()' "solace-hub/src/hub-app.js"
grep -q "var stored = hashContext || loadSelectedRun()" "solace-hub/src/hub-app.js"
grep -q "var storedSource = hashContext ? 'deep-link' : 'restored'" "solace-hub/src/hub-app.js"
echo "  -> OK: URL context has explicit precedence"

echo "[4/6] Checking honest deep-link fallback..."
grep -q 'prependInvalidDeepLinkNotice' "solace-hub/src/hub-app.js"
grep -q 'deep link invalid' "solace-hub/src/hub-app.js"
grep -q 'Falling back to <code>' "solace-hub/src/hub-app.js"
echo "  -> OK: invalid deep-link fallback exists"

echo "[5/6] Checking selection writes hash..."
grep -q 'setInspectionHash(appId, runId)' "solace-hub/src/hub-app.js"
grep -q 'history.replaceState' "solace-hub/src/hub-app.js"
echo "  -> OK: selection writes URL-backed context"

echo "[6/6] Checking prior selected-run persistence regressions..."
bash "scripts/smoke-selected-run-persistence.sh" >/dev/null
echo "  -> OK: selected-run persistence smoke still passes"

echo "=== DEEP-LINK INSPECTION SMOKE TEST COMPLETE ==="
