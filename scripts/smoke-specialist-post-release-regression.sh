#!/usr/bin/env bash
# SAC59 Smoke Path: Specialist Post-Release Regression Response
# Verifies system explicitly surfaces what it does when restored services relapse.
set -euo pipefail

echo "=== SAC59 Smoke: Specialist Post-Release Regression Response Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-regression-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-regression-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseRegression" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseRegression" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseRegression(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three regression response states are present
grep -q "Rollback Triggered" solace-hub/src/hub-app.js && \
  grep -q "Live Mitigation" solace-hub/src/hub-app.js && \
  grep -q "Containment Escalated" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Rollback Triggered / Live Mitigation / Containment Escalated" || \
  { echo "[FAIL] One or more regression response states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + regressionLineage + responseVerdict)
grep -q "btoa(entry.state + entry.regressionLineage + entry.responseVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Response Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active response context present" || \
  { echo "[FAIL] Active response context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-regression.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC59 Smoke COMPLETE: all checks passed ==="
