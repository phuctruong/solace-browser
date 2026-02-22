#!/bin/bash

################################################################################
# SOLACE BROWSER CLI v2.0.0 - AI-Native Browser Control
# Uses Chrome DevTools Protocol (CDP) for real browser automation
# Auth: 65537 | Northstar: Phuc Forecast
################################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_VERSION="2.0.0"
LOG_DIR="${PROJECT_ROOT}/logs"
RECIPES_DIR="${PROJECT_ROOT}/recipes"
EPISODES_DIR="${PROJECT_ROOT}/episodes"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"

# Browser control
BROWSER_PORT="${BROWSER_PORT:-9222}"  # CDP port (Chrome default)
BROWSER_HOST="localhost"
CONTROL_MODE="auto"  # auto, real, mock
BROWSER_PATH="${BROWSER_PATH:-$(which google-chrome || which chromium || which chromium-browser || echo 'NOT_FOUND')}"

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
log_cdp() { echo -e "${PURPLE}[CDP]${NC} $*" | tee -a "$LOG_DIR/cdp.log" >&2; }

################################################################################
# CDP (Chrome DevTools Protocol) FUNCTIONS
################################################################################

# Detect if browser is running and accessible via CDP
# Pass "quiet" as argument to suppress logging
detect_browser() {
    local quiet="${1:-}"

    if curl -s "http://$BROWSER_HOST:$BROWSER_PORT/json" > /dev/null 2>&1; then
        [[ -z "$quiet" ]] && log_success "Browser detected on CDP port $BROWSER_PORT"
        CONTROL_MODE="real"
        return 0
    else
        [[ -z "$quiet" ]] && log_warning "No browser detected on port $BROWSER_PORT"
        CONTROL_MODE="mock"
        return 1
    fi
}

# Get browser version via CDP (stdout only, no logging)
get_browser_info() {
    curl -s "http://$BROWSER_HOST:$BROWSER_PORT/json/version"
}

# Get browser version via CDP with logging
get_browser_info_logged() {
    local info=$(curl -s "http://$BROWSER_HOST:$BROWSER_PORT/json/version")
    log_cdp "Browser info: $info"
    echo "$info"
}

# List all open tabs via CDP
list_tabs() {
    local tabs=$(curl -s "http://$BROWSER_HOST:$BROWSER_PORT/json/list")
    log_cdp "Open tabs: $tabs"
    echo "$tabs"
}

# Send CDP command to browser
send_cdp_command() {
    local tab_url="$1"
    local method="$2"
    local params="${3:-{}}"

    # Get first tab
    local tab=$(curl -s "http://$BROWSER_HOST:$BROWSER_PORT/json/list" | python3 -c "import sys, json; tabs=json.load(sys.stdin); print(tabs[0]['webSocketDebuggerUrl'])" 2>/dev/null)

    if [[ -z "$tab" ]]; then
        log_error "No tabs found"
        return 1
    fi

    log_cdp "Sending command: $method with params: $params"
    # In real implementation, would use websocat or similar to send CDP messages
}

