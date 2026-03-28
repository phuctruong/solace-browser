#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-human-gate.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-human-gate-card" "$html"
rg -q "Human-in-the-Loop Gate" "$html"

rg -q "updateWorkerHumanGate" "$js"
rg -q "Active Human Gate Context:" "$js"
rg -q "Gate Basis:" "$js"
rg -q "Intervention Basis:" "$js"
rg -q "not_yet_at_gate" "$js"
rg -q "awaiting_human" "$js"
rg -q "intervention_required" "$js"
rg -q "approved" "$js"
rg -q "Review & Approve" "$js"

echo "smoke-worker-human-gate: ok"
