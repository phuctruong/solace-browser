#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/promotion-audit-trail.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-promotion-audit-trail-card" "$html"
rg -Fq "Promotion Audit Trail" "$html"

rg -Fq "updatePromotionAuditTrail" "$js"
rg -Fq "Candidate:" "$js"
rg -Fq "Transition Basis:" "$js"
rg -Fq "Audit Hash:" "$js"
rg -Fq "Active Audit Context:" "$js"
rg -Fq "Log Binding:" "$js"
rg -Fq "History Basis:" "$js"
rg -Fq "Evidence Standard:" "$js"
rg -Fq "state: 'approved'" "$js"
rg -Fq "state: 'pending'" "$js"
rg -Fq "state: 'blocked'" "$js"

echo "smoke-promotion-audit-trail: ok"