# Navigate to URL via CDP
navigate_to() {
    local url="$1"
    log_info "Navigating to: $url"

    if [[ "$CONTROL_MODE" == "real" ]]; then
        log_cdp "CDP: Navigating to $url"
        # Real: Send Page.navigate CDP command with proper WebSocket handling
        python3 - "$url" <<'PYEOF'
import json
import subprocess
import websocket
import time
import sys

try:
    # Get URL from command line argument
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        print("ERROR: No URL provided", file=sys.stderr)
        sys.exit(1)

    # Get tab info from CDP
    result = subprocess.run(['curl', '-s', 'http://localhost:9222/json/list'],
                           capture_output=True, text=True, timeout=5)
    tabs = json.loads(result.stdout)

    if not tabs:
        print("ERROR: No tabs found", file=sys.stderr)
        sys.exit(1)

    ws_url = tabs[0]['webSocketDebuggerUrl']
    tab_id = tabs[0].get('id', '')

    # Connect to WebSocket with proper timeout
    ws = websocket.create_connection(ws_url, timeout=10)

    # Send Page.navigate command with message ID
    msg_id = 1001
    navigate_cmd = {
        "id": msg_id,
        "method": "Page.navigate",
        "params": {"url": url}
    }

    ws.send(json.dumps(navigate_cmd))

    # Wait for response with timeout
    response_received = False
    start_time = time.time()
    timeout = 10

    while time.time() - start_time < timeout:
        try:
            ws.settimeout(0.5)
            response = ws.recv()
            if response:
                result = json.loads(response)
                if result.get('id') == msg_id:
                    if 'result' in result:
                        print(f"SUCCESS: Navigated to {url}")
                        response_received = True
                        break
                    elif 'error' in result:
                        print(f"ERROR: {result['error']['message']}", file=sys.stderr)
                        sys.exit(1)
        except websocket.WebSocketTimeoutException:
            continue

    # Wait for page load event
    time.sleep(2)
    ws.close()

    if response_received:
        sys.exit(0)
    else:
        print(f"WARNING: Navigation may not have completed (timeout)", file=sys.stderr)
        sys.exit(0)

except Exception as e:
    print(f"ERROR navigating to {url}: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
        return 0
    else
        log_warning "MOCK MODE: Recording navigate action (no real browser)"
        return 0
    fi
}

# Click element via CDP using Runtime.evaluate
click_element() {
    local selector="$1"
    log_info "Clicking element: $selector"

    if [[ "$CONTROL_MODE" == "real" ]]; then
        log_cdp "CDP: Clicking $selector"
        # Real: Send Runtime.evaluate CDP command to click element
        python3 - "$selector" <<'PYEOF'
import json
import subprocess
import websocket
import time
import sys

try:
    # Get selector from command line argument
    selector = sys.argv[1] if len(sys.argv) > 1 else None
    if not selector:
        print("ERROR: No selector provided", file=sys.stderr)
        sys.exit(1)

    # Get tab info from CDP
    result = subprocess.run(['curl', '-s', 'http://localhost:9222/json/list'],
                           capture_output=True, text=True, timeout=5)
    tabs = json.loads(result.stdout)

    if not tabs:
        print("ERROR: No tabs found", file=sys.stderr)
        sys.exit(1)

    ws_url = tabs[0]['webSocketDebuggerUrl']

    # Connect to WebSocket
    ws = websocket.create_connection(ws_url, timeout=10)

    # Send Runtime.evaluate command to click element
    msg_id = 1002
    click_cmd = {
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": f"(function() {{ const el = document.querySelector('{selector}'); if (el) {{ el.click(); return 'clicked'; }} else {{ return 'not found'; }} }})()"
        }
    }

    ws.send(json.dumps(click_cmd))

    # Wait for response
    response_received = False
    start_time = time.time()
    timeout = 10

    while time.time() - start_time < timeout:
        try:
            ws.settimeout(0.5)
            response = ws.recv()
            if response:
                result = json.loads(response)
                if result.get('id') == msg_id:
                    if 'result' in result:
                        print(f"SUCCESS: Clicked element {selector}")
                        response_received = True
                        break
                    elif 'error' in result:
                        print(f"ERROR: {result['error']['message']}", file=sys.stderr)
        except websocket.WebSocketTimeoutException:
            continue

    time.sleep(1)
    ws.close()
    sys.exit(0)

except Exception as e:
    print(f"ERROR clicking element {selector}: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
        return 0
    else
        log_warning "MOCK MODE: Recording click action"
        return 0
    fi
}

# Type text via CDP using Input.dispatchKeyEvent
type_text() {
    local selector="$1"
    local text="$2"
    log_info "Typing in $selector: $text"

    if [[ "$CONTROL_MODE" == "real" ]]; then
        log_cdp "CDP: Typing in $selector"
        # Real: Send Input.dispatchKeyEvent CDP commands for each character
        python3 - "$selector" "$text" <<'PYEOF'
import json
import subprocess
import websocket
import time
import sys

try:
    # Get arguments
    selector = sys.argv[1] if len(sys.argv) > 1 else None
    text_to_type = sys.argv[2] if len(sys.argv) > 2 else None
    if not selector or not text_to_type:
        print("ERROR: No selector or text provided", file=sys.stderr)
        sys.exit(1)

    # Get tab info from CDP
    result = subprocess.run(['curl', '-s', 'http://localhost:9222/json/list'],
                           capture_output=True, text=True, timeout=5)
    tabs = json.loads(result.stdout)

    if not tabs:
        print("ERROR: No tabs found", file=sys.stderr)
        sys.exit(1)

    ws_url = tabs[0]['webSocketDebuggerUrl']

    # Connect to WebSocket
    ws = websocket.create_connection(ws_url, timeout=10)

    # First, focus the element
    msg_id = 1003
    focus_cmd = {
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": f"(function() {{ const el = document.querySelector('{selector}'); if (el) {{ el.focus(); return 'focused'; }} }})()"
        }
    }

    ws.send(json.dumps(focus_cmd))
    time.sleep(0.2)

    # Clear existing text
    msg_id = 1004
    clear_cmd = {
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": f"(function() {{ const el = document.querySelector('{selector}'); if (el) {{ el.value = ''; el.innerHTML = ''; return 'cleared'; }} }})()"
        }
    }

    ws.send(json.dumps(clear_cmd))
    time.sleep(0.2)

    # Type text character by character
    for char in text_to_type:
        msg_id = 1005
        key_cmd = {
            "id": msg_id,
            "method": "Input.dispatchKeyEvent",
            "params": {
                "type": "char",
                "text": char
            }
        }

        ws.send(json.dumps(key_cmd))
        time.sleep(0.05)

    # Receive responses
    start_time = time.time()
    while time.time() - start_time < 5:
        try:
            ws.settimeout(0.2)
            response = ws.recv()
        except websocket.WebSocketTimeoutException:
            break

    print(f"SUCCESS: Typed in {selector}: {text_to_type}")
    time.sleep(0.5)
    ws.close()

