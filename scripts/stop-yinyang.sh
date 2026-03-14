#!/bin/sh
# Diagram: 29-chromium-build-pipeline

set -eu

STATE_DIR="${HOME}/.solace"
PID_FILE="${STATE_DIR}/yinyang.pid"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

if [ ! -f "${PID_FILE}" ]; then
  echo "Yinyang server is not running"
  exit 0
fi

pid=$(sed -n '1p' "${PID_FILE}")
case "${pid}" in
  ''|*[!0-9]*)
    rm -f "${PID_FILE}"
    fail "invalid PID file at ${PID_FILE}"
    ;;
esac

if ! kill -0 "${pid}" 2>/dev/null; then
  rm -f "${PID_FILE}"
  echo "Removed stale PID file ${PID_FILE}"
  exit 0
fi

kill -TERM "${pid}"

remaining=3
while [ "${remaining}" -gt 0 ]; do
  if ! kill -0 "${pid}" 2>/dev/null; then
    rm -f "${PID_FILE}"
    echo "Stopped Yinyang server ${pid}"
    exit 0
  fi

  sleep 1
  remaining=$((remaining - 1))
done

kill -9 "${pid}" 2>/dev/null || fail "unable to force-stop Yinyang server ${pid}"
rm -f "${PID_FILE}"
echo "Force-stopped Yinyang server ${pid}"
