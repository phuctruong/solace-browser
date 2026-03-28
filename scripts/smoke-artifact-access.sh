#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Artifact Access Smoke Test ==="

echo "[1/6] Checking artifact-access source diagram..."
test -f "specs/solace-dev/diagrams/artifact-access-flow.prime-mermaid.md"
echo "  -> OK: artifact-access diagram exists"

echo "[2/6] Checking runtime artifact route..."
grep -q '/api/v1/apps/:app_id/runs/:run_id/artifact/:filename' "solace-runtime/src/routes/apps.rs"
grep -q 'serve_run_artifact' "solace-runtime/src/routes/apps.rs"
grep -q 'ALLOWED_ARTIFACTS' "solace-runtime/src/routes/apps.rs"
echo "  -> OK: runtime artifact route exists"

echo "[3/6] Checking whitelist coverage..."
grep -q '"report.html"' "solace-runtime/src/routes/apps.rs"
grep -q '"payload.json"' "solace-runtime/src/routes/apps.rs"
grep -q '"stillwater.json"' "solace-runtime/src/routes/apps.rs"
grep -q '"ripple.json"' "solace-runtime/src/routes/apps.rs"
grep -q '"events.jsonl"' "solace-runtime/src/routes/apps.rs"
echo "  -> OK: whitelist covers core artifacts"

echo "[4/6] Checking Hub artifact links..."
grep -q '/artifact/' "solace-hub/src/hub-app.js"
grep -q 'report.html' "solace-hub/src/hub-app.js"
grep -q 'payload.json' "solace-hub/src/hub-app.js"
grep -q 'stillwater.json' "solace-hub/src/hub-app.js"
grep -q 'events.jsonl' "solace-hub/src/hub-app.js"
echo "  -> OK: Hub links to first-class artifact routes"

echo "[5/6] Checking old fake routes are gone..."
if grep -q '/reports/' "solace-hub/src/hub-app.js"; then
  echo "  -> FAIL: stale /reports/ route still present"
  exit 1
fi
if grep -q 'not exposed as first-class' "solace-hub/src/hub-app.js"; then
  echo "  -> FAIL: stale disclaimer still present"
  exit 1
fi
echo "  -> OK: stale fake routes/disclaimers are gone"

echo "[6/6] Checking prior durable-state regressions..."
bash "scripts/smoke-durable-run-state.sh" >/dev/null
echo "  -> OK: durable run-state smoke still passes"

echo "=== ARTIFACT ACCESS SMOKE TEST COMPLETE ==="
