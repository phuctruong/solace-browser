#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Artifact Preview Smoke Test ==="

echo "[1/6] Checking artifact-preview source diagram..."
test -f "specs/solace-dev/diagrams/artifact-preview-flow.prime-mermaid.md"
echo "  -> OK: artifact-preview diagram exists"

echo "[2/6] Checking preview card in Hub..."
grep -q 'dev-artifact-preview-card' "solace-hub/src/index.html"
grep -q 'dev-artifact-previews' "solace-hub/src/index.html"
echo "  -> OK: artifact preview card exists"

echo "[3/6] Checking preview hydration hooks..."
grep -q 'hydrateArtifactPreviews' "solace-hub/src/hub-app.js"
grep -q 'fetchArtifactText' "solace-hub/src/hub-app.js"
grep -q "showRunInspection(appId, runId" "solace-hub/src/hub-app.js"
echo "  -> OK: preview hydration hooks exist"

echo "[4/6] Checking inline preview coverage..."
grep -q 'buildPayloadPreview' "solace-hub/src/hub-app.js"
grep -q 'buildEventsPreview' "solace-hub/src/hub-app.js"
grep -q 'buildReportPreview' "solace-hub/src/hub-app.js"
echo "  -> OK: payload, events, and report previews exist"

echo "[5/6] Checking honest missing-state handling..."
grep -q 'buildMissingState' "solace-hub/src/hub-app.js"
grep -q 'r.status === 404' "solace-hub/src/hub-app.js"
grep -q 'r.status === 403' "solace-hub/src/hub-app.js"
echo "  -> OK: missing-state handling exists"

echo "[6/6] Checking prior artifact-access regressions..."
bash "scripts/smoke-artifact-access.sh" >/dev/null
echo "  -> OK: artifact-access smoke still passes"

echo "=== ARTIFACT PREVIEW SMOKE TEST COMPLETE ==="
