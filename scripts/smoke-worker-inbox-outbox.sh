#!/usr/bin/env bash
set -euo pipefail

echo "=== Solace Worker Inbox/Outbox Smoke Test ==="

echo "[1/6] Checking worker inbox/outbox source artifact..."
test -f "specs/solace-dev/diagrams/worker-inbox-outbox.prime-mermaid.md"
echo "  -> OK: worker inbox/outbox diagram exists"

echo "[2/6] Checking native inbox/outbox panel..."
grep -q 'dev-worker-inbox-outbox-card' "solace-hub/src/index.html"
grep -q 'Worker Inbox / Outbox Contract' "solace-hub/src/index.html"
grep -q 'dev-worker-inbox-outbox' "solace-hub/src/index.html"
echo "  -> OK: inbox/outbox panel exists in the workspace"

echo "[3/6] Checking active context wiring..."
grep -q 'updateWorkerInboxOutbox(appId, runId)' "solace-hub/src/hub-app.js"
grep -q 'Active Contract Context:' "solace-hub/src/hub-app.js"
grep -q 'Outbox Root:' "solace-hub/src/hub-app.js"
echo "  -> OK: inbox/outbox surface is tied to active app/run context"

echo "[4/6] Checking role-specific sources..."
grep -q 'manager-to-design-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'design-to-coder-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'coder-to-qa-handoff.md' "solace-hub/src/hub-app.js"
grep -q 'solace-worker-inbox-contract.md' "solace-hub/src/hub-app.js"
echo "  -> OK: role-specific inbox sources are surfaced"

echo "[5/6] Checking result surface visibility..."
grep -q 'Outbox Outputs (result surface)' "solace-hub/src/hub-app.js"
grep -q 'App Outbox / Runs' "solace-hub/src/hub-app.js"
grep -q 'qa-signoffs' "solace-hub/src/hub-app.js"
echo "  -> OK: outbox/result surface is explicit"

echo "[6/6] Checking prior worker-detail regressions..."
bash "scripts/smoke-worker-detail-access.sh" >/dev/null
echo "  -> OK: worker-detail smoke still passes"

echo "=== WORKER INBOX/OUTBOX SMOKE TEST COMPLETE ==="
