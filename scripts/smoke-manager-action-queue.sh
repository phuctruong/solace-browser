#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/manager-action-queue.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-manager-action-queue-card" "$html"
rg -Fq "Manager Action Queue" "$html"

rg -Fq "updateManagerActionQueue" "$js"
rg -Fq "priority: 'Immediate'" "$js"
rg -Fq "priority: 'Pending'" "$js"
rg -Fq "priority: 'Blocked'" "$js"
rg -Fq "candidate:" "$js"
rg -Fq "role:" "$js"
rg -Fq "reason:" "$js"
rg -Fq "Active Queue Constraints:" "$js"
rg -Fq "Display Scope:" "$js"
rg -Fq "Priority Bound:" "$js"
rg -Fq "Action Basis:" "$js"
rg -Fq "btoa(act.candidate + act.priority + act.role)" "$js"

echo "smoke-manager-action-queue: ok"
