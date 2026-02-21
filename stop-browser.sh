#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-9222}"
API_BASE="http://localhost:${PORT}/api"

# Must match start-browser.sh defaults (can be overridden by env).
SESSION_FILE="${SESSION_FILE:-artifacts/solace_session.json}"
USER_DATA_DIR="${USER_DATA_DIR:-artifacts/solace_user_data}"

cd "${ROOT_DIR}"

is_running() {
  curl -fsS "${API_BASE}/status" >/dev/null 2>&1
}

find_listen_pid() {
  # Prefer lsof; fall back to ss. Both are present in this env, but keep robust.
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    # Example: LISTEN 0 128 127.0.0.1:9222 ... users:(("python3",pid=12345,fd=...))
    ss -lptn "sport = :${PORT}" 2>/dev/null | rg -o "pid=\\d+" | head -n 1 | cut -d= -f2 || true
    return 0
  fi
  return 0
}

echo "Stopping Solace browser on port ${PORT}..."
echo "User data dir: ${USER_DATA_DIR}"
echo "Session file:  ${SESSION_FILE}"

# Best-effort persist cookies/localStorage export (in addition to Chrome profile persistence).
if is_running; then
  curl -fsS -X POST "${API_BASE}/save-session" >/dev/null 2>&1 || true
fi

PID="$(find_listen_pid)"
if [[ -n "${PID}" ]]; then
  echo "Found server PID: ${PID}"

  # Graceful shutdown first (lets server save session on stop).
  kill -INT "${PID}" 2>/dev/null || true

  # Wait up to ~10s.
  for _ in $(seq 1 20); do
    if ! kill -0 "${PID}" 2>/dev/null; then
      break
    fi
    sleep 0.5
  done

  # Escalate if still alive.
  if kill -0 "${PID}" 2>/dev/null; then
    kill -TERM "${PID}" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "${PID}" 2>/dev/null; then
        break
      fi
      sleep 0.5
    done
  fi

  if kill -0 "${PID}" 2>/dev/null; then
    echo "Server still alive; sending KILL"
    kill -KILL "${PID}" 2>/dev/null || true
  fi
else
  echo "No listening PID found on port ${PORT} (server may already be stopped)."
fi

# Kill orphaned Chromium processes that are clearly from this Solace profile.
# This avoids nuking the user's normal Chrome sessions.
if command -v pkill >/dev/null 2>&1; then
  pkill -f -- "--user-data-dir=${USER_DATA_DIR}" 2>/dev/null || true
fi

echo "Stop complete."

