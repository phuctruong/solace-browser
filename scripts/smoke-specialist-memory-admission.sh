#!/usr/bin/env bash
# SAM40 Smoke Path: Specialist Memory Admission
# Verifies the final workspace load → memory-admission inspection path.
set -euo pipefail

echo "=== SAM40 Smoke: Specialist Memory Admission Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-memory-admission-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-memory-admission-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistMemoryAdmission" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistMemoryAdmission" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistMemoryAdmission(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three admission states are present
grep -q "Admitted" solace-hub/src/hub-app.js && \
  grep -q "Queued" solace-hub/src/hub-app.js && \
  grep -q "Rejected" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Admitted / Queued / Rejected" || \
  { echo "[FAIL] One or more admission states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (status + bundleId + targetMemory)
grep -q "btoa(token.status + token.bundleId + token.targetMemory)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active admission context exists
grep -q "Audit Constraints:" solace-hub/src/hub-app.js && \
  grep -q "Admission Basis:" solace-hub/src/hub-app.js && \
  grep -q "Resolution Bound:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active admission context present" || \
  { echo "[FAIL] Active admission context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-memory-admission.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAM40 Smoke COMPLETE: all checks passed ==="
