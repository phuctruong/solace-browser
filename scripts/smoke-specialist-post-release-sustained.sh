#!/usr/bin/env bash
# SAC58 Smoke Path: Specialist Post-Release Sustained Service
# Verifies explicit long-term gating of post-quarantine physical survival.
set -euo pipefail

echo "=== SAC58 Smoke: Specialist Post-Release Sustained Service Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-sustained-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-sustained-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseSustained" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseSustained" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseSustained(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three sustained service validation states are present
grep -q "Stable Service" solace-hub/src/hub-app.js && \
  grep -q "Regression Watch" solace-hub/src/hub-app.js && \
  grep -q "Relapse Detected" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Stable Service / Regression Watch / Relapse Detected" || \
  { echo "[FAIL] One or more sustained service states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + returnLineage + sustainedVerdict)
grep -q "btoa(entry.state + entry.returnLineage + entry.sustainedVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Sustained Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active sustained context present" || \
  { echo "[FAIL] Active sustained context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-sustained.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC58 Smoke COMPLETE: all checks passed ==="
