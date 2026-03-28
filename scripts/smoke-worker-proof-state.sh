#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-proof-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-proof-state-card" "$html"
rg -q "Transparency & Proof State" "$html"

rg -q "updateWorkerProofState" "$js"
rg -q "Active Proof Context:" "$js"
rg -q "Proof Basis:" "$js"
rg -q "Transparency Basis:" "$js"
rg -q "proven" "$js"
rg -q "partial" "$js"
rg -q "missing" "$js"
rg -q "Evidence Present:" "$js"
rg -q "Unproven / Missing Elements:" "$js"

echo "smoke-worker-proof-state: ok"
