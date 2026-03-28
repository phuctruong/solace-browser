#!/usr/bin/env bash
# Smoke path for the Solace Design role.

set -euo pipefail

echo "=== Solace Design Role Smoke Test ==="

echo "[1/5] Checking design app contract..."
test -f "data/apps/solace-design/manifest.prime-mermaid.md"
test -f "data/apps/solace-design/manifest.yaml"
test -f "data/apps/solace-design/recipe.prime-mermaid.md"
echo "  -> OK: design app source and compatibility files exist"

echo "[2/5] Checking design diagram set..."
test -f "specs/solace-dev/diagrams/browser-page-map.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/browser-ui-state-map.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/browser-component-state-map.prime-mermaid.md"
test -f "specs/solace-dev/diagrams/design-handoff-flow.prime-mermaid.md"
echo "  -> OK: design diagrams exist"

echo "[3/5] Checking manager-to-design handoff contract..."
test -f "specs/solace-dev/manager-to-design-handoff.md"
grep -q "design_handoffs" "data/apps/solace-dev-manager/manifest.yaml"
echo "  -> OK: handoff contract is wired into manager state"

echo "[4/5] Checking Hub design workspace..."
grep -q "design-workspace-card" "solace-hub/src/index.html"
grep -q "/backoffice/solace-design/design_specs" "solace-hub/src/index.html"
grep -q "/backoffice/solace-dev-manager/design_handoffs" "solace-hub/src/index.html"
echo "  -> OK: Hub points to design artifacts"

echo "[5/5] Checking backoffice registry..."
grep -q '\"solace-design\"' "solace-runtime/src/routes/backoffice.rs"
echo "  -> OK: backoffice route registry knows about solace-design"

echo "=== DESIGN SMOKE TEST COMPLETE ==="
