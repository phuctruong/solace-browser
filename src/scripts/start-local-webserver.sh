#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${1:-8791}"
BIND_ADDR="127.0.0.1"

printf "=== Solace Browser Local Web Server ===\n"
printf "Project Root: %s\n" "$PROJECT_ROOT"
printf "Bind: %s:%s\n" "$BIND_ADDR" "$PORT"

if lsof -i ":$PORT" >/dev/null 2>&1; then
  PID="$(lsof -t -i ":$PORT" | head -1)"
  printf "Stopping existing server on %s (PID %s)\n" "$PORT" "$PID"
  kill "$PID" || true
  sleep 1
fi

cd "$PROJECT_ROOT"
PORT="$PORT" BIND_ADDR="$BIND_ADDR" python3 web/server.py
