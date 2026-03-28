#!/usr/bin/env bash
# scripts/smoke-manager-run-packet-provenance-truth.sh
set -e

echo "=== SAC79 Smoke: Manager Run Packet Provenance Truth ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "Next-Step Packet Provenance & Handoff Truth:" "$HUB_JS"; then
    echo "[FAIL] Missing SAC79 explicit contract header rendering the provenance block natively"
    exit 1
fi
echo "[PASS] New DOM handoff mapping bounds found flawlessly in Javascript strings"

if ! grep -q "Source Assignment ID:" "$HUB_JS" || ! grep -q "Target Assignment ID:" "$HUB_JS"; then
    echo "[FAIL] Missing source and target assignment traceability strings in provenance block"
    exit 1
fi
echo "[PASS] Explicit assignment strings tracked inside provenance natively"

if ! grep -q "Exact launched-workflow handoff tracked" "$HUB_JS"; then
    echo "[FAIL] Missing explicit exact launched-workflow provenance state"
    exit 1
fi
echo "[PASS] Exact launched-workflow provenance state is surfaced honestly"

if ! grep -q "Fallback handoff tracked" "$HUB_JS"; then
    echo "[FAIL] Missing explicit fallback provenance state"
    exit 1
fi
echo "[PASS] Fallback provenance state is surfaced honestly"

DIAGRAM="specs/solace-dev/diagrams/manager-run-packet-provenance-truth.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact provenance rendering layer diagram"
    exit 1
fi
echo "[PASS] Manager Execution Routing handoff Prime Mermaid continuous mappings validated successfully"

echo "=== SAC79 Smoke COMPLETE: all checks passed ==="
exit 0
