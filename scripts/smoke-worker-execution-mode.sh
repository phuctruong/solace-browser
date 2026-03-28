#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-execution-mode.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-execution-mode-card" "$html"
rg -q "Execution Mode & Convention" "$html"

rg -q "updateWorkerExecutionMode" "$js"
rg -q "Active Execution Context:" "$js"
rg -q "Mode Basis:" "$js"
rg -q "Convention Basis:" "$js"
rg -q "DISCOVER" "$js"
rg -q "REPLAY" "$js"
rg -q "solace-dev-workspace.md" "$js"
rg -q "prime-mermaid-substrate.md" "$js"
rg -q "solace-worker-inbox-contract.md" "$js"

echo "smoke-worker-execution-mode: ok"
