#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Worker Assignment Packet Smoke Test ==="

echo "[1/6] Checking worker assignment source artifact..."
test -f "specs/solace-dev/diagrams/worker-assignment-packet.prime-mermaid.md"
echo "  -> OK: worker assignment diagram exists"

echo "[2/6] Checking native assignment packet panel..."
grep -q 'dev-worker-assignment-packet-card' "solace-hub/src/index.html"
grep -q 'Worker Assignment Packet' "solace-hub/src/index.html"
grep -q 'dev-worker-assignment-packet' "solace-hub/src/index.html"
echo "  -> OK: assignment packet panel exists in the workspace"

echo "[3/6] Checking active assignment context..."
grep -q 'updateWorkerAssignmentPacket(appId, runId)' "solace-hub/src/hub-app.js"
grep -q 'Active Assignment Context:' "solace-hub/src/hub-app.js"
grep -q 'Packet Basis:' "solace-hub/src/hub-app.js"
grep -q 'Outbox Root:' "solace-hub/src/hub-app.js"
echo "  -> OK: assignment packet is tied to active app/run context"

echo "[4/6] Checking task, scope lock, and evidence contract..."
grep -q 'Task Statement / Objective:' "solace-hub/src/hub-app.js"
grep -q 'Scope Change Policy:' "solace-hub/src/hub-app.js"
grep -q 'FAIL_AND_NEW_TASK' "solace-hub/src/hub-app.js"
grep -q 'Evidence Contract (Required Output):' "solace-hub/src/hub-app.js"
echo "  -> OK: assignment contract fields are visible"

echo "[5/6] Checking role-specific evidence surfaces..."
grep -q 'manager-to-design-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'design-to-coder-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'coder-to-qa-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'qa-signoffs record' "solace-hub/src/hub-app.js"
echo "  -> OK: role-specific assignment evidence remains visible"

echo "[6/6] Checking prior inbox/outbox regressions..."
bash "scripts/smoke-worker-inbox-outbox.sh" >/dev/null
echo "  -> OK: inbox/outbox smoke still passes"

echo "=== WORKER ASSIGNMENT PACKET SMOKE TEST COMPLETE ==="
