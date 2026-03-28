#!/usr/bin/env bash
# Smoke path for the Solace QA role.

set -euo pipefail

echo "=== Solace QA Role Smoke Test ==="

echo "[1/6] Checking QA app contract..."
test -f "data/apps/solace-qa/manifest.prime-mermaid.md"
test -f "data/apps/solace-qa/manifest.yaml"
test -f "data/apps/solace-qa/recipe.prime-mermaid.md"
echo "  -> OK: QA app source and compatibility files exist"

echo "[2/6] Checking QA diagram set..."
test -f "specs/solace-dev/diagrams/qa-workflow.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/qa-evidence-flow.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/qa-signoff-release-gate.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/qa-regression-routing.prime-mermaid.md"
echo "  -> OK: QA diagrams exist"

echo "[3/6] Checking coder-to-QA handoff contract..."
test -f "specs/solace-dev/coder-to-qa-handoff.md"
grep -q "qa_handoffs" "data/apps/solace-dev-manager/manifest.yaml"
echo "  -> OK: handoff contract is wired into manager state"

echo "[4/6] Checking Hub QA workspace..."
grep -q 'id="role-card-qa"' "solace-hub/src/index.html"
grep -q 'id="role-detail-qa"' "solace-hub/src/index.html"
grep -q "/backoffice/solace-qa/qa_runs" "solace-hub/src/index.html"
grep -q "/backoffice/solace-dev-manager/qa_handoffs" "solace-hub/src/index.html"
echo "  -> OK: Hub points to QA artifacts"

echo "[5/6] Checking backoffice registry..."
grep -q '"solace-qa"' "solace-runtime/src/routes/backoffice.rs"
echo "  -> OK: backoffice route registry knows about solace-qa"

echo "[6/6] Checking coder dependency is still present..."
grep -q "code_run_refs" "specs/solace-dev/coder-to-qa-handoff.md"
echo "  -> OK: QA flow is bounded by coder artifacts"

echo "=== QA SMOKE TEST COMPLETE ==="
