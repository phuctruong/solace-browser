#!/usr/bin/env bash
# SAC42 Smoke Path: Specialist Memory Reuse
# Verifies the final loop from memory entry bound back into callable context.
set -euo pipefail

echo "=== SAC42 Smoke: Specialist Memory Reuse Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-memory-reuse-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-memory-reuse-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistMemoryReuse" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistMemoryReuse" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistMemoryReuse(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three reuse states are present
grep -q "Callable" solace-hub/src/hub-app.js && \
  grep -q "Limited" solace-hub/src/hub-app.js && \
  grep -q "Blocked" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Callable / Limited / Blocked" || \
  { echo "[FAIL] One or more reuse states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + memoryId + nextTarget)
grep -q "btoa(entry.state + entry.memoryId + entry.nextTarget)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active reuse context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Reuse Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active reuse context present" || \
  { echo "[FAIL] Active reuse context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-memory-reuse.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC42 Smoke COMPLETE: all checks passed ==="
