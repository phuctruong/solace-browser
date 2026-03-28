#!/usr/bin/env bash
# SAC48 Smoke Path: Specialist Convention Trust
# Verifies the governance decision proving verified artifact lineages are definitively released or blocked.
set -euo pipefail

echo "=== SAC48 Smoke: Specialist Convention Trust Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-trust-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-trust-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionTrust" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionTrust" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionTrust(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three trust states are present
grep -q "Trusted" solace-hub/src/hub-app.js && \
  grep -q "Provisional" solace-hub/src/hub-app.js && \
  grep -q "Blocked" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Trusted / Provisional / Blocked" || \
  { echo "[FAIL] One or more trust states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + verdictLineage + decisionVerdict)
grep -q "btoa(entry.state + entry.verdictLineage + entry.decisionVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active trust context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Trust Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active trust context present" || \
  { echo "[FAIL] Active trust context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-trust.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC48 Smoke COMPLETE: all checks passed ==="
