#!/usr/bin/env bash
# SAC57 Smoke Path: Specialist Post-Release Return-to-Service Verification
# Verifies system explicit gating of physical survival post-quarantine.
set -euo pipefail

echo "=== SAC57 Smoke: Specialist Post-Release Return-to-Service Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-return-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-return-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseReturn" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseReturn" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseReturn(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three return-to-service verification states are present
grep -q "Service Restored" solace-hub/src/hub-app.js && \
  grep -q "Provisional Service" solace-hub/src/hub-app.js && \
  grep -q "Re-entry Failed" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Service Restored / Provisional Service / Re-entry Failed" || \
  { echo "[FAIL] One or more return states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + recoveryLineage + serviceVerdict)
grep -q "btoa(entry.state + entry.recoveryLineage + entry.serviceVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Service Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active service context present" || \
  { echo "[FAIL] Active service context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-return.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC57 Smoke COMPLETE: all checks passed ==="
