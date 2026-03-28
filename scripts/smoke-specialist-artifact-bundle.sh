#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
html="$root/solace-hub/src/index.html"
js="$root/solace-hub/src/hub-app.js"
test_file="$root/tests/test_specialist_artifact_bundle_visibility.py"
diagram="$root/specs/solace-dev/diagrams/specialist-artifact-bundle.prime-mermaid.md"

test -f "$html"
test -f "$js"
test -f "$test_file"
test -f "$diagram"

rg -Fq "dev-specialist-artifact-bundle-card" "$html"
rg -Fq "Specialist Artifact Bundle" "$html"
rg -Fq "updateSpecialistArtifactBundle" "$js"
rg -Fq "state: 'Open'" "$js"
rg -Fq "state: 'Sealed'" "$js"
rg -Fq "Partial" "$js"
rg -Fq "bundleId:" "$js"
rg -Fq "sourcePacket:" "$js"
rg -Fq "artifacts:" "$js"
rg -Fq "Bundle Hash:" "$js"
rg -Fq "Audit Constraints:" "$js"
rg -Fq "Artifact Basis:" "$js"
rg -Fq "Resolution Bound:" "$js"
rg -Fq "btoa(bundle.state + bundle.bundleId + bundle.specialist)" "$js"

echo "smoke-specialist-artifact-bundle: ok"
