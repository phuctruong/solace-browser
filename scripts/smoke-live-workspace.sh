#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Live Workspace Smoke Test ==="

echo "[1/6] Checking live workspace source diagrams..."
test -f "specs/solace-dev/diagrams/live-workspace-hydration.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/run-feedback-flow.prime-mermaid.md"
echo "  -> OK: live workspace diagrams exist"

echo "[2/6] Checking hub-app hydration hooks..."
grep -q "hydrateDevWorkspace" "solace-hub/src/hub-app.js"
grep -q "hydrateHubStatus" "solace-hub/src/hub-app.js"
grep -q "hydrateRoleCard" "solace-hub/src/hub-app.js"
grep -q "/api/v1/hub/status" "solace-hub/src/hub-app.js"
grep -q "/api/v1/backoffice/" "solace-hub/src/hub-app.js"
echo "  -> OK: hub-app hydration path exists"

echo "[3/6] Checking live workspace containers..."
grep -q 'id="dev-live-status"' "solace-hub/src/index.html"
grep -q 'id="role-live-manager"' "solace-hub/src/index.html"
grep -q 'id="role-live-design"' "solace-hub/src/index.html"
grep -q 'id="role-live-coder"' "solace-hub/src/index.html"
grep -q 'id="role-live-qa"' "solace-hub/src/index.html"
echo "  -> OK: live role containers exist"

echo "[4/6] Checking live count anchors..."
grep -q 'id="live-count-manager-requests"' "solace-hub/src/index.html"
grep -q 'id="live-count-design-design_specs"' "solace-hub/src/index.html"
grep -q 'id="live-count-coder-code_runs"' "solace-hub/src/index.html"
grep -q 'id="live-count-qa-qa_runs"' "solace-hub/src/index.html"
echo "  -> OK: live count anchors exist"

echo "[5/6] Checking run feedback surface..."
grep -q 'id="dev-last-run"' "solace-hub/src/index.html"
grep -q 'id="worker-control-output"' "solace-hub/src/index.html"
grep -q 'Run completed' "solace-hub/src/hub-app.js"
grep -q 'Run failed' "solace-hub/src/hub-app.js"
echo "  -> OK: run feedback surface exists"

echo "[6/6] Checking integrated role stack regressions..."
bash "scripts/smoke-integrated-workspace.sh" >/dev/null
bash "scripts/smoke-qa-role.sh" >/dev/null
bash "scripts/smoke-coder-role.sh" >/dev/null
bash "scripts/smoke-design-role.sh" >/dev/null
echo "  -> OK: prior role stack smoke checks still pass"

echo "=== LIVE WORKSPACE SMOKE TEST COMPLETE ==="