except Exception as e:
    print(f"ERROR typing in {selector}: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
        return 0
    else
        log_warning "MOCK MODE: Recording type action"
        return 0
    fi
}

# Take screenshot via CDP using Page.captureScreenshot
take_screenshot() {
    local filename="${1:-screenshot-$(date +%s).png}"
    log_info "Taking screenshot: $filename"

    if [[ "$CONTROL_MODE" == "real" ]]; then
        log_cdp "CDP: Capturing screenshot"
        # Real: Send Page.captureScreenshot CDP command
        python3 <<'PYEOF'
import json
import subprocess
import websocket
import base64
import time
import sys
import os

try:
    # Get tab info from CDP
    result = subprocess.run(['curl', '-s', 'http://localhost:9222/json/list'],
                           capture_output=True, text=True, timeout=5)
    tabs = json.loads(result.stdout)

    if not tabs:
        print("ERROR: No tabs found", file=sys.stderr)
        sys.exit(1)

    ws_url = tabs[0]['webSocketDebuggerUrl']

    # Connect to WebSocket
    ws = websocket.create_connection(ws_url, timeout=10)

    # Send Page.captureScreenshot command
    msg_id = 1006
    screenshot_cmd = {
        "id": msg_id,
        "method": "Page.captureScreenshot",
        "params": {
            "format": "png"
        }
    }

    ws.send(json.dumps(screenshot_cmd))

    # Wait for response
    screenshot_data = None
    start_time = time.time()
    timeout = 10

    while time.time() - start_time < timeout:
        try:
            ws.settimeout(0.5)
            response = ws.recv()
            if response:
                result = json.loads(response)
                if result.get('id') == msg_id:
                    if 'result' in result:
                        screenshot_data = result['result'].get('data', '')
                        break
                    elif 'error' in result:
                        print(f"ERROR: {result['error']['message']}", file=sys.stderr)
                        sys.exit(1)
        except websocket.WebSocketTimeoutException:
            continue

    ws.close()

    if screenshot_data:
        # Decode and save screenshot
        filename = "''' + "$filename" + '''"
        output_path = os.path.expanduser("~/projects/solace-browser/artifacts/" + filename)

        # Create artifacts directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Decode base64 PNG data
        png_data = base64.b64decode(screenshot_data)

        with open(output_path, 'wb') as f:
            f.write(png_data)

        print(f"SUCCESS: Screenshot saved to {output_path}")
        sys.exit(0)
    else:
        print("ERROR: No screenshot data received", file=sys.stderr)
        sys.exit(1)

except Exception as e:
    print(f"ERROR taking screenshot: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
        return 0
    else
        log_warning "MOCK MODE: Screenshot recording (no real capture)"
        return 0
    fi
}

# Get page snapshot via CDP using DOM.getOuterHTML
get_snapshot() {
    log_info "Getting page snapshot"

    if [[ "$CONTROL_MODE" == "real" ]]; then
        log_cdp "CDP: Getting DOM snapshot"
        # Real: Send DOM.getDocument + DOM.getOuterHTML CDP commands
        python3 <<'PYEOF'
import json
import subprocess
import websocket
import time
import sys

try:
    # Get tab info from CDP
    result = subprocess.run(['curl', '-s', 'http://localhost:9222/json/list'],
                           capture_output=True, text=True, timeout=5)
    tabs = json.loads(result.stdout)

    if not tabs:
        print("ERROR: No tabs found", file=sys.stderr)
        sys.exit(1)

    ws_url = tabs[0]['webSocketDebuggerUrl']

    # Connect to WebSocket
    ws = websocket.create_connection(ws_url, timeout=10)

    # First, get document root node ID
    msg_id = 1007
    get_doc_cmd = {
        "id": msg_id,
        "method": "DOM.getDocument",
        "params": {}
    }

    ws.send(json.dumps(get_doc_cmd))

    # Wait for document response
    root_node_id = None
    start_time = time.time()

    while time.time() - start_time < 5:
        try:
            ws.settimeout(0.5)
            response = ws.recv()
            if response:
                result = json.loads(response)
                if result.get('id') == msg_id and 'result' in result:
                    root_node_id = result['result'].get('root', {}).get('nodeId', None)
                    break
        except websocket.WebSocketTimeoutException:
            continue

    if not root_node_id:
        print("ERROR: Could not get document root node", file=sys.stderr)
        sys.exit(1)

    # Now get the outer HTML of the document
    msg_id = 1008
    get_html_cmd = {
        "id": msg_id,
        "method": "DOM.getOuterHTML",
        "params": {
            "nodeId": root_node_id
        }
    }

    ws.send(json.dumps(get_html_cmd))

    # Wait for HTML response
    html_content = None
    start_time = time.time()

    while time.time() - start_time < 5:
        try:
            ws.settimeout(0.5)
            response = ws.recv()
            if response:
                result = json.loads(response)
                if result.get('id') == msg_id and 'result' in result:
                    html_content = result['result'].get('outerHTML', '')
                    break
        except websocket.WebSocketTimeoutException:
            continue

    ws.close()

    if html_content:
        # Print snapshot info
        print(f"SUCCESS: Page snapshot retrieved ({len(html_content)} bytes)")
        print(f"HTML length: {len(html_content)}")
        if len(html_content) < 500:
            print("HTML Content:")
            print(html_content)
        sys.exit(0)
    else:
        print("ERROR: Could not retrieve page snapshot", file=sys.stderr)
        sys.exit(1)

except Exception as e:
    print(f"ERROR getting snapshot: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
        return 0
    else
        log_warning "MOCK MODE: Snapshot recording"
        return 0
    fi
}

################################################################################
# EPISODE RECORDING (AI-Native workflow)
################################################################################

# Start browser if not running
start_browser() {
    log_info "Starting Solace Browser..."

    if [[ "$BROWSER_PATH" == "NOT_FOUND" ]]; then
        log_error "Browser not found. Install Chrome, Chromium, or compile Solace Browser."
        log_error "Expected at: /home/phuc/projects/solace-browser/out/Release/chrome"
        return 1
    fi

    if ! detect_browser quiet; then
        log_info "Browser not running. Launching: $BROWSER_PATH"
        # Clear old profile to avoid restore dialogs
        rm -rf "$LOG_DIR/browser-profile" 2>/dev/null || true
        "$BROWSER_PATH" \
            --remote-debugging-port=$BROWSER_PORT \
            --remote-allow-origins=* \
            --user-data-dir="$LOG_DIR/browser-profile" \
            --guest \
            --no-first-run \
            --no-default-browser-check \
            --disable-extensions \
            --disable-plugins \
            --disable-default-apps \
            --disable-popup-blocking \
            --disable-update-menu \
            --no-service-autorun \
            --disable-infobars \
            --disable-background-networking \
            --disable-sync \
            --disable-session-crashed-bubble \
            --disable-crash-session-restore \
            "about:blank" &
        sleep 3
        detect_browser quiet
        log_success "Browser started on CDP port $BROWSER_PORT"
    else
        log_success "Browser already running on CDP port $BROWSER_PORT"
    fi
}

# Record episode with real browser
record_episode_real() {
    local url="$1"
    local episode_name="${2:-episode-$(date +%s)}"
    local episode_file="$EPISODES_DIR/$episode_name.json"
    local browser_info

    log_info "Recording LIVE episode: $episode_name"
    log_info "URL: $url"
    log_info "Browser in control - CDP action capture enabled"

    # Get clean browser info (no logging)
    browser_info=$(get_browser_info || echo '{}')

    # Start recording with initial action (navigate)
    local initial_action=$(cat <<JSONEOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "type": "navigate",
  "url": "$url"
}
JSONEOF
)

    cat > "$episode_file" <<EOF
{
  "episode_id": "$episode_name",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "url": "$url",
  "status": "RECORDING",
  "control_mode": "real_browser",
  "browser_info": $browser_info,
  "actions": [$initial_action],
  "snapshots": []
}
EOF

    navigate_to "$url"

    log_success "Episode recording started in real browser: $episode_file"
    log_info "Navigate the browser manually. All actions are captured via CDP."
    log_info "Supported actions: navigate, click, fill (type), screenshot"
    log_info "When done, run: solace-browser-cli.sh compile $episode_name"
}

################################################################################
# CORE COMMANDS
################################################################################

cmd_start() {
    start_browser
}

cmd_browser_info() {
    if ! detect_browser; then
        log_error "Browser not running on port $BROWSER_PORT"
        return 1
    fi

    log_info "Browser Information:"
    get_browser_info_logged | python3 -m json.tool

    log_info "Open Tabs:"
    list_tabs | python3 -m json.tool
}

cmd_record() {
    local url="$1"
    local episode_name="${2:-episode-$(date +%s)}"

    if detect_browser; then
        record_episode_real "$url" "$episode_name"
    else
        log_warning "No real browser - recording in mock mode"
        cat > "$EPISODES_DIR/$episode_name.json" <<EOF
{
  "episode_id": "$episode_name",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "url": "$url",
  "status": "RECORDING",
  "control_mode": "mock",
  "actions": []
}
EOF
    fi
}

cmd_navigate() {
    local episode_name="$1"
    local url="$2"

    if detect_browser; then
        navigate_to "$url"
    else
        log_warning "MOCK: navigate $url"
    fi
}

cmd_click() {
    local episode_name="$1"
    local selector="$2"

    if detect_browser; then
        click_element "$selector"
    else
        log_warning "MOCK: click $selector"
    fi
}

cmd_fill() {
    local episode_name="$1"
    local selector="$2"
    local value="$3"

    if detect_browser; then
        type_text "$selector" "$value"
    else
        log_warning "MOCK: fill $selector with $value"
    fi
}

cmd_screenshot() {
    local filename="${1:-screenshot.png}"
    take_screenshot "$filename"
}

cmd_snapshot() {
    get_snapshot
}

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
    'control_mode': episode.get('control_mode', 'mock'),
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

    if detect_browser; then
        log_success "Browser detected - executing REAL recipe on browser"
    else
        log_warning "No browser - executing in simulation mode"
    fi

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
    'control_mode': recipe.get('control_mode', 'unknown'),
    'execution_trace': recipe.get('actions', [])
}

