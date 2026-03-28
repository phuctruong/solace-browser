#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_delegation_handoff_visibility.py"
diagram="$root/specs/solace-dev/diagrams/delegation-handoff-log.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-delegation-handoff-log-card" "$html"
rg -Fq "Delegation Handoff Log" "$html"
rg -Fq "updateDelegationHandoffLog" "$js"
rg -Fq "Accepted" "$js"
rg -Fq "Pending" "$js"
rg -Fq "Blocked" "$js"
rg -Fq "Handoff Target:" "$js"
rg -Fq "Dispatch Payload:" "$js"
rg -Fq "Handoff Hash:" "$js"
rg -Fq "Active Handoff Constraints:" "$js"
rg -Fq "Tracking Source:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "Dispatch Basis:" "$js"
rg -Fq "btoa(log.target + log.lane + log.state)" "$js"

echo "smoke-delegation-handoff-log: ok"
