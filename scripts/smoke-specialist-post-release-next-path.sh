#!/usr/bin/env bash
# SAC61 Smoke Path: Specialist Post-Release Next-Path Decision
# Verifies system explicitly surfaces terminal routing commands after resolution.
set -euo pipefail

echo "=== SAC61 Smoke: Specialist Post-Release Next-Path Decision Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-next-path-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-next-path-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseNextPath" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseNextPath" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseNextPath(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three next-path commands are present
grep -q "Clean Exit" solace-hub/src/hub-app.js && \
  grep -q "Bounded Recovery Re-entry" solace-hub/src/hub-app.js && \
  grep -q "Architecture Reset Dispatch" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Clean Exit / Bounded Recovery Re-entry / Architecture Reset Dispatch" || \
  { echo "[FAIL] One or more next-path states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + resolutionLineage + nextPathVerdict)
grep -q "btoa(entry.state + entry.resolutionLineage + entry.nextPathVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active next-path context is visible
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Next-Path Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active next-path context present" || \
  { echo "[FAIL] Active next-path context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-next-path.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC61 Smoke COMPLETE: all checks passed ==="
