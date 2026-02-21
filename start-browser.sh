#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-9222}"
HEALTH_URL="http://localhost:${PORT}/health"
API_STATUS_URL="http://localhost:${PORT}/api/status"
SESSION_FILE="${SESSION_FILE:-artifacts/solace_session.json}"
# Shared Chrome profile directory. This preserves logins (HN/Reddit/etc.) across restarts
# even if the server is killed without a clean shutdown.
USER_DATA_DIR="${USER_DATA_DIR:-artifacts/solace_user_data}"
# Default disabled to avoid disruptive background activity (e.g. while typing).
# Enable if you want periodic persistence: AUTOSAVE_SECONDS=15 ./start-browser.sh
AUTOSAVE_SECONDS="${AUTOSAVE_SECONDS:-0}"

cd "${ROOT_DIR}"
mkdir -p logs artifacts

is_running() {
  curl -fsS "${HEALTH_URL}" >/dev/null 2>&1 || curl -fsS "${API_STATUS_URL}" >/dev/null 2>&1
}

if is_running; then
  echo "A browser server is already running on port ${PORT}."
  echo "Stop it first, then rerun:"
  echo "  ./stop-browser.sh"
  exit 1
fi

echo "Starting headed Solace browser on port ${PORT}..."
echo "This is the correct browser for manual login."
echo
echo "User data dir (shared Chrome profile): ${USER_DATA_DIR}"
echo "Session file (shared across restarts): ${SESSION_FILE}"
if [[ "${AUTOSAVE_SECONDS}" == "0" ]]; then
  echo "Autosave: disabled (recommended for interactive typing)"
else
  echo "Autosave: every ${AUTOSAVE_SECONDS}s"
fi
echo
if [[ "${AUTOSAVE_SECONDS}" == "0" ]]; then
  echo "After you finish logging in, force a save:"
else
  echo "After you finish logging in, the server will autosave cookies/localStorage."
  echo "You can also force a save anytime:"
fi
echo "  curl -s -X POST http://localhost:${PORT}/api/save-session | python3 -m json.tool"
echo
echo "Then tell me and I will verify headless reuse."
echo

PYTHON="./.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

export SOLACE_SESSION_FILE="${SESSION_FILE}"
export SOLACE_AUTOSAVE_SECONDS="${AUTOSAVE_SECONDS}"
export SOLACE_USER_DATA_DIR="${USER_DATA_DIR}"

exec "$PYTHON" persistent_browser_server.py \
  --port "${PORT}" \
  --session-file "${SESSION_FILE}" \
  --user-data-dir "${USER_DATA_DIR}" \
  --autosave-seconds "${AUTOSAVE_SECONDS}"
