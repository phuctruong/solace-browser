#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_specialist_artifact_provenance_visibility.py"
diagram="$root/specs/solace-dev/diagrams/specialist-artifact-provenance.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-specialist-artifact-provenance-card" "$html"
rg -Fq "Specialist Artifact Provenance" "$html"
rg -Fq "updateSpecialistArtifactProvenance" "$js"
rg -Fq "integrity: 'Verified'" "$js"
rg -Fq "integrity: 'Partial'" "$js"
rg -Fq "integrity: 'Invalid'" "$js"
rg -Fq "origin:" "$js"
rg -Fq "checks:" "$js"
rg -Fq "hash-match" "$js"
rg -Fq "hash-mismatch" "$js"
rg -Fq "'missing'" "$js"
rg -Fq "Provenance Hash:" "$js"
rg -Fq "Audit Constraints:" "$js"
rg -Fq "Provenance Basis:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "btoa(entry.integrity + entry.bundleId + entry.origin)" "$js"

echo "smoke-specialist-artifact-provenance: ok"
