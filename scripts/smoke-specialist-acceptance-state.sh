#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_specialist_acceptance_visibility.py"
diagram="$root/specs/solace-dev/diagrams/specialist-acceptance-state.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-specialist-acceptance-state-card" "$html"
rg -Fq "Specialist Acceptance State" "$html"
rg -Fq "updateSpecialistAcceptanceState" "$js"
rg -Fq "Confirmed" "$js"
rg -Fq "Pending" "$js"
rg -Fq "Rejected" "$js"
rg -Fq "Bound Directive:" "$js"
rg -Fq "Inbox Trace:" "$js"
rg -Fq "Receipt Hash:" "$js"
rg -Fq "Active Acceptance Constraints:" "$js"
rg -Fq "Evaluation Limit:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "Delivery Basis:" "$js"
rg -Fq "btoa(log.state + log.directive + log.inboxTarget)" "$js"

echo "smoke-specialist-acceptance-state: ok"
