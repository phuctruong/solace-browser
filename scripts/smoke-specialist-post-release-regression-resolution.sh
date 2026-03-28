#!/usr/bin/env bash
# SAC60 Smoke Path: Specialist Post-Release Regression Resolution
# Verifies system explicitly surfaces how it exits physical relapse loops.
set -euo pipefail

echo "=== SAC60 Smoke: Specialist Post-Release Regression Resolution Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-regression-resolution-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-regression-resolution-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseRegressionResolution" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseRegressionResolution" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseRegressionResolution(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three regression resolution states are present
grep -q "Resolved After Mitigation" solace-hub/src/hub-app.js && \
  grep -q "Staged Recovery Reopened" solace-hub/src/hub-app.js && \
  grep -q "Architecture Reset Required" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Resolved After Mitigation / Staged Recovery Reopened / Architecture Reset Required" || \
  { echo "[FAIL] One or more regression resolution states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + responseLineage + resolutionVerdict)
grep -q "btoa(entry.state + entry.responseLineage + entry.resolutionVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active regression-resolution context is visible
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Resolution Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active regression-resolution context present" || \
  { echo "[FAIL] Active regression-resolution context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-regression-resolution.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC60 Smoke COMPLETE: all checks passed ==="
