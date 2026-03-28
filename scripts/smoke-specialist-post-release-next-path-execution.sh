#!/usr/bin/env bash
# SAC62 Smoke Path: Specialist Post-Release Next-Path Execution
# Verifies system explicitly proves whether terminal commands executed.
set -euo pipefail

echo "=== SAC62 Smoke: Specialist Post-Release Next-Path Execution Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-next-path-execution-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-next-path-execution-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseNextPathExecution" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseNextPathExecution" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseNextPathExecution(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three next-path execution states are present
grep -q "Execution Confirmed" solace-hub/src/hub-app.js && \
  grep -q "Execution Queued" solace-hub/src/hub-app.js && \
  grep -q "Execution Blocked" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Execution Confirmed / Execution Queued / Execution Blocked" || \
  { echo "[FAIL] One or more next-path execution states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + decisionLineage + executionVerdict)
grep -q "btoa(entry.state + entry.decisionLineage + entry.executionVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active next-path execution context is visible
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Execution Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active next-path execution context present" || \
  { echo "[FAIL] Active next-path execution context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-next-path-execution.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC62 Smoke COMPLETE: all checks passed ==="
