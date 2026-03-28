#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-graph-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-graph-state-card" "$html"
rg -q "Execution Graph Trace" "$html"

rg -q "updateWorkerGraphState" "$js"
rg -q "Active Graph Context:" "$js"
rg -q "Graph Basis:" "$js"
rg -q "Path Basis:" "$js"
rg -q "PLANNER &rarr; ROUTER" "$js"
rg -q "UNKNOWN_GRAPH" "$js"
rg -q "Active Node Context" "$js"

echo "smoke-worker-graph-state: ok"
