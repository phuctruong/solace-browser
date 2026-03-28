#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

html="solace-hub/src/index.html"
js="solace-hub/src/hub-app.js"
diagram="specs/solace-dev/diagrams/department-memory-queue.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$diagram"

rg -Fq "dev-department-memory-queue-card" "$html"
rg -Fq "Department Memory Queue" "$html"

rg -Fq "updateDepartmentMemoryQueue" "$js"
rg -Fq "PROMOTED" "$js"
rg -Fq "PENDING REVIEW" "$js"
rg -Fq "BLOCKED" "$js"
rg -Fq "Candidate:" "$js"
rg -Fq "Review Basis:" "$js"
rg -Fq "Active Queue Context:" "$js"
rg -Fq "Viewer Role:" "$js"
rg -Fq "Queue Basis:" "$js"
rg -Fq "Promotion Basis:" "$js"

echo "smoke-department-memory-queue: ok"
