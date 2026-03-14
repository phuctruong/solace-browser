#!/usr/bin/env bash
# Diagram: 29-chromium-build-pipeline
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
PORT="${PORT:-8888}"

Xvfb "${DISPLAY}" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
echo "Xvfb started (PID=${XVFB_PID}, DISPLAY=${DISPLAY})"

sleep 1

exec python3 yinyang_server.py --port "${PORT}" --cloud-twin
