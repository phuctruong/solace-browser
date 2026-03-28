#!/usr/bin/env bash
# SAC51 Smoke Path: Specialist Post-Release Health
# Verifies the ongoing telemetry binding resolving deployed assets into continuous operational states.
set -euo pipefail

echo "=== SAC51 Smoke: Specialist Post-Release Health Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-health-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-health-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseHealth" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseHealth" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseHealth(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three health states are present
grep -q "Healthy" solace-hub/src/hub-app.js && \
  grep -q "Degraded" solace-hub/src/hub-app.js && \
  grep -q "Rolled Back" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Healthy / Degraded / Rolled Back" || \
  { echo "[FAIL] One or more health states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + rolloutLineage + postReleaseVerdict)
grep -q "btoa(entry.state + entry.rolloutLineage + entry.postReleaseVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active post-release context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Health Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active post-release context present" || \
  { echo "[FAIL] Active post-release context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-health.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC51 Smoke COMPLETE: all checks passed ==="
