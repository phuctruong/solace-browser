#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_specialist_execution_evidence_visibility.py"
diagram="$root/specs/solace-dev/diagrams/specialist-execution-evidence.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-specialist-execution-evidence-card" "$html"
rg -Fq "Specialist Execution Evidence" "$html"
rg -Fq "updateSpecialistExecutionEvidence" "$js"
rg -Fq "Streaming" "$js"
rg -Fq "Stalled" "$js"
rg -Fq "Terminated" "$js"
rg -Fq "Source Packet:" "$js"
rg -Fq "Evidence Hash:" "$js"
rg -Fq "Audit Constraints:" "$js"
rg -Fq "Evidence Basis:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "btoa(log.state + log.specialist + log.logLines[0])" "$js"

echo "smoke-specialist-execution-evidence: ok"