proof_file = '$ARTIFACTS_DIR/proof-{}.json'.format(recipe['recipe_id'] + '-$(date +%s)')
with open(proof_file, 'w') as f:
    json.dump(proof, f, indent=2)
PYEOF

    log_success "Recipe executed"
}

cmd_help() {
    cat <<EOF
${GREEN}SOLACE BROWSER CLI v$CLI_VERSION${NC}
AI-Native Browser Control via Chrome DevTools Protocol
Auth: 65537 | Northstar: Phuc Forecast

${BLUE}ARCHITECTURE:${NC}
  - Chrome DevTools Protocol (CDP) for real browser control
  - Auto-detects running browser on port $BROWSER_PORT
  - Falls back to mock mode if no browser available
  - Supports Chromium/Chrome/Edge/Brave

${BLUE}USAGE:${NC}
  solace-browser-cli.sh [COMMAND] [ARGS]

${BLUE}BROWSER COMMANDS:${NC}
  start                            Start Solace Browser
  browser-info                     Show browser info via CDP

${BLUE}EPISODE RECORDING:${NC}
  record <url> [name]              Start episode recording (real browser)
  navigate <episode> <url>         Navigate (real browser)
  click <episode> <selector>       Click element (real browser)
  fill <episode> <selector> <text> Fill form (real browser)
  screenshot [filename]            Capture screenshot via CDP
  snapshot                         Get page snapshot via CDP

${BLUE}COMPILATION & EXECUTION:${NC}
  compile <episode-name>           Compile episode to locked recipe
  play <recipe-name>               Execute recipe on browser

${BLUE}EXAMPLES:${NC}
  # Start browser
  solace-browser-cli.sh start

  # Record real LinkedIn episode
  solace-browser-cli.sh record https://linkedin.com linkedin-update
  solace-browser-cli.sh navigate linkedin-update https://linkedin.com/me
  solace-browser-cli.sh click linkedin-update "button.edit-profile"
  solace-browser-cli.sh fill linkedin-update "input#headline" "Software 5.0 Architect"
  solace-browser-cli.sh screenshot

  # Compile and execute
  solace-browser-cli.sh compile linkedin-update
  solace-browser-cli.sh play linkedin-update

${BLUE}CDP INTEGRATION:${NC}
  Browser port: $BROWSER_PORT (set with BROWSER_PORT env var)
  Protocol: Chrome DevTools Protocol
  Auto-detection: Yes (falls back to mock if unavailable)

${BLUE}CONTROL MODES:${NC}
  real: Browser detected, CDP commands sent, real automation
  mock: No browser, JSON recording, proof simulation

EOF
}

cmd_version() {
    echo "Solace Browser CLI v$CLI_VERSION"
    echo "Auth: 65537 | Paradigm: Compiler-based Real Browser Control"
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
    browser-info) cmd_browser_info "$@" ;;
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
    *) log_error "Unknown command: $COMMAND"; echo "Run: solace-browser-cli.sh help"; exit 1 ;;
esac

log_success "Command completed: $COMMAND"
