#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Integrated Dev Workspace Smoke Test ==="

echo "[1/6] Checking integrated workspace source diagrams..."
test -f "specs/solace-dev/diagrams/integrated-dev-workspace.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/worker-control-flow.prime-mermaid.md"
echo "  -> OK: integrated workspace diagrams exist"

echo "[2/6] Checking integrated Dev workspace shell..."
grep -q 'id="dev-project-header"' "solace-hub/src/index.html"
grep -q 'id="dev-role-roster"' "solace-hub/src/index.html"
grep -q 'Integrated Dev Workspace' "solace-hub/src/index.html"
echo "  -> OK: integrated workspace shell exists in Hub"

echo "[3/6] Checking four role detail panels..."
grep -q 'id="role-detail-manager"' "solace-hub/src/index.html"
grep -q 'id="role-detail-design"' "solace-hub/src/index.html"
grep -q 'id="role-detail-coder"' "solace-hub/src/index.html"
grep -q 'id="role-detail-qa"' "solace-hub/src/index.html"
echo "  -> OK: role detail panels exist"

echo "[4/6] Checking worker control path..."
grep -q 'id="dev-worker-control"' "solace-hub/src/index.html"
grep -q '__solaceRunWorker' "solace-hub/src/index.html"
grep -q '/api/v1/apps/run/' "solace-hub/src/index.html"
grep -q 'route(\"/api/v1/apps/run/:app_id\", post(run_app))' "solace-runtime/src/routes/apps.rs"
echo "  -> OK: worker control path is wired"

echo "[5/6] Checking role stack references..."
grep -q 'solace-dev-manager' "solace-hub/src/index.html"
grep -q 'solace-design' "solace-hub/src/index.html"
grep -q 'solace-coder' "solace-hub/src/index.html"
grep -q 'solace-qa' "solace-hub/src/index.html"
echo "  -> OK: integrated role stack is visible"

echo "[6/6] Checking project context anchors..."
grep -q '/backoffice/solace-dev-manager/projects' "solace-hub/src/index.html"
grep -q '/backoffice/solace-dev-manager/requests' "solace-hub/src/index.html"
grep -q '/backoffice/solace-dev-manager/assignments' "solace-hub/src/index.html"
echo "  -> OK: project context anchors exist"

echo "=== INTEGRATED WORKSPACE SMOKE TEST COMPLETE ==="
