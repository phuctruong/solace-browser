#!/usr/bin/env bash
# SAC43 Smoke Path: Specialist Convention Invocation
# Verifies the final routing loop from reusable memory bound into next directive execution.
set -euo pipefail

echo "=== SAC43 Smoke: Specialist Convention Invocation Visibility ==="

# 1. Confirm HTML container exists
grep -q "dev-specialist-convention-invocation-card" solace-hub/src/index.html && \
  echo "[PASS] DOM card present: dev-specialist-convention-invocation-card" || \
  { echo "[FAIL] DOM card missing"; exit 1; }

# 2. Confirm JS function exists
grep -q "function updateSpecialistConventionInvocation" solace-hub/src/hub-app.js && \
  echo "[PASS] JS function present: updateSpecialistConventionInvocation" || \
  { echo "[FAIL] JS function missing"; exit 1; }

# 3. Confirm function is chained in updateWorkerDetail
grep -q "updateSpecialistConventionInvocation(appId, runId);" solace-hub/src/hub-app.js && \
  echo "[PASS] Function chained in updateWorkerDetail" || \
  { echo "[FAIL] Function not chained"; exit 1; }

# 4. Confirm all three invocation states are present
grep -q "Invoked" solace-hub/src/hub-app.js && \
  grep -q "Queued" solace-hub/src/hub-app.js && \
  grep -q "Blocked" solace-hub/src/hub-app.js && \
  echo "[PASS] Honest states present: Invoked / Queued / Blocked" || \
  { echo "[FAIL] One or more invocation states missing"; exit 1; }

# 5. Confirm ALCOA+ hash binding matches specification (state + conventionTarget + nextDirective)
grep -q "btoa(entry.state + entry.conventionTarget + entry.nextDirective)" solace-hub/src/hub-app.js && \
  echo "[PASS] ALCOA+ hash binding present" || \
  { echo "[FAIL] ALCOA+ hash missing"; exit 1; }

# 6. Confirm active invocation context is explicit
grep -q "Viewer Role:" solace-hub/src/hub-app.js && \
  grep -q "Selected Worker:" solace-hub/src/hub-app.js && \
  grep -q "Selected Run:" solace-hub/src/hub-app.js && \
  grep -q "Invocation Basis:" solace-hub/src/hub-app.js && \
  echo "[PASS] Active invocation context present" || \
  { echo "[FAIL] Active invocation context missing"; exit 1; }

# 7. Confirm Prime Mermaid diagram exists
test -f specs/solace-dev/diagrams/specialist-convention-invocation.prime-mermaid.md && \
  echo "[PASS] Prime Mermaid diagram present" || \
  { echo "[FAIL] Mermaid diagram missing"; exit 1; }

echo ""
echo "=== SAC43 Smoke COMPLETE: all checks passed ==="
