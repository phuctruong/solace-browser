#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-efficiency-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-worker-efficiency-state-card" "$html"
rg -Fq "Efficiency Metrics" "$html"

rg -Fq "updateWorkerEfficiencyState" "$js"
rg -Fq "System Economics Profile:" "$js"
rg -Fq "Replay Rate:" "$js"
rg -Fq "Compute Economics:" "$js"
rg -Fq "Execution Latency:" "$js"
rg -Fq "Active Efficiency Context:" "$js"
rg -Fq "Efficiency Basis:" "$js"
rg -Fq "Latency Basis:" "$js"
rg -Fq "Replay Heavy" "$js"
rg -Fq "Discover Heavy (Ripple)" "$js"
rg -Fq "Mixed (Local + Replay)" "$js"

echo "smoke-worker-efficiency-state: ok"
