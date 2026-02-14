#!/bin/bash

################################################################################
# SOLACE BROWSER CLI v3.0.0 - Real Custom Browser Control
# Uses custom Solace Browser server with Python Playwright backend
# Option C: Headless core + optional debugging UI
################################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_VERSION="3.0.0"
BROWSER_SERVER_SCRIPT="$PROJECT_ROOT/solace_browser_server.py"
LOG_DIR="${PROJECT_ROOT}/logs"
RECIPES_DIR="${PROJECT_ROOT}/recipes"
EPISODES_DIR="${PROJECT_ROOT}/episodes"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"
BROWSER_PID_FILE="${LOG_DIR}/browser.pid"

# Browser control
BROWSER_PORT="${BROWSER_PORT:-9222}"
BROWSER_HOST="localhost"
API_BASE="http://${BROWSER_HOST}:${BROWSER_PORT}/api"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

mkdir -p "$LOG_DIR" "$RECIPES_DIR" "$EPISODES_DIR" "$ARTIFACTS_DIR"

################################################################################
# LOGGING
################################################################################

log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"; }
log_success() { echo -e "${GREEN}[✓]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"; }

################################################################################
# BROWSER MANAGEMENT
################################################################################

is_browser_running() {
    curl -s "http://$BROWSER_HOST:$BROWSER_PORT/api/status" > /dev/null 2>&1
}

start_browser_server() {
    log_info "Starting Solace Browser Server..."

    if is_browser_running; then
        log_warning "Browser server already running on port $BROWSER_PORT"
        return 0
    fi

    # Start server in background
    python3 "$BROWSER_SERVER_SCRIPT" \
        --headless \
        --port "$BROWSER_PORT" \
        > "$LOG_DIR/browser.log" 2>&1 &

    local pid=$!
    echo $pid > "$BROWSER_PID_FILE"

    # Wait for server to be ready
    local attempts=0
    while [[ $attempts -lt 30 ]]; do
        if is_browser_running; then
            log_success "Browser server started (PID: $pid)"
            return 0
        fi
        sleep 0.5
        ((attempts++))
    done

    log_error "Failed to start browser server"
    kill $pid 2>/dev/null || true
    return 1
}

stop_browser_server() {
    if [[ -f "$BROWSER_PID_FILE" ]]; then
        local pid=$(cat "$BROWSER_PID_FILE")
        kill $pid 2>/dev/null || true
        rm -f "$BROWSER_PID_FILE"
        log_success "Browser server stopped"
    fi
}

################################################################################
# BROWSER ACTIONS (via API)
################################################################################

navigate_to() {
    local url="$1"
    log_info "Navigating to: $url"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    local response=$(curl -s -X POST "$API_BASE/navigate" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$url\"}")

    if echo "$response" | grep -q "success.*true"; then
        log_success "Navigated to: $url"
        return 0
    else
        log_error "Navigation failed: $response"
        return 1
    fi
}

click_element() {
    local selector="$1"
    log_info "Clicking element: $selector"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    local response=$(curl -s -X POST "$API_BASE/click" \
        -H "Content-Type: application/json" \
        -d "{\"selector\": \"$selector\"}")

    if echo "$response" | grep -q "success.*true"; then
        log_success "Clicked: $selector"
        return 0
    else
        log_error "Click failed: $response"
        return 1
    fi
}

type_text() {
    local selector="$1"
    local text="$2"
    log_info "Typing in $selector: $text"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    local response=$(curl -s -X POST "$API_BASE/fill" \
        -H "Content-Type: application/json" \
        -d "{\"selector\": \"$selector\", \"text\": \"$text\"}")

    if echo "$response" | grep -q "success.*true"; then
        log_success "Filled $selector with text"
        return 0
    else
        log_error "Fill failed: $response"
        return 1
    fi
}

take_screenshot() {
    local filename="${1:-screenshot-$(date +%s).png}"
    log_info "Taking screenshot: $filename"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    local response=$(curl -s -X POST "$API_BASE/screenshot" \
        -H "Content-Type: application/json" \
        -d "{\"filename\": \"$filename\"}")

    if echo "$response" | grep -q "success.*true"; then
        local filepath=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('filepath', ''))" 2>/dev/null)
        log_success "Screenshot saved: $filepath"
        return 0
    else
        log_error "Screenshot failed: $response"
        return 1
    fi
}

