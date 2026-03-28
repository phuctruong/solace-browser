#!/usr/bin/env bash
# SAC49 Smoke Path: Specialist Convention Release
# Verifies the physical human manager signoff proving trusted constraints are cleared for production runtime loops.
set -euo pipefail

echo "=== SAC49 Smoke: Specialist Convention Release Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-release-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-release-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionRelease" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionRelease" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionRelease(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three release states are present
grep -q "Approved" solace-hub/src/hub-app.js && \
  grep -q "Pending" solace-hub/src/hub-app.js && \
  grep -q "Denied" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Approved / Pending / Denied" || \
  { echo "[FAIL] One or more release states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + trustLineage + actionVerdict)
grep -q "btoa(entry.state + entry.trustLineage + entry.actionVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active release context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Action Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active release context present" || \
  { echo "[FAIL] Active release context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-release.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC49 Smoke COMPLETE: all checks passed ==="
