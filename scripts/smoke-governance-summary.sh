#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/governance-summary.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-governance-summary-card" "$html"
rg -Fq "Governance Overview" "$html"

rg -Fq "updateGovernanceSummary" "$js"
rg -Fq "approved:" "$js"
rg -Fq "pending:" "$js"
rg -Fq "blocked:" "$js"
rg -Fq "pressureLane:" "$js"
rg -Fq "pressureLabel:" "$js"
rg -Fq "pressureDesc:" "$js"
rg -Fq "Active Governance Context:" "$js"
rg -Fq "Governance Tracking:" "$js"
rg -Fq "Pressure Basis:" "$js"
rg -Fq "Evidence Standard:" "$js"

echo "smoke-governance-summary: ok"
