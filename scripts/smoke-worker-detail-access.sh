#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Worker Detail Access Smoke Test ==="

echo "[1/6] Checking worker-detail source artifact..."
test -f "specs/solace-dev/diagrams/worker-detail-access.prime-mermaid.md"
echo "  -> OK: worker-detail diagram exists"

echo "[2/6] Checking native worker-detail panel..."
grep -q 'dev-worker-detail-card' "solace-hub/src/index.html"
grep -q 'dev-worker-diagram-preview' "solace-hub/src/index.html"
grep -q 'Worker Detail' "solace-hub/src/index.html"
echo "  -> OK: worker-detail panel exists in the workspace"

echo "[3/6] Checking workspace-native diagram access..."
grep -q '__solaceShowWorkerDiagram' "solace-hub/src/hub-app.js"
grep -q 'renderWorkerDiagramPreview' "solace-hub/src/hub-app.js"
grep -q 'scrollIntoView' "solace-hub/src/hub-app.js"
echo "  -> OK: diagram access is handled in the workspace"

echo "[4/6] Checking diagram surface is not editor-only..."
grep -q 'role-stack.prime-mermaid.md' "solace-hub/src/hub-app.js"
grep -q 'browser-page-map.prime-mermaid.md' "solace-hub/src/hub-app.js"
if rg -q 'vscode://file' "solace-hub/src/hub-app.js"; then
  echo "  -> FAIL: editor-only vscode links are still present"
  exit 1
fi
echo "  -> OK: no editor-only vscode links remain"

echo "[5/6] Checking role-specific handoff visibility..."
grep -q 'manager-to-design-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'design-to-coder-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'coder-to-qa-handoff.md' "solace-hub/src/hub-app.js"
echo "  -> OK: role-specific handoff sources are surfaced"

echo "[6/6] Checking prior inspection-context regressions..."
bash "scripts/smoke-inspection-context.sh" >/dev/null
echo "  -> OK: inspection-context smoke still passes"

echo "=== WORKER DETAIL ACCESS SMOKE TEST COMPLETE ==="
