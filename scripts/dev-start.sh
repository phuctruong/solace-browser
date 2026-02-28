#!/usr/bin/env bash
# Dev startup: Claude Code wrapper + Solace Browser
set -euo pipefail

WRAPPER_PATH="${CLAUDE_CODE_WRAPPER_PATH:-/home/phuc/projects/stillwater/src/cli/src/claude_code_wrapper.py}"
BROWSER_PORT="${BROWSER_PORT:-9222}"
WRAPPER_PORT="${CLAUDE_CODE_PORT:-8080}"

echo "=== Solace Browser Dev Mode ==="
echo "Starting Claude Code wrapper on port $WRAPPER_PORT..."

if [ -f "$WRAPPER_PATH" ]; then
    python3 "$WRAPPER_PATH" &
    WRAPPER_PID=$!
    echo "[wrapper] PID=$WRAPPER_PID"

    # Wait for wrapper health
    for i in $(seq 1 15); do
        if curl -s "http://127.0.0.1:$WRAPPER_PORT/" > /dev/null 2>&1; then
            echo "[wrapper] Ready on port $WRAPPER_PORT"
            break
        fi
        sleep 1
    done
else
    echo "[wrapper] Not found at $WRAPPER_PATH — running without LLM"
    WRAPPER_PID=""
fi

echo "Starting Solace Browser on port $BROWSER_PORT..."
SOLACE_LLM_BACKEND=claude_code \
CLAUDE_CODE_HOST=127.0.0.1 \
CLAUDE_CODE_PORT=$WRAPPER_PORT \
python3 solace_browser_server.py --port "$BROWSER_PORT" --show-ui --llm-backend claude_code &
BROWSER_PID=$!

echo "[browser] PID=$BROWSER_PID"
echo "=== Dev servers running ==="
echo "  Browser: http://localhost:$BROWSER_PORT"
echo "  Wrapper: http://localhost:$WRAPPER_PORT"

cleanup() {
    echo "Shutting down..."
    [ -n "${BROWSER_PID:-}" ] && kill "$BROWSER_PID" 2>/dev/null
    [ -n "${WRAPPER_PID:-}" ] && kill "$WRAPPER_PID" 2>/dev/null
    wait
}
trap cleanup SIGINT SIGTERM

wait
