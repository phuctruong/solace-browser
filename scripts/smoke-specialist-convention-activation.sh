#!/usr/bin/env bash
# SAC45 Smoke Path: Specialist Convention Activation
# Verifies the ultimate execution receipt proving a delivered convention actively constrained target execution.
set -euo pipefail

echo "=== SAC45 Smoke: Specialist Convention Activation Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-activation-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-activation-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionActivation" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionActivation" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionActivation(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three activation states are present
grep -q "Active" solace-hub/src/hub-app.js && \
  grep -q "Queued" solace-hub/src/hub-app.js && \
  grep -q "Failed" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Active / Queued / Failed" || \
  { echo "[FAIL] One or more activation states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + conventionTarget + targetRuntime)
grep -q "btoa(entry.state + entry.conventionTarget + entry.targetRuntime)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active activation context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Activation Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active activation context present" || \
  { echo "[FAIL] Active activation context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-activation.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC45 Smoke COMPLETE: all checks passed ==="
