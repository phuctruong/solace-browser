#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_specialist_execution_visibility.py"
diagram="$root/specs/solace-dev/diagrams/specialist-execution-activity.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-specialist-execution-activity-card" "$html"
rg -Fq "Specialist Execution Activity" "$html"
rg -Fq "updateSpecialistExecutionActivity" "$js"
rg -Fq "Running" "$js"
rg -Fq "Paused" "$js"
rg -Fq "Failed" "$js"
rg -Fq "Running Packet:" "$js"
rg -Fq "First Output Signal:" "$js"
rg -Fq "Activity Hash:" "$js"
rg -Fq "Active Observability Constraints:" "$js"
rg -Fq "Evaluation Limit:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "Execution Basis:" "$js"
rg -Fq "btoa(log.state + log.specialist + log.firstOutput)" "$js"

echo "smoke-specialist-execution-activity: ok"
