#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_specialist_intake_readiness_visibility.py"
diagram="$root/specs/solace-dev/diagrams/specialist-intake-readiness.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-specialist-intake-readiness-card" "$html"
rg -Fq "Specialist Intake Readiness" "$html"
rg -Fq "updateSpecialistIntakeReadiness" "$js"
rg -Fq "Ready" "$js"
rg -Fq "Queued" "$js"
rg -Fq "Blocked" "$js"
rg -Fq "Intake Packet:" "$js"
rg -Fq "Execution Trace:" "$js"
rg -Fq "Readiness Hash:" "$js"
rg -Fq "Active Execution Constraints:" "$js"
rg -Fq "Evaluation Limit:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "Execution Basis:" "$js"
rg -Fq "btoa(log.state + log.specialist + log.activePacket)" "$js"

echo "smoke-specialist-intake-readiness: ok"
