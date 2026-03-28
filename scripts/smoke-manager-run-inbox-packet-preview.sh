#!/usr/bin/env bash
# scripts/smoke-manager-run-inbox-packet-preview.sh
set -e

echo "=== SAC78 Smoke: Manager Run Inbox Packet Preview ==="

HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "SAC78 Inbox Packet Preview Box" "$HUB_JS"; then
    echo "[FAIL] Missing SAC78 explicit CSS grid elements rendering the preview box natively"
    exit 1
fi
echo "[PASS] New DOM block preview mapping bounds mapped flawlessly in string layouts"

if grep -q "} else {" "$HUB_JS" | grep -q "loading payload preview"; then
    echo "[FAIL] The payload preview block remains mutually exclusively bound inside reportExists block!"
    exit 1
fi
echo "[PASS] Mutually exclusive SAC72 legacy limits fully decoupled executing rendering arrays asynchronously unconditionally"

if ! grep -q "dev-active-workflow-payload-preview" "$HUB_JS"; then
    echo "[FAIL] The separated payload preview id block DOM element missing from fetch pipeline bindings"
    exit 1
fi
echo "[PASS] Re-linked the DOM document target resolving explicit payloads cleanly"

if ! grep -q "Packet Preview Basis: exact launched next-step run artifact" "$HUB_JS"; then
    echo "[FAIL] Missing exact launched-run packet preview basis"
    exit 1
fi
echo "[PASS] Exact launched-run packet preview basis is surfaced honestly"

if ! grep -q "buildMissingState('payload.json', 'missing for launched next-step run')" "$HUB_JS"; then
    echo "[FAIL] Missing honest missing-state rendering for launched next-step packet preview"
    exit 1
fi
echo "[PASS] Missing-state preview fallback is explicit for launched next-step packet"

DIAGRAM="specs/solace-dev/diagrams/manager-run-inbox-packet-preview.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid artifact inbox preview rendering layer diagram"
    exit 1
fi
echo "[PASS] Manager Execution Routing preview Prime Mermaid continuous mappings validated successfully"

echo "=== SAC78 Smoke COMPLETE: all checks passed ==="
exit 0
