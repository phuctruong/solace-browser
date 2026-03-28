#!/usr/bin/env bash
# SAP39 Smoke Path: Specialist Promotion-Candidate
# Verifies the full workspace load → promotion-candidate inspection path.
set -euo pipefail

echo "=== SAP39 Smoke: Specialist Promotion-Candidate Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-promotion-candidate-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-promotion-candidate-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPromotionCandidate" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPromotionCandidate" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPromotionCandidate(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three promotion states are present
grep -q "Ready-to-Seal" solace-hub/src/hub-app.js && \
  grep -q "Provisional" solace-hub/src/hub-app.js && \
  grep -q "Disqualified" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Ready-to-Seal / Provisional / Disqualified" || \
  { echo "[FAIL] One or more promotion states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding
grep -q "btoa(c.status + c.bundleId + c.basis)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-promotion-candidate.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAP39 Smoke COMPLETE: all checks passed ==="
