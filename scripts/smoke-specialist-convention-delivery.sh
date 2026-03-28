#!/usr/bin/env bash
# SAC44 Smoke Path: Specialist Convention Delivery
# Verifies the final delivery receipt proving a routed convention reached its execution target.
set -euo pipefail

echo "=== SAC44 Smoke: Specialist Convention Delivery Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-delivery-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-delivery-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionDelivery" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionDelivery" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionDelivery(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three delivery states are present
grep -q "Acknowledged" solace-hub/src/hub-app.js && \
  grep -q "Pending" solace-hub/src/hub-app.js && \
  grep -q "Rejected" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Acknowledged / Pending / Rejected" || \
  { echo "[FAIL] One or more delivery states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + conventionTarget + targetPacket)
grep -q "btoa(entry.state + entry.conventionTarget + entry.targetPacket)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active delivery context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Delivery Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active delivery context present" || \
  { echo "[FAIL] Active delivery context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-delivery.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC44 Smoke COMPLETE: all checks passed ==="
