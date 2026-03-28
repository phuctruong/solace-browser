#!/usr/bin/env bash
# SAC50 Smoke Path: Specialist Convention Rollout
# Verifies the physical deployment execution binding moving signoff actions into terminal realization.
set -euo pipefail

echo "=== SAC50 Smoke: Specialist Convention Rollout Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-rollout-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-rollout-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionRollout" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionRollout" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionRollout(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three rollout states are present
grep -q "Live" solace-hub/src/hub-app.js && \
  grep -q "Staged" solace-hub/src/hub-app.js && \
  grep -q "Aborted" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Live / Staged / Aborted" || \
  { echo "[FAIL] One or more rollout states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + actionLineage + executionVerdict)
grep -q "btoa(entry.state + entry.actionLineage + entry.executionVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active rollout context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Rollout Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active rollout context present" || \
  { echo "[FAIL] Active rollout context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-rollout.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC50 Smoke COMPLETE: all checks passed ==="
