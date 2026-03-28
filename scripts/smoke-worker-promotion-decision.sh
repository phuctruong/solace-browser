#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/worker-promotion-decision.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-promotion-decision-card" "$html"
rg -Fq "Promotion Decision Ticket" "$html"

rg -Fq "updatePromotionDecisionState" "$js"
rg -Fq "Manager Decision:" "$js"
rg -Fq "Candidate:" "$js"
rg -Fq "Evidence Basis:" "$js"
rg -Fq "Approval Basis:" "$js"
rg -Fq "Active Packet Context:" "$js"
rg -Fq "Packet Binding:" "$js"
rg -Fq "Decision Basis:" "$js"
rg -Fq "approved" "$js"
rg -Fq "pending" "$js"
rg -Fq "blocked" "$js"

echo "smoke-worker-promotion-decision: ok"
