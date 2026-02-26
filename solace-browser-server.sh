#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
HOST="${SOLACE_HOST:-127.0.0.1}"
API_PORT="${SOLACE_API_PORT:-9222}"
UI_PORT="${SOLACE_UI_PORT:-9223}"

PID_DIR="${HOME}/.solace-browser"
LOG_DIR="${HOME}/.solace-browser/logs"
API_PID_FILE="${PID_DIR}/api.pid"
UI_PID_FILE="${PID_DIR}/ui.pid"
API_LOG="${LOG_DIR}/api.log"
UI_LOG="${LOG_DIR}/ui.log"

ensure_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
}

is_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file" || true
}

wait_http() {
  local url="$1"
  local retries=30
  for _ in $(seq 1 "$retries"); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_all() {
  local mode="$1" # headless|headed
  ensure_dirs

  if [[ "$mode" == "headless" ]]; then
    nohup env PYTHONPATH="$ROOT" "$PYTHON" "$ROOT/solace_browser_server.py" --port "$API_PORT" --headless >>"$API_LOG" 2>&1 &
  else
    nohup env PYTHONPATH="$ROOT" "$PYTHON" "$ROOT/solace_browser_server.py" --port "$API_PORT" --head >>"$API_LOG" 2>&1 &
  fi
  echo "$!" > "$API_PID_FILE"

  nohup env PYTHONPATH="$ROOT" SOLACE_BROWSER_API_BASE="http://${HOST}:${API_PORT}" "$PYTHON" -m uvicorn ui_server:app --host "$HOST" --port "$UI_PORT" --log-level warning >>"$UI_LOG" 2>&1 &
  echo "$!" > "$UI_PID_FILE"

  wait_http "http://${HOST}:${API_PORT}/api/health"
  wait_http "http://${HOST}:${UI_PORT}/"

  echo "started api=http://${HOST}:${API_PORT} ui=http://${HOST}:${UI_PORT} mode=${mode}"
}

stop_all() {
  ensure_dirs
  local api_pid ui_pid
  api_pid="$(read_pid "$API_PID_FILE")"
  ui_pid="$(read_pid "$UI_PID_FILE")"

  if is_running "$api_pid"; then
    kill "$api_pid" 2>/dev/null || true
  fi
  if is_running "$ui_pid"; then
    kill "$ui_pid" 2>/dev/null || true
  fi

  rm -f "$API_PID_FILE" "$UI_PID_FILE"
  echo "stopped"
}

status_all() {
  ensure_dirs
  local api_pid ui_pid
  api_pid="$(read_pid "$API_PID_FILE")"
  ui_pid="$(read_pid "$UI_PID_FILE")"
  local api_state="down" ui_state="down"
  is_running "$api_pid" && api_state="running"
  is_running "$ui_pid" && ui_state="running"

  local api_health="down" ui_health="down"
  curl -fsS --max-time 2 "http://${HOST}:${API_PORT}/api/health" >/dev/null 2>&1 && api_health="ok"
  curl -fsS --max-time 2 "http://${HOST}:${UI_PORT}/" >/dev/null 2>&1 && ui_health="ok"

  echo "api_pid=${api_pid:-none} api_state=${api_state} api_health=${api_health}"
  echo "ui_pid=${ui_pid:-none} ui_state=${ui_state} ui_health=${ui_health}"
}

usage() {
  cat <<USAGE
Usage:
  ./solace-browser-server.sh               # start headless (default)
  ./solace-browser-server.sh --head        # start headed
  ./solace-browser-server.sh --headless    # start headless
  ./solace-browser-server.sh --stop        # stop API + UI
  ./solace-browser-server.sh --status      # status + health
USAGE
}

main() {
  local arg="${1:-}"
  case "$arg" in
    "")
      start_all "headless"
      ;;
    --head)
      start_all "headed"
      ;;
    --headless)
      start_all "headless"
      ;;
    --stop)
      stop_all
      ;;
    --status)
      status_all
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
