#!/usr/bin/env bash
# SAC55 Smoke Path: Specialist Post-Release Quarantine
# Verifies severe operational control matrices over escalated artifacts.
set -euo pipefail

echo "=== SAC55 Smoke: Specialist Post-Release Quarantine Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-quarantine-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-quarantine-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseQuarantine" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseQuarantine" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseQuarantine(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three control states are present
grep -q "Constrained Continuation" solace-hub/src/hub-app.js && \
  grep -q "Manual Override Required" solace-hub/src/hub-app.js && \
  grep -q "Quarantined" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Constrained Continuation / Manual Override Required / Quarantined" || \
  { echo "[FAIL] One or more quarantine states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + escalationLineage + controlVerdict)
grep -q "btoa(entry.state + entry.escalationLineage + entry.controlVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Control Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active control context present" || \
  { echo "[FAIL] Active control context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-quarantine.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC55 Smoke COMPLETE: all checks passed ==="
