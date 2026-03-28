#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/manager-directive-packet.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-manager-directive-packet-card" "$html"
rg -Fq "Manager Directive Packet" "$html"

rg -Fq "updateManagerDirectivePacket" "$js"
rg -Fq "EXECUTE PROMOTION" "$js"
rg -Fq "HALT EXECUTION" "$js"
rg -Fq "DEFER" "$js"
rg -Fq "Delegation Target:" "$js"
rg -Fq "Trigger Evidence:" "$js"
rg -Fq "Next Explicit Delegation Step:" "$js"
rg -Fq "Directive Stamp:" "$js"
rg -Fq "Active Directive Constraints:" "$js"
rg -Fq "Action Source:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "Directive Basis:" "$js"
rg -Fq "btoa(directive.target + directive.action + directive.state)" "$js"

echo "smoke-manager-directive-packet: ok"
