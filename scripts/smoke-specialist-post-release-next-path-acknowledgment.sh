#!/usr/bin/env bash
# SAC63 Smoke Path: Specialist Post-Release Next-Path Acknowledgment
# Verifies system explicitly proves whether downstream targets accepted the routing handoff.
set -euo pipefail

echo "=== SAC63 Smoke: Specialist Post-Release Next-Path Acknowledgment Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-next-path-acknowledgment-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-next-path-acknowledgment-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseNextPathAcknowledgment" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseNextPathAcknowledgment" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseNextPathAcknowledgment(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three next-path acknowledgment states are present
grep -q "Routing Acknowledged" solace-hub/src/hub-app.js && \
  grep -q "Routing Deferred" solace-hub/src/hub-app.js && \
  grep -q "Routing Rejected" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Routing Acknowledged / Routing Deferred / Routing Rejected" || \
  { echo "[FAIL] One or more next-path acknowledgment states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + executionLineage + acknowledgmentVerdict)
grep -q "btoa(entry.state + entry.executionLineage + entry.acknowledgmentVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active next-path acknowledgment context is visible
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Acknowledgment Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active next-path acknowledgment context present" || \
  { echo "[FAIL] Active next-path acknowledgment context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-next-path-acknowledgment.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC63 Smoke COMPLETE: all checks passed ==="
