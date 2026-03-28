#!/usr/bin/env bash
# scripts/smoke-manager-run-launch.sh
set -e

echo "=== SAC69 Smoke: Manager Run Launch ==="

HUB_HTML="solace-hub/src/index.html"
HUB_JS="solace-hub/src/hub-app.js"

if ! grep -q "dev-active-workflow-launch" "$HUB_HTML"; then
    echo "[FAIL] Missing active assignment run launch UI card"
    exit 1
fi
echo "[PASS] Active workflow launch UI present"

if ! grep -q "__solaceLaunchRoutedFlow" "$HUB_JS"; then
    echo "[FAIL] Missing run launch action hook"
    exit 1
fi
echo "[PASS] Native run launch API loop mapped"

if ! grep -q "fetch(API + '/api/v1/apps/run/' + appId" "$HUB_JS"; then
    echo "[FAIL] Native POST dispatch to runtime layer missing"
    exit 1
fi
echo "[PASS] Explicit fetch request to mapped applications detected"

if ! grep -q "chosen = active.find" "$HUB_JS"; then
    echo "[FAIL] Launch path does not prefer the explicitly selected routed role"
    exit 1
fi
echo "[PASS] Launch path resolves selected routed role before fallback"

if ! grep -q "Runtime Route: POST /api/v1/apps/run/" "$HUB_JS"; then
    echo "[FAIL] Launch output missing honest runtime route basis"
    exit 1
fi
echo "[PASS] Honest runtime route basis surfaced"

DIAGRAM="specs/solace-dev/diagrams/manager-run-launch-workflow.prime-mermaid.md"
if [ ! -f "$DIAGRAM" ]; then
    echo "[FAIL] Missing Prime Mermaid diagram"
    exit 1
fi
echo "[PASS] Manager Execution Launch Prime Mermaid artifact present"

echo "=== SAC69 Smoke COMPLETE: all checks passed ==="
exit 0
