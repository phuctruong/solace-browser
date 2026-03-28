#!/usr/bin/env bash
# SAC41 Smoke Path: Specialist Memory Entry
# Verifies the final workspace load → memory object inspection path.
set -euo pipefail

echo "=== SAC41 Smoke: Specialist Memory Entry Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-memory-entry-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-memory-entry-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistMemoryEntry" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistMemoryEntry" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistMemoryEntry(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three entry states are present
grep -q "Live" solace-hub/src/hub-app.js && \
  grep -q "Draft" solace-hub/src/hub-app.js && \
  grep -q "Revoked" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Live / Draft / Revoked" || \
  { echo "[FAIL] One or more entry states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + bundleId + conventionTarget)
grep -q "btoa(entry.state + entry.bundleId + entry.conventionTarget)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active memory-entry context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Memory Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active memory-entry context present" || \
  { echo "[FAIL] Active memory-entry context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-memory-entry.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC41 Smoke COMPLETE: all checks passed ==="
