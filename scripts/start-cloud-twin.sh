#!/usr/bin/env bash
# Solace Cloud Twin — starts Xvfb + Rust Runtime
# Auth: 65537 | Zero Python
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
PORT="${PORT:-8080}"
export SOLACE_HOME="/home/solace/.solace"

# Start virtual display for headed-headless browser
Xvfb "${DISPLAY}" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
echo "INFO: Xvfb started (PID=${XVFB_PID}, DISPLAY=${DISPLAY})"
sleep 1

# Start Rust runtime (binds to PORT from Cloud Run)
echo "INFO: Starting solace-runtime on port ${PORT}"
exec /app/solace-runtime --port "${PORT}"
