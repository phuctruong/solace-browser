#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-drift-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -q "dev-worker-drift-state-card" "$html"
rg -q "Drift & Adaptive Replay" "$html"

rg -q "updateWorkerDriftState" "$js"
rg -q "Active Drift Context:" "$js"
rg -q "Replay Basis:" "$js"
rg -q "Drift Basis:" "$js"
rg -q "safe_replay" "$js"
rg -q "drift_detected" "$js"
rg -q "fallback_to_discover" "$js"
rg -q "Observed Deviation:" "$js"
rg -q "System Adaptation:" "$js"

echo "smoke-worker-drift-state: ok"
