#!/usr/bin/env bash
# solace-browser-server.sh — start|stop|restart|status|tail|log|session
# Manages the Solace Browser WebService (port 9223)
#
# This is a persistent browser automation server with REST API control surface.
# Features:
#  - OAuth3 session persistence (cookies + localStorage)
#  - Headed or headless mode
#  - Multi-provider support (Gmail, LinkedIn, GitHub, Twitter, Slack, Discord)
#  - REST API: /navigate, /click, /fill, /snapshot, /screenshot, /oauth3/*, etc.
#
# Usage:
#   ./solace-browser-server.sh start          # Start server (opens browser in headed mode)
#   ./solace-browser-server.sh start --headless  # Start in headless mode (Cloud Run)
#   ./solace-browser-server.sh stop           # Stop server
#   ./solace-browser-server.sh restart        # Restart server
#   ./solace-browser-server.sh status         # Show status
#   ./solace-browser-server.sh tail           # Tail logs (live)
#   ./solace-browser-server.sh log            # Show full log
#   ./solace-browser-server.sh session        # Show session info
#   ./solace-browser-server.sh test           # Run health check
#
# Environment variables:
#   SOLACE_PORT              Default: 9223 (browser API)
#   SOLACE_HOST              Default: 127.0.0.1
#   SOLACE_HEADLESS          Default: false (headed mode shows browser)
#   SOLACE_SESSION_FILE      Default: artifacts/solace_session.json
#   SOLACE_USER_DATA_DIR     Default: ~/.solace-browser/profile
#   SOLACE_AUTOSAVE_SECONDS  Default: 60 (auto-save session interval)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

# Configuration
PORT="${SOLACE_PORT:-9223}"
HOST="${SOLACE_HOST:-127.0.0.1}"
HEADLESS="${SOLACE_HEADLESS:-false}"
PID_FILE="${HOME}/.solace-browser/server.pid"
LOG_DIR="${HOME}/.solace-browser/logs"
LOG_FILE="${LOG_DIR}/browser-$(date +%Y%m%d).log"
SESSION_FILE="${REPO_ROOT}/artifacts/solace_session.json"
USER_DATA_DIR="${HOME}/.solace-browser/profile"
AUTOSAVE_SECONDS="${SOLACE_AUTOSAVE_SECONDS:-60}"

URL="http://${HOST}:${PORT}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helpers
# ============================================================================

_log() {
    echo -e "${BLUE}[solace-browser-server]${NC} $*"
}

_error() {
    echo -e "${RED}[solace-browser-server]${NC} ERROR: $*" >&2
}

_success() {
    echo -e "${GREEN}[solace-browser-server]${NC} $*"
}

_warn() {
    echo -e "${YELLOW}[solace-browser-server]${NC} WARNING: $*"
}

_pid_running() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null
}

_read_pid() {
    [[ -f "$PID_FILE" ]] && cat "$PID_FILE" || echo ""
}

_open_browser() {
    # Only open browser if NOT in headless mode
    if [[ "$HEADLESS" == "true" ]]; then
        return 0
    fi

    sleep 1
    _log "Opening browser at $URL"
    if command -v xdg-open &>/dev/null; then
        xdg-open "$URL" &>/dev/null &
    elif command -v open &>/dev/null; then
        open "$URL" &>/dev/null &
    else
        _warn "Could not auto-open browser (no xdg-open or open command)"
    fi
}

_ensure_dirs() {
    mkdir -p "$LOG_DIR" "$(dirname "$PID_FILE")" "$(dirname "$SESSION_FILE")" "$USER_DATA_DIR"
}

# ============================================================================
# Commands
# ============================================================================

