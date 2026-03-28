#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-convention-store.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-convention-store-card" "$html"
rg -q "Convention Store Binding" "$html"

rg -q "updateWorkerConventionStore" "$js"
rg -q "Active Convention Context:" "$js"
rg -q "Convention Basis:" "$js"
rg -q "Replay Basis:" "$js"
rg -q "replayable" "$js"
rg -q "discover_only" "$js"
rg -q "partial" "$js"
rg -q "Store Ring:" "$js"
rg -q "Active Convention:" "$js"

echo "smoke-worker-convention-store: ok"
