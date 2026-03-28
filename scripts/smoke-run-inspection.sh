#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Run Inspection Smoke Test ==="

echo "[1/6] Checking run inspection source diagram..."
test -f "specs/solace-dev/diagrams/run-inspection-flow.prime-mermaid.md"
echo "  -> OK: run inspection diagram exists"

echo "[2/6] Checking run inspection hooks in hub-app..."
grep -q "extractRunId" "solace-hub/src/hub-app.js"
grep -q "fetchRunEvents" "solace-hub/src/hub-app.js"
grep -q "showRunInspection" "solace-hub/src/hub-app.js"
grep -q "/api/v1/apps/' + appId + '/runs/' + runId + '/events" "solace-hub/src/hub-app.js"
echo "  -> OK: hub-app inspection hooks exist"

echo "[3/6] Checking real inspection routes..."
grep -q 'route("/apps/:app_id/runs/:run_id", get(run_detail_page))' "solace-runtime/src/routes/files.rs"
grep -q '/api/v1/apps/:app_id/runs/:run_id/events' "solace-runtime/src/routes/apps.rs"
grep -q 'get_run_events' "solace-runtime/src/routes/apps.rs"
grep -q '/api/v1/apps/' "solace-hub/src/hub-app.js"
grep -q '/report' "solace-hub/src/hub-app.js"
echo "  -> OK: inspection routes are real"

echo "[4/6] Checking run inspection surface in Hub..."
grep -q 'id="dev-run-inspection"' "solace-hub/src/index.html"
grep -q 'id="dev-last-run"' "solace-hub/src/index.html"
grep -q 'worker-control-output' "solace-hub/src/index.html"
echo "  -> OK: Hub inspection containers exist"

echo "[5/6] Checking honest artifact boundary..."
grep -q 'payload.json and stillwater.json are not exposed as first-class Hub routes yet' "solace-hub/src/hub-app.js"
echo "  -> OK: artifact boundary is stated honestly"

echo "[6/6] Checking prior live workspace regressions..."
bash "scripts/smoke-live-workspace.sh" >/dev/null
echo "  -> OK: live workspace smoke still passes"

echo "=== RUN INSPECTION SMOKE TEST COMPLETE ==="