cmd_start() {
    local existing_pid
    existing_pid=$(_read_pid)
    if [[ -n "$existing_pid" ]] && _pid_running "$existing_pid"; then
        _log "Already running (pid=$existing_pid) at $URL"
        return 0
    fi

    _ensure_dirs

    # Determine mode
    if [[ "$HEADLESS" == "true" ]]; then
        _log "Starting browser server in HEADLESS mode..."
        MODE="headless"
    else
        _log "Starting browser server in HEADED mode (visible browser window)..."
        MODE="headed"
    fi

    _log "Server will listen on: $URL"
    _log "Session file: $SESSION_FILE"
    _log "User data dir: $USER_DATA_DIR"
    _log "Session autosave: ${AUTOSAVE_SECONDS}s"

    # Set up environment
    export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
    export SOLACE_PORT="$PORT"
    export SOLACE_HOST="$HOST"
    export SOLACE_HEADLESS="$HEADLESS"
    export SOLACE_SESSION_FILE="$SESSION_FILE"
    export SOLACE_USER_DATA_DIR="$USER_DATA_DIR"
    export SOLACE_AUTOSAVE_SECONDS="$AUTOSAVE_SECONDS"

    # Start the server
    nohup "$PYTHON" solace_browser_server.py \
        --port "$PORT" \
        $(if [[ "$HEADLESS" != "true" ]]; then echo "--show-ui"; fi) \
        >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    _success "Started (pid=$pid) — log: $LOG_FILE"

    # Wait for server to be ready
    sleep 2
    if _pid_running "$pid"; then
        _success "Server is running and ready"
        _open_browser
    else
        _error "Server failed to start. Check logs:"
        tail -20 "$LOG_FILE"
        return 1
    fi
}

cmd_stop() {
    local pid
    pid=$(_read_pid)
    if [[ -z "$pid" ]] || ! _pid_running "$pid"; then
        _log "Not running"
        rm -f "$PID_FILE"
        return 0
    fi
    _log "Stopping server (pid=$pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1
    if _pid_running "$pid"; then
        _warn "Process didn't stop gracefully, killing it..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    _success "Stopped (pid=$pid)"
}

cmd_restart() {
    _log "Restarting server..."
    cmd_stop
    sleep 1
    cmd_start
}

cmd_status() {
    local pid
    pid=$(_read_pid)
    if [[ -n "$pid" ]] && _pid_running "$pid"; then
        _success "RUNNING (pid=$pid) at $URL"
        # Show additional status info
        if command -v curl &>/dev/null; then
            _log "Checking health endpoint..."
            if curl -s "$URL/api/status" > /dev/null 2>&1; then
                _success "Health check: PASS"
            else
                _warn "Health check: FAILED (endpoint not responding)"
            fi
        fi
    else
        _log "STOPPED"
        rm -f "$PID_FILE"
    fi
}

cmd_tail() {
    if [[ ! -f "$LOG_FILE" ]]; then
        _error "Log file not found: $LOG_FILE"
        return 1
    fi
    _log "Tailing logs (Ctrl+C to stop)..."
    tail -f "$LOG_FILE"
}

cmd_log() {
    if [[ ! -f "$LOG_FILE" ]]; then
        _error "Log file not found: $LOG_FILE"
        return 1
    fi
    _log "Full log file: $LOG_FILE"
    echo ""
    cat "$LOG_FILE"
}

cmd_session() {
    _log "Session information:"
    echo ""
    echo "Session file: $SESSION_FILE"
    if [[ -f "$SESSION_FILE" ]]; then
        local size
        size=$(du -h "$SESSION_FILE" | cut -f1)
        _success "Session exists (size: $size)"
        echo ""
        _log "Session contents (first 20 keys):"
        if command -v jq &>/dev/null; then
            jq 'keys[:20]' "$SESSION_FILE" 2>/dev/null || echo "  (could not parse as JSON)"
        else
            head -c 500 "$SESSION_FILE"
        fi
    else
        _log "No session file yet"
    fi
    echo ""
    _log "User data directory: $USER_DATA_DIR"
    if [[ -d "$USER_DATA_DIR" ]]; then
        du -sh "$USER_DATA_DIR"
    else
        _log "Directory does not exist yet"
    fi
}

