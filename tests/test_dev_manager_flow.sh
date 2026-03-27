#!/usr/bin/env bash
# Automated narrow verification script for Dev Manager configuration

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR/.."

echo "Running Dev Manager Artifact & Config Checks..."

# 1. Check PM diagrams
echo "Checking Prime Mermaid mappings..."
test -f specs/solace-dev/manager-source-map.md
test -f specs/solace-dev/diagrams/dev-role-map.prime-mermaid.md
test -f specs/solace-dev/diagrams/dev-manager-flow.prime-mermaid.md
test -f specs/solace-dev/project-mappings/solace-browser.prime-mermaid.md
test -f data/apps/solace-dev-manager/manifest.prime-mermaid.md
echo "-> Diagrams OK."

# 2. Check Backoffice code integration
echo "Checking Backoffice config..."
test -f data/apps/solace-dev-manager/manifest.yaml
grep -q "solace-dev-manager" solace-runtime/src/routes/backoffice.rs || { echo "solace-dev-manager not found in backoffice.rs"; exit 1; }
grep -q "find_app_dir(app_id)" solace-runtime/src/routes/backoffice.rs || { echo "app discovery is not wired through find_app_dir"; exit 1; }
echo "-> Config OK."

# 3. Check worker app contract
echo "Checking worker app contract..."
python -m pytest -q tests/test_dev_manager_contract.py
echo "-> Worker app contract OK."

# 4. Check Hub HTML
echo "Checking Hub UI..."
grep -q "Dev Workspace" solace-hub/src/index.html || { echo "Dev Workspace tab not found in Hub index.html"; exit 1; }
grep -q "solace-dev-manager/requests" solace-hub/src/index.html || { echo "Requests link not found in Hub index.html"; exit 1; }
echo "-> Hub UI OK."

echo "All narrow verification checks passed!"
exit 0
