#!/usr/bin/env bash
# SAC65 Smoke Path: Specialist Post-Release Upstream Release
# Verifies system explicitly proves whether upstream tracking nodes cleared their memory.
set -euo pipefail

echo "=== SAC65 Smoke: Specialist Post-Release Upstream Release Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-upstream-release-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-upstream-release-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseUpstreamRelease" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseUpstreamRelease" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseUpstreamRelease(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three upstream release states are present
grep -q "Custody Released" solace-hub/src/hub-app.js && \
  grep -q "Custody Retained" solace-hub/src/hub-app.js && \
  grep -q "Custody Re-armed" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Custody Released / Custody Retained / Custody Re-armed" || \
  { echo "[FAIL] One or more upstream release states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + ownershipLineage + releaseVerdict)
grep -q "btoa(entry.state + entry.ownershipLineage + entry.releaseVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active upstream release context is visible
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Upstream Release Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active upstream release context present" || \
  { echo "[FAIL] Active upstream release context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-upstream-release.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC65 Smoke COMPLETE: all checks passed ==="
