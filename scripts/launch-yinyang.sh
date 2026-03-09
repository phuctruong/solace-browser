#!/bin/sh

set -eu

STATE_DIR="${HOME}/.solace"
PID_FILE="${STATE_DIR}/yinyang.pid"
REPO_FILE="${STATE_DIR}/repo-root"
LOG_FILE="${STATE_DIR}/yinyang.log"
PORT="8888"
HEALTH_URL="http://localhost:${PORT}/health"
SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "$1 not found"
  fi
}

read_pid_file() {
  if [ ! -f "${PID_FILE}" ]; then
    return 1
  fi

  pid=$(sed -n '1p' "${PID_FILE}")
  case "${pid}" in
    ''|*[!0-9]*)
      rm -f "${PID_FILE}"
      return 1
      ;;
  esac

  printf '%s\n' "${pid}"
  return 0
}

resolve_repo_root() {
  if [ -n "${SOLACE_REPO_ROOT:-}" ]; then
    printf '%s\n' "${SOLACE_REPO_ROOT}"
    return 0
  fi

  repo_candidate=$(CDPATH= cd "${SCRIPT_DIR}/.." 2>/dev/null && pwd)
  if [ -f "${repo_candidate}/yinyang-server.py" ]; then
    printf '%s\n' "${repo_candidate}"
    return 0
  fi

  if [ -f "${REPO_FILE}" ]; then
    repo_root=$(sed -n '1p' "${REPO_FILE}")
    if [ -n "${repo_root}" ] && [ -f "${repo_root}/yinyang-server.py" ]; then
      printf '%s\n' "${repo_root}"
      return 0
    fi
  fi

  fail "unable to locate yinyang-server.py; set SOLACE_REPO_ROOT or run scripts/install.sh"
}

wait_for_health() {
  target_pid=${1:-}
  attempt=1
  while [ "${attempt}" -le 5 ]; do
    if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
      echo "Yinyang server healthy on port ${PORT}"
      return 0
    fi

    if [ -n "${target_pid}" ] && ! kill -0 "${target_pid}" 2>/dev/null; then
      return 2
    fi

    sleep 1
    attempt=$((attempt + 1))
  done

  return 1
}

mkdir -p "${STATE_DIR}"

require_cmd nc
require_cmd curl
require_cmd nohup
require_cmd python3

started_new=0
current_pid=""

if current_pid=$(read_pid_file); then
  if kill -0 "${current_pid}" 2>/dev/null; then
    if wait_for_health; then
      exit 0
    fi

    fail "existing Yinyang process ${current_pid} did not become healthy"
  fi

  rm -f "${PID_FILE}"
fi

if nc -z localhost "${PORT}" 2>/dev/null; then
  if wait_for_health; then
    exit 0
  fi

  fail "port ${PORT} is in use but /health did not respond"
fi

repo_root=$(resolve_repo_root)
server_script="${repo_root}/yinyang-server.py"

if [ ! -f "${server_script}" ]; then
  fail "server entry point not found at ${server_script}"
fi

nohup python3 "${server_script}" "${repo_root}" >>"${LOG_FILE}" 2>&1 &
current_pid=$!
started_new=1
printf '%s\n' "${current_pid}" > "${PID_FILE}"

if wait_for_health "${current_pid}"; then
  exit 0
else
  wait_status=$?
fi

if [ "${started_new}" -eq 1 ]; then
  kill -TERM "${current_pid}" 2>/dev/null || true
  sleep 1
  kill -9 "${current_pid}" 2>/dev/null || true
  rm -f "${PID_FILE}"
fi

if [ "${wait_status}" -eq 2 ]; then
  fail "Yinyang server process ${current_pid} exited before passing health check; see ${LOG_FILE}"
fi

fail "Yinyang server failed health check after 5 attempts"
