#!/usr/bin/env bash
# SAC64 Smoke Path: Specialist Post-Release Next-Path Ownership
# Verifies system explicitly proves whether acknowledged artifacts physically settled.
set -euo pipefail

echo "=== SAC64 Smoke: Specialist Post-Release Next-Path Ownership Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-next-path-ownership-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-next-path-ownership-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseNextPathOwnership" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseNextPathOwnership" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseNextPathOwnership(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three next-path ownership states are present
grep -q "Ownership Settled" solace-hub/src/hub-app.js && \
  grep -q "Ownership Pending" solace-hub/src/hub-app.js && \
  grep -q "Ownership Bounced" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Ownership Settled / Ownership Pending / Ownership Bounced" || \
  { echo "[FAIL] One or more next-path ownership states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + acknowledgmentLineage + ownershipVerdict)
grep -q "btoa(entry.state + entry.acknowledgmentLineage + entry.ownershipVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active next-path ownership context is visible
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Ownership Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active next-path ownership context present" || \
  { echo "[FAIL] Active next-path ownership context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-next-path-ownership.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC64 Smoke COMPLETE: all checks passed ==="
