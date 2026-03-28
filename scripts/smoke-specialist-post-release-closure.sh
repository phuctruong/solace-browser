#!/usr/bin/env bash
# SAC53 Smoke Path: Specialist Post-Release Closure
# Verifies remediation closure tracking binding active operations to verified outcomes.
set -euo pipefail

echo "=== SAC53 Smoke: Specialist Post-Release Closure Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-closure-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-closure-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseClosure" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseClosure" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseClosure(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three closure states are present
grep -q "Verified Closed" solace-hub/src/hub-app.js && \
  grep -q "Pending Verification" solace-hub/src/hub-app.js && \
  grep -q "Failed Verification" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Verified Closed / Pending / Failed" || \
  { echo "[FAIL] One or more closure states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + incidentLineage + closureVerdict)
grep -q "btoa(entry.state + entry.incidentLineage + entry.closureVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Closure Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active closure context present" || \
  { echo "[FAIL] Active closure context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-closure.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC53 Smoke COMPLETE: all checks passed ==="
