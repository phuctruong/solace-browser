#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-routing-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-routing-state-card" "$html"
rg -q "Hybrid Routing" "$html"

rg -q "updateWorkerRoutingState" "$js"
rg -q "Route Selection:" "$js"
rg -q "Cost &amp; Latency Profile:" "$js"
rg -q "Routing Justification:" "$js"
rg -q "Active Routing Context:" "$js"
rg -q "Routing Basis:" "$js"
rg -q "Cost Basis:" "$js"
rg -q "replay" "$js"
rg -q "deterministic" "$js"
rg -q "local_model" "$js"
rg -q "external_api" "$js"

echo "smoke-worker-routing-state: ok"
