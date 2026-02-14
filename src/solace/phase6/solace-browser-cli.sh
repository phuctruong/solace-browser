#!/usr/bin/env bash
# solace-browser-cli.sh - CLI wrapper for Solace Browser HTTP API
# Phase 6: CLI Bridge
#
# Usage:
#   solace-browser record <url>           - Start recording at URL
#   solace-browser stop                   - Stop recording
#   solace-browser replay <episode_id>    - Replay a recorded episode
#   solace-browser list                   - List all episodes
#   solace-browser show <episode_id>      - Show episode details
#   solace-browser export <episode_id> [output_path] - Export episode
#   solace-browser snapshot               - Take page snapshot
#   solace-browser verify <selector>      - Verify element exists
#   solace-browser health                 - Check server health
#   solace-browser status                 - Show system status
#   solace-browser server                 - Start the HTTP server

set -euo pipefail

# Configuration
SOLACE_HTTP_PORT="${SOLACE_HTTP_PORT:-9999}"
SOLACE_API_URL="http://127.0.0.1:${SOLACE_HTTP_PORT}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ---- Utility Functions ----

print_header() {
    echo -e "${CYAN}${BOLD}Solace Browser CLI${NC} v0.6.0"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if curl is available
check_curl() {
    if ! command -v curl &>/dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
}

# Check if jq is available (optional, for pretty output)
has_jq() {
    command -v jq &>/dev/null
}

# Make API call and format output
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="${SOLACE_API_URL}${endpoint}"
    local response
    local http_code

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null) || {
            print_error "Cannot connect to Solace HTTP server at ${SOLACE_API_URL}"
            print_info "Start the server with: solace-browser server"
            exit 1
        }
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$url" 2>/dev/null) || {
            print_error "Cannot connect to Solace HTTP server at ${SOLACE_API_URL}"
            print_info "Start the server with: solace-browser server"
            exit 1
        }
    fi

    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 400 ] 2>/dev/null; then
        if has_jq; then
            local err_msg
            err_msg=$(echo "$body" | jq -r '.error // "Unknown error"' 2>/dev/null)
            print_error "$err_msg"
        else
            print_error "$body"
        fi
        return 1
    fi

    if has_jq; then
        echo "$body" | jq .
    else
        echo "$body"
    fi
}

# ---- Command Handlers ----

cmd_record() {
    local url="${1:-}"
    if [ -z "$url" ]; then
        print_error "Usage: solace-browser record <url>"
        exit 1
    fi

    print_info "Starting recording at: $url"
    api_call POST /record-episode "{\"url\": \"$url\"}"
}

cmd_stop() {
    print_info "Stopping recording..."
    api_call POST /stop-recording "{}"
}

cmd_replay() {
    local episode_id="${1:-}"
    local speed="${2:-1.0}"
    if [ -z "$episode_id" ]; then
        print_error "Usage: solace-browser replay <episode_id> [speed]"
        exit 1
    fi

    print_info "Replaying episode: $episode_id (speed: ${speed}x)"
    api_call POST /play-recipe "{\"episode_id\": \"$episode_id\", \"speed\": $speed}"
}

cmd_list() {
    api_call GET /list-episodes
}

cmd_show() {
    local episode_id="${1:-}"
    if [ -z "$episode_id" ]; then
        print_error "Usage: solace-browser show <episode_id>"
        exit 1
    fi

    api_call GET "/episode/$episode_id"
}

cmd_export() {
    local episode_id="${1:-}"
    local output_path="${2:-}"
    if [ -z "$episode_id" ]; then
        print_error "Usage: solace-browser export <episode_id> [output_path]"
        exit 1
    fi

    local data="{\"episode_id\": \"$episode_id\""
    if [ -n "$output_path" ]; then
        data="${data}, \"output_path\": \"$output_path\""
    fi
    data="${data}}"

    print_info "Exporting episode: $episode_id"
    api_call POST /export-episode "$data"
}

cmd_snapshot() {
    print_info "Taking page snapshot..."
    api_call POST /get-snapshot "{}"
}

cmd_verify() {
    local selector="${1:-}"
    if [ -z "$selector" ]; then
        print_error "Usage: solace-browser verify <css-selector>"
        exit 1
    fi

    print_info "Verifying element: $selector"
    api_call POST /verify-interaction "{\"selector\": \"$selector\"}"
}

cmd_health() {
    api_call GET /health
}

cmd_status() {
    api_call GET /status
}

cmd_server() {
    print_header
    print_info "Starting HTTP API server on port $SOLACE_HTTP_PORT..."

    if command -v node &>/dev/null; then
        exec node "${SCRIPT_DIR}/http_server.js"
    else
        print_error "Node.js is required to run the HTTP server"
        print_info "Install Node.js: https://nodejs.org/"
        exit 1
    fi
}

cmd_help() {
    print_header
    echo ""
    echo "Usage: solace-browser <command> [args...]"
    echo ""
    echo -e "${BOLD}Recording Commands:${NC}"
    echo "  record <url>              Start recording at URL"
    echo "  stop                      Stop recording"
    echo "  replay <episode_id>       Replay a recorded episode"
    echo ""
    echo -e "${BOLD}Episode Commands:${NC}"
    echo "  list                      List all recorded episodes"
    echo "  show <episode_id>         Show episode details"
    echo "  export <id> [path]        Export episode as JSON"
    echo ""
    echo -e "${BOLD}Inspection Commands:${NC}"
    echo "  snapshot                  Take current page snapshot"
    echo "  verify <selector>         Verify element exists on page"
    echo ""
    echo -e "${BOLD}System Commands:${NC}"
    echo "  health                    Check server health"
    echo "  status                    Show system status"
    echo "  server                    Start the HTTP API server"
    echo "  help                      Show this help message"
    echo ""
    echo -e "${BOLD}Environment:${NC}"
    echo "  SOLACE_HTTP_PORT          HTTP port (default: 9999)"
    echo "  SOLACE_WS_URL             WebSocket URL (default: ws://localhost:9222)"
    echo "  SOLACE_EPISODE_DIR        Episode storage directory"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  solace-browser server                      # Start server"
    echo "  solace-browser record https://example.com   # Record"
    echo "  solace-browser stop                         # Stop recording"
    echo "  solace-browser list                         # List episodes"
    echo "  solace-browser replay session_12345         # Replay"
    echo "  solace-browser verify 'button.submit'       # Verify element"
}

# ---- Main ----

check_curl

command="${1:-help}"
shift 2>/dev/null || true

case "$command" in
    record)     cmd_record "$@" ;;
    stop)       cmd_stop ;;
    replay)     cmd_replay "$@" ;;
    list)       cmd_list ;;
    show)       cmd_show "$@" ;;
    export)     cmd_export "$@" ;;
    snapshot)   cmd_snapshot ;;
    verify)     cmd_verify "$@" ;;
    health)     cmd_health ;;
    status)     cmd_status ;;
    server)     cmd_server ;;
    help|--help|-h)  cmd_help ;;
    *)
        print_error "Unknown command: $command"
        echo "Run 'solace-browser help' for usage"
        exit 1
        ;;
esac
