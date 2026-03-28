#!/usr/bin/env bash
# SAC47 Smoke Path: Specialist Convention Proof
# Verifies the governing evidence verdict proving constrained artifacts pass structural bounds.
set -euo pipefail

echo "=== SAC47 Smoke: Specialist Convention Proof Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-proof-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-proof-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionProof" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionProof" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionProof(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three proof states are present
grep -q "Verified" solace-hub/src/hub-app.js && \
  grep -q "Partial" solace-hub/src/hub-app.js && \
  grep -q "Missing" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Verified / Partial / Missing" || \
  { echo "[FAIL] One or more proof states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + producedArtifact + proofStrategy)
grep -q "btoa(entry.state + entry.producedArtifact + entry.proofStrategy)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active proof context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Proof Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active proof context present" || \
  { echo "[FAIL] Active proof context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-proof.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC47 Smoke COMPLETE: all checks passed ==="