cmd_test() {
    _log "Running health check..."
    if ! command -v curl &>/dev/null; then
        _error "curl not installed"
        return 1
    fi

    local pid
    pid=$(_read_pid)
    if [[ -z "$pid" ]] || ! _pid_running "$pid"; then
        _error "Server not running. Start with: $0 start"
        return 1
    fi

    _log "Testing endpoints..."
    echo ""

    # API Status check
    _log "GET /api/status"
    if curl -s "$URL/api/status" | grep -q "running"; then
        _success "✓ API status check passed"
    else
        _error "✗ API status check failed"
        return 1
    fi
    echo ""

    # Version check (CDP compatible endpoint)
    _log "GET /json/version"
    if curl -s "$URL/json/version" | grep -q "Solace"; then
        _success "✓ Version endpoint working"
    else
        _error "✗ Version endpoint failed"
        return 1
    fi
    echo ""

    _success "All tests passed!"
}

cmd_help() {
    cat << 'EOF'
solace-browser-server.sh — Manage the Solace Browser WebService

USAGE:
  ./solace-browser-server.sh <command> [options]

COMMANDS:
  start          Start browser server (headed mode by default)
  start --headless
                 Start in headless mode (for Cloud Run / CI environments)
  stop           Stop browser server
  restart        Stop and start
  status         Show running status
  tail           Tail logs in real-time
  log            Show full log file
  session        Show session information
  test           Run health checks
  help           Show this help

ENVIRONMENT VARIABLES:
  SOLACE_PORT              API port (default: 9223)
  SOLACE_HOST              API host (default: 127.0.0.1)
  SOLACE_HEADLESS          Run headless (default: false)
  SOLACE_SESSION_FILE      Session file path (default: artifacts/solace_session.json)
  SOLACE_USER_DATA_DIR     Chrome profile dir (default: ~/.solace-browser/profile)
  SOLACE_AUTOSAVE_SECONDS  Auto-save interval (default: 60)

EXAMPLES:
  # Start headed mode (shows browser window)
  ./solace-browser-server.sh start

  # Start headless (for Cloud Run)
  SOLACE_HEADLESS=true ./solace-browser-server.sh start

  # Check if server is running
  ./solace-browser-server.sh status

  # Monitor logs
  ./solace-browser-server.sh tail

  # Restart for a clean session
  ./solace-browser-server.sh restart

API ENDPOINTS (when server is running):
  Health/Status:
    GET /health                    Server health
    GET /status                    Current page status
    GET /api/status                Alternative endpoint

  Navigation:
    POST /navigate                 { "url": "https://..." }
    GET /screenshot                Capture visual
    GET /snapshot                  Get ARIA + DOM + console

  Interaction:
    POST /click                    { "selector": "..." }
    POST /fill                     { "selector": "...", "text": "..." }
    POST /keyboard                 { "key": "Enter" }

  OAuth3:
    GET /api/oauth3/providers      List all OAuth3 providers
    POST /api/oauth3/login         { "provider_id": "gmail" }
    GET /api/oauth3/session        Current session info
    POST /api/oauth3/logout        { "provider_id": "gmail" }

  Session:
    POST /save-session             Save cookies + localStorage

DEFAULT PORT: 9223
WEB ADDRESS: http://127.0.0.1:9223

For more info, see:
  - NORTHSTAR.md         Project vision
  - README.md            Features and setup
  - docs/ARCHITECTURE_OAUTH3_HOMEPAGE.md  API design

EOF
}

# ============================================================================
# Main
# ============================================================================

main() {
    local cmd="${1:-help}"

    case "$cmd" in
        start)
            # Check for --headless flag
            if [[ "${2:-}" == "--headless" ]]; then
                HEADLESS="true"
            fi
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        tail)
            cmd_tail
            ;;
        log)
            cmd_log
            ;;
        session)
            cmd_session
            ;;
        test)
            cmd_test
            ;;
        help|-h|--help)
            cmd_help
            ;;
        *)
            _error "Unknown command: $cmd"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# Run main if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
