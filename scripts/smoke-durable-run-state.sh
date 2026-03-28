#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Durable Run State Smoke Test ==="

echo "[1/6] Checking durable run-state source diagram..."
test -f "specs/solace-dev/diagrams/durable-run-state.prime-mermaid.md"
echo "  -> OK: durable run-state diagram exists"

echo "[2/6] Checking list-runs runtime route..."
grep -q '/api/v1/apps/:app_id/runs' "solace-runtime/src/routes/apps.rs"
grep -q 'list_runs' "solace-runtime/src/routes/apps.rs"
grep -q 'outbox' "solace-runtime/src/routes/apps.rs"
echo "  -> OK: list-runs route exists"

echo "[3/6] Checking Hub run-history hydration hooks..."
grep -q 'hydrateRunHistory' "solace-hub/src/hub-app.js"
grep -q '__solaceInspectRun' "solace-hub/src/hub-app.js"
grep -q '/api/v1/apps/' "solace-hub/src/hub-app.js"
grep -q '/runs' "solace-hub/src/hub-app.js"
echo "  -> OK: durable run-state hydration hooks exist"

echo "[4/6] Checking run-history surface..."
grep -q 'id="dev-run-history-card"' "solace-hub/src/index.html"
grep -q 'id="dev-run-history"' "solace-hub/src/index.html"
grep -q 'Run History' "solace-hub/src/index.html"
grep -q 'SDI7' "solace-hub/src/index.html"
echo "  -> OK: run-history surface exists"

echo "[5/6] Checking real report/detail links..."
grep -q '/api/v1/apps/' "solace-hub/src/hub-app.js"
grep -q '/runs/' "solace-hub/src/hub-app.js"
grep -q '/report' "solace-hub/src/hub-app.js"
grep -q '/apps/' "solace-hub/src/hub-app.js"
if grep -q '/reports/' "solace-hub/src/hub-app.js"; then
  echo "  -> FAIL: stale /reports/ link still present"
  exit 1
fi
echo "  -> OK: run-history links use real runtime routes"

echo "[6/6] Checking prior run inspection regressions..."
bash "scripts/smoke-run-inspection.sh" >/dev/null
echo "  -> OK: prior run inspection smoke still passes"

echo "=== DURABLE RUN STATE SMOKE TEST COMPLETE ==="
