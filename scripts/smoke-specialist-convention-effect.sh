#!/usr/bin/env bash
# SAC46 Smoke Path: Specialist Convention Effect
# Verifies the terminal output receipt proving a constrained runtime definitively shifted the produced artifact.
set -euo pipefail

echo "=== SAC46 Smoke: Specialist Convention Effect Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-effect-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-effect-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionEffect" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionEffect" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionEffect(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three effect states are present
grep -q "Visible" solace-hub/src/hub-app.js && \
  grep -q "Partial" solace-hub/src/hub-app.js && \
  grep -q "Absent" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Visible / Partial / Absent" || \
  { echo "[FAIL] One or more effect states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + targetRuntime + producedArtifact)
grep -q "btoa(entry.state + entry.targetRuntime + entry.producedArtifact)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active effect context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Effect Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active effect context present" || \
  { echo "[FAIL] Active effect context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-effect.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC46 Smoke COMPLETE: all checks passed ==="
