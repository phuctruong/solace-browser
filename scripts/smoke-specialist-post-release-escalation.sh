#!/usr/bin/env bash
# SAC54 Smoke Path: Specialist Post-Release Escalation
# Verifies operational tracking loop capturing failed closures.
set -euo pipefail

echo "=== SAC54 Smoke: Specialist Post-Release Escalation Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-post-release-escalation-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-post-release-escalation-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistPostReleaseEscalation" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistPostReleaseEscalation" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistPostReleaseEscalation(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three escalation states are present
grep -q "Reopened" solace-hub/src/hub-app.js && \
  grep -q "Escalated" solace-hub/src/hub-app.js && \
  grep -q "Under Observation" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Reopened / Escalated / Under Observation" || \
  { echo "[FAIL] One or more escalation states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + closureLineage + escalationVerdict)
grep -q "btoa(entry.state + entry.closureLineage + entry.escalationVerdict)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm explicit active context is present
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Escalation Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active escalation context present" || \
  { echo "[FAIL] Active escalation context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-post-release-escalation.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC54 Smoke COMPLETE: all checks passed ==="
