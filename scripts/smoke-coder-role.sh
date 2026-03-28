#!/usr/bin/env bash
# Smoke path for the Solace Coder role.

set -euo pipefail

echo "=== Solace Coder Role Smoke Test ==="

echo "[1/6] Checking coder app contract..."
test -f "data/apps/solace-coder/manifest.prime-mermaid.md"
test -f "data/apps/solace-coder/manifest.yaml"
test -f "data/apps/solace-coder/recipe.prime-mermaid.md"
echo "  -> OK: coder app source and compatibility files exist"

echo "[2/6] Checking coder diagram set..."
test -f "specs/solace-dev/diagrams/coder-workflow.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/coder-implementation-handoff.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/coder-run-lifecycle.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/coder-artifact-flow.prime-mermaid.md"
echo "  -> OK: coder diagrams exist"

echo "[3/6] Checking design-to-coder handoff contract..."
test -f "specs/solace-dev/design-to-coder-handoff.md"
grep -q "coder_handoffs" "data/apps/solace-dev-manager/manifest.yaml"
echo "  -> OK: handoff contract is wired into manager state"

echo "[4/6] Checking Hub coder workspace..."
grep -q 'id="role-card-coder"' "solace-hub/src/index.html"
grep -q 'id="role-detail-coder"' "solace-hub/src/index.html"
grep -q "/backoffice/solace-coder/code_runs" "solace-hub/src/index.html"
grep -q "/backoffice/solace-dev-manager/coder_handoffs" "solace-hub/src/index.html"
echo "  -> OK: Hub points to coder artifacts"

echo "[5/6] Checking backoffice registry..."
grep -q '"solace-coder"' "solace-runtime/src/routes/backoffice.rs"
echo "  -> OK: backoffice route registry knows about solace-coder"

echo "[6/6] Checking design dependency is still present..."
grep -q "design_spec_refs" "specs/solace-dev/design-to-coder-handoff.md"
echo "  -> OK: coder flow is bounded by design artifacts"

echo "=== CODER SMOKE TEST COMPLETE ==="
