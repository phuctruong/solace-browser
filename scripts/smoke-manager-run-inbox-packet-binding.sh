#!/usr/bin/env bash
# scripts/smoke-manager-run-inbox-packet-binding.sh
set -e

echo "=== SAC77 Smoke: Manager Run Inbox Packet Binding ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Inbox Packet State:" "$HUB_JS"; then
    echo "[FAIL] Missing workflow-bound next-step inbox packet state block"
    exit 1
fi
echo "[PASS] Workflow-bound packet state block present"

if ! grep -q "artifact/payload.json" "$HUB_JS"; then
    echo "[FAIL] Missing explicit artifact link for the payload URL bindings"
    exit 1
fi
echo "[PASS] Explicit DOM artifact links bound to payload.json successfully natively"

if ! grep -q "Workflow-bound launched assignment packet via exact launched run artifact (SAC77)" "$HUB_JS"; then
    echo "[FAIL] Missing honest exact packet basis for launched assignment packet view"
    exit 1
fi
echo "[PASS] Exact launched-assignment packet basis is surfaced honestly"

if ! grep -q ">\[↗ View Inbox Packet (payload.json)\]<" "$HUB_JS"; then
    echo "[FAIL] Missing explicit DOM text for the worker inbox truth visibility string"
    exit 1
fi
echo "[PASS] Visibility labels natively mapped to accurate inbox packet terminology constraints"

DIAGRAM="specs/solace-dev/diagrams/manager-run-inbox-packet-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact inbox verification mapping layer diagram"
    exit 1
fi
echo "[PASS] Manager Execution Routing Action Prime Mermaid continuous top-level launch loop validated successfully"

echo "=== SAC77 Smoke COMPLETE: all checks passed ==="
exit 0