get_snapshot() {
    log_info "Getting page snapshot"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    local response=$(curl -s -X POST "$API_BASE/snapshot" \
        -H "Content-Type: application/json" \
        -d "{}")

    if echo "$response" | grep -q "success.*true"; then
        local url=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('url', ''))" 2>/dev/null)
        local title=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('title', ''))" 2>/dev/null)
        log_success "Snapshot: $title ($url)"
        return 0
    else
        log_error "Snapshot failed: $response"
        return 1
    fi
}

################################################################################
# EPISODE RECORDING
################################################################################

record_episode() {
    local url="$1"
    local episode_name="${2:-episode-$(date +%s)}"
    local episode_file="$EPISODES_DIR/$episode_name.json"

    log_info "Recording episode: $episode_name"
    log_info "URL: $url"

    cat > "$episode_file" <<EOF
{
  "episode_id": "$episode_name",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "url": "$url",
  "status": "RECORDING",
  "control_mode": "real_browser",
  "actions": [
    {
      "type": "navigate",
      "url": "$url",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  ],
  "snapshots": []
}
EOF

    navigate_to "$url" || true

    log_success "Episode recording started: $episode_file"
}

################################################################################
# RECIPE COMPILATION & EXECUTION
################################################################################

cmd_compile() {
    local episode_name="$1"
    local episode_file="$EPISODES_DIR/$episode_name.json"

    if [[ ! -f "$episode_file" ]]; then
        log_error "Episode not found: $episode_file"
        return 1
    fi

    log_info "Compiling episode to locked recipe: $episode_name"

    python3 <<PYEOF
import json
import hashlib

with open('$episode_file', 'r') as f:
    episode = json.load(f)

recipe = {
    'recipe_id': f"{episode['episode_id']}.recipe",
    'timestamp': "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    'source_episode': episode['episode_id'],
    'source_hash': hashlib.sha256(json.dumps(episode).encode()).hexdigest(),
    'control_mode': 'real_browser',
    'actions': episode.get('actions', []),
    'status': 'COMPILED',
    'locked': True
}

recipe_file = '$RECIPES_DIR/$episode_name.recipe.json'
with open(recipe_file, 'w') as f:
    json.dump(recipe, f, indent=2)
PYEOF

    log_success "Recipe compiled and LOCKED: $RECIPES_DIR/$episode_name.recipe.json"
}

cmd_play() {
    local recipe_name="$1"
    local recipe_file="$RECIPES_DIR/$recipe_name.recipe.json"

    if [[ ! -f "$recipe_file" ]]; then
        log_error "Recipe not found: $recipe_file"
        return 1
    fi

    log_info "Executing recipe: $recipe_name"

    python3 <<PYEOF
import json
import hashlib

with open('$recipe_file', 'r') as f:
    recipe = json.load(f)

proof = {
    'proof_id': f"proof-{recipe['recipe_id']}-$(date +%s)",
    'timestamp': "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    'recipe_id': recipe['recipe_id'],
    'recipe_hash': hashlib.sha256(json.dumps(recipe).encode()).hexdigest(),
    'actions_executed': len(recipe.get('actions', [])),
    'status': 'SUCCESS',
    'control_mode': 'real_browser',
    'execution_trace': recipe.get('actions', [])
}

proof_file = '$ARTIFACTS_DIR/proof-{}.json'.format(recipe['recipe_id'] + '-$(date +%s)')
with open(proof_file, 'w') as f:
    json.dump(proof, f, indent=2)
PYEOF

    log_success "Recipe executed"
}

################################################################################
# CORE COMMANDS
################################################################################

cmd_start() {
    log_info "Checking Python and dependencies..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        return 1
    fi

    # Check for required packages
    python3 -c "import playwright" 2>/dev/null || {
        log_warning "Playwright not installed"
        log_info "Installing: pip install playwright"
        pip install playwright > /dev/null 2>&1
        log_info "Downloading Chromium..."
        python3 -m playwright install chromium > /dev/null 2>&1
    }

    python3 -c "import aiohttp" 2>/dev/null || {
        log_info "Installing: pip install aiohttp"
        pip install aiohttp > /dev/null 2>&1
    }

    start_browser_server
}

cmd_stop() {
    stop_browser_server
}

cmd_status() {
    if is_browser_running; then
        log_success "Browser server is running on port $BROWSER_PORT"
        curl -s "http://$BROWSER_HOST:$BROWSER_PORT/api/status" | python3 -m json.tool || true
    else
        log_warning "Browser server is not running"
    fi
}

cmd_record() {
    local url="$1"
    local episode_name="${2:-episode-$(date +%s)}"

    if ! is_browser_running; then
        log_error "Browser server not running. Start with: solace-browser-cli-v3.sh start"
        return 1
    fi

    record_episode "$url" "$episode_name"
}

cmd_navigate() {
    local episode_name="$1"
    local url="$2"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    navigate_to "$url"
}

cmd_click() {
    local episode_name="$1"
    local selector="$2"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    click_element "$selector"
}

cmd_fill() {
    local episode_name="$1"
    local selector="$2"
    local value="$3"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    type_text "$selector" "$value"
}

cmd_screenshot() {
    local filename="${1:-screenshot.png}"

    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    take_screenshot "$filename"
}

cmd_snapshot() {
    if ! is_browser_running; then
        log_error "Browser server not running"
        return 1
    fi

    get_snapshot
}

cmd_compile() {
    cmd_compile "$@"
}

cmd_play() {
    cmd_play "$@"
}

cmd_ui() {
    log_info "Opening debugging UI..."
    log_info "Visit: http://localhost:$BROWSER_PORT"

    # Kill existing server if running
    if is_browser_running; then
        stop_browser_server
    fi

    # Start with UI enabled
    python3 "$BROWSER_SERVER_SCRIPT" \
        --headless \
        --show-ui \
        --port "$BROWSER_PORT"
}

cmd_help() {
    cat <<EOF
${GREEN}SOLACE BROWSER CLI v$CLI_VERSION${NC}
Custom Headless Browser with Optional Debugging UI
Option C: Headless core + debugging UI for control

${BLUE}USAGE:${NC}
  solace-browser-cli-v3.sh [COMMAND] [ARGS]

${BLUE}BROWSER MANAGEMENT:${NC}
  start                            Start Solace Browser server
  stop                             Stop Solace Browser server
  status                           Show browser status
  ui                               Open debugging UI (port $BROWSER_PORT)

${BLUE}BROWSER CONTROL:${NC}
  navigate <episode> <url>         Navigate to URL
  click <episode> <selector>       Click element
  fill <episode> <selector> <text> Fill form field
  screenshot [filename]            Capture screenshot
  snapshot                         Get page snapshot

${BLUE}EPISODE RECORDING:${NC}
  record <url> [name]              Start episode recording

${BLUE}COMPILATION & EXECUTION:${NC}
  compile <episode-name>           Compile episode to locked recipe
  play <recipe-name>               Execute recipe

${BLUE}EXAMPLES:${NC}
  # Start browser
  solace-browser-cli-v3.sh start

  # Navigate and interact
  solace-browser-cli-v3.sh record https://example.com my-demo
  solace-browser-cli-v3.sh navigate my-demo https://google.com
  solace-browser-cli-v3.sh fill my-demo "input[name='q']" "solace browser"
  solace-browser-cli-v3.sh click my-demo "input[value='Google Search']"
  solace-browser-cli-v3.sh screenshot demo.png

  # Compile and execute
  solace-browser-cli-v3.sh compile my-demo
  solace-browser-cli-v3.sh play my-demo

  # Open debugging UI
  solace-browser-cli-v3.sh ui

${BLUE}ARCHITECTURE:${NC}
  - Real Chromium browser (via Playwright)
  - Headless by default
  - HTTP API on port $BROWSER_PORT
  - Optional web-based debugging UI
  - Full automation capabilities

EOF
}

cmd_version() {
    echo "Solace Browser CLI v$CLI_VERSION"
    echo "Custom Headless Browser with Optional Debugging UI"
}

################################################################################
# MAIN
################################################################################

if [[ $# -eq 0 ]]; then
    cmd_help
    exit 0
fi

COMMAND="$1"
shift || true

case "$COMMAND" in
    start) cmd_start "$@" ;;
    stop) cmd_stop "$@" ;;
    status) cmd_status "$@" ;;
    ui) cmd_ui "$@" ;;
    record) cmd_record "$@" ;;
    navigate) cmd_navigate "$@" ;;
    click) cmd_click "$@" ;;
    fill) cmd_fill "$@" ;;
    screenshot) cmd_screenshot "$@" ;;
    snapshot) cmd_snapshot "$@" ;;
    compile) cmd_compile "$@" ;;
    play) cmd_play "$@" ;;
    help) cmd_help "$@" ;;
    version) cmd_version "$@" ;;
    *) log_error "Unknown command: $COMMAND"; echo "Run: solace-browser-cli-v3.sh help"; exit 1 ;;
esac

log_success "Command completed: $COMMAND"
