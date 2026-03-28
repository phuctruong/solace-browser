#!/usr/bin/env bash
# SAC56 Smoke Path: Specialist Post-Release Recovery
# Verifies system explicit gating of re-entry vectors exiting quarantine.
set -euo pipefail

echo "=== SAC56 Smoke: Specialist Post-Release Recovery Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-recovery-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-recovery-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseRecovery" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseRecovery" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseRecovery(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three recovery authorization states are present
grep -q "Authorized" solace-hub/src/hub-app.js && \
  grep -q "Staged Recovery" solace-hub/src/hub-app.js && \
  grep -q "Blocked" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Authorized / Staged Recovery / Blocked" || \
  { echo "[FAIL] One or more recovery states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + controlLineage + recoveryVerdict)
grep -q "btoa(entry.state + entry.controlLineage + entry.recoveryVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Recovery Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active recovery context present" || \
  { echo "[FAIL] Active recovery context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-recovery.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC56 Smoke COMPLETE: all checks passed ==="
