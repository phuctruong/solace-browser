#!/usr/bin/env bash
# scripts/smoke-manager-request-creation.sh
set -e

echo "=== SAC67 Smoke: Manager Request Creation & Selection ==="

HUB_HTML="solace-hub/src/index.html"
HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "dev-active-workflow-card" "$HUB_HTML"; then
    echo "[FAIL] Missing active workflow UI card"
    exit 1
fi
echo "[PASS] Active workflow select UI present"

if ! grep -q "__solaceCreateSac67Request" "$HUB_JS"; then
    echo "[FAIL] Missing request creation hook"
    exit 1
fi
echo "[PASS] Native request creation POST hook mapped"

if ! grep -q "/api/v1/backoffice/solace-dev-manager/projects" "$HUB_JS"; then
    echo "[FAIL] Missing on-demand project creation path"
    exit 1
fi
echo "[PASS] Native project bootstrap path mapped"

if ! grep -q "window.__solaceActiveRequestId" "$HUB_JS"; then
    echo "[FAIL] Missing selected request state variable"
    exit 1
fi
echo "[PASS] Explicit request selection bounds mapped"

DIAGRAM="specs/solace-dev/diagrams/request-selection-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid diagram"
    exit 1
fi
echo "[PASS] Manager Selection Prime Mermaid artifact present"

echo "=== SAC67 Smoke COMPLETE: all checks passed ==="
exit 0
