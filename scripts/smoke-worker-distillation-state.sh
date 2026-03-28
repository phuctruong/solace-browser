#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-distillation-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-worker-distillation-state-card" "$html"
rg -Fq "Convention Distillation" "$html"

rg -Fq "updateWorkerDistillationState" "$js"
rg -Fq "Promotion Status:" "$js"
rg -Fq "Candidate Convention:" "$js"
rg -Fq "Distillation Basis:" "$js"
rg -Fq "Active Distillation Context:" "$js"
rg -Fq "Promotion Basis:" "$js"
rg -Fq "Evidence Basis:" "$js"
rg -Fq "promoted" "$js"
rg -Fq "pending_candidate" "$js"
rg -Fq "blocked" "$js"

echo "smoke-worker-distillation-state: ok"
