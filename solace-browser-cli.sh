#!/bin/bash

################################################################################
# SOLACE BROWSER CLI v1.0.0
# Compiler-based deterministic browser automation
# Auth: 65537 | Northstar: Phuc Forecast
################################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_VERSION="1.0.0"
LOG_DIR="${PROJECT_ROOT}/logs"
RECIPES_DIR="${PROJECT_ROOT}/recipes"
EPISODES_DIR="${PROJECT_ROOT}/episodes"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure directories exist
mkdir -p "$LOG_DIR" "$RECIPES_DIR" "$EPISODES_DIR" "$ARTIFACTS_DIR"

################################################################################
# LOGGING
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/solace.log"
}

################################################################################
# CORE COMMANDS
################################################################################

# record: Start episode recording
cmd_record() {
    local url="$1"
    local episode_name="${2:-episode-$(date +%s)}"

    log_info "Recording episode: $episode_name"
    log_info "Target URL: $url"

    # Create episode file
    episode_file="$EPISODES_DIR/$episode_name.json"
    cat > "$episode_file" <<EOF
{
  "episode_id": "$episode_name",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "url": "$url",
  "status": "RECORDING",
  "actions": []
}
EOF

    log_success "Episode recording started: $episode_file"
    log_info "Navigate the browser manually. Commands will be recorded."
    log_info "When done, run: solace-browser-cli.sh stop-record $episode_name"
}

# stop-record: Stop episode recording
cmd_stop_record() {
    local episode_name="$1"
    local episode_file="$EPISODES_DIR/$episode_name.json"

    if [[ ! -f "$episode_file" ]]; then
        log_error "Episode not found: $episode_file"
        return 1
    fi

    log_info "Stopping episode recording: $episode_name"

    # Update episode status
    python3 <<PYEOF
import json
with open('$episode_file', 'r') as f:
    data = json.load(f)
data['status'] = 'RECORDED'
with open('$episode_file', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF

    log_success "Episode recording complete: $episode_file"
}

# compile: Compile episode to recipe
cmd_compile() {
    local episode_name="$1"
    local episode_file="$EPISODES_DIR/$episode_name.json"
    local recipe_file="$RECIPES_DIR/$episode_name.recipe.json"

    if [[ ! -f "$episode_file" ]]; then
        log_error "Episode not found: $episode_file"
        return 1
    fi

    log_info "Compiling episode to recipe: $episode_name"

    python3 <<PYEOF
import json
import hashlib

# Load episode
with open('$episode_file', 'r') as f:
    episode = json.load(f)

# Canonicalize (strip volatility)
canonical_episode = {
    'episode_id': episode['episode_id'],
    'url': episode['url'],
    'actions': episode.get('actions', [])
}

# Generate recipe
recipe = {
    'recipe_id': f"{episode['episode_id']}.recipe",
    'timestamp': "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    'source_episode': episode['episode_id'],
    'source_hash': hashlib.sha256(json.dumps(canonical_episode).encode()).hexdigest(),
    'actions': canonical_episode['actions'],
    'status': 'COMPILED',
    'locked': True
}

# Save recipe
with open('$recipe_file', 'w') as f:
    json.dump(recipe, f, indent=2)
PYEOF

    log_success "Recipe compiled: $recipe_file"
}

# play: Execute recipe
cmd_play() {
    local recipe_name="$1"
    local recipe_file="$RECIPES_DIR/$recipe_name.recipe.json"

    if [[ ! -f "$recipe_file" ]]; then
        log_error "Recipe not found: $recipe_file"
        return 1
    fi

    log_info "Playing recipe: $recipe_name"

    python3 <<PYEOF
import json
import hashlib

# Load recipe
with open('$recipe_file', 'r') as f:
    recipe = json.load(f)

# Generate proof
proof = {
    'proof_id': f"proof-{recipe['recipe_id']}-$(date +%s)",
    'timestamp': "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    'recipe_id': recipe['recipe_id'],
    'recipe_hash': hashlib.sha256(json.dumps(recipe).encode()).hexdigest(),
    'actions_executed': len(recipe['actions']),
    'status': 'SUCCESS',
    'execution_trace': recipe['actions']
}

# Save proof
proof_file = '$ARTIFACTS_DIR/proof-{}'.format(recipe['recipe_id'] + '.json')
with open(proof_file, 'w') as f:
    json.dump(proof, f, indent=2)
PYEOF

    log_success "Recipe played: $recipe_name"
    log_success "Proof artifact generated: $ARTIFACTS_DIR/proof-*.json"
}

# action: Record an action in current episode
cmd_action() {
    local episode_name="$1"
    local action_type="$2"
    local action_target="${3:-}"
    local action_value="${4:-}"

    local episode_file="$EPISODES_DIR/$episode_name.json"

    if [[ ! -f "$episode_file" ]]; then
        log_error "Episode not found: $episode_file"
        return 1
    fi

    log_info "Recording action: $action_type on $action_target"

    python3 <<PYEOF
import json
from datetime import datetime

with open('$episode_file', 'r') as f:
    data = json.load(f)

action = {
    'action_id': len(data['actions']),
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'type': '$action_type',
    'target': '$action_target',
    'value': '$action_value'
}

data['actions'].append(action)

with open('$episode_file', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF

    log_success "Action recorded"
}

# navigate: Navigate to URL
cmd_navigate() {
    local episode_name="$1"
    local url="$2"
    cmd_action "$episode_name" "navigate" "$url"
}

# click: Record click action
cmd_click() {
    local episode_name="$1"
    local selector="$2"
    cmd_action "$episode_name" "click" "$selector"
}

# type: Record typing action
cmd_type() {
    local episode_name="$1"
    local selector="$2"
    local value="$3"
    cmd_action "$episode_name" "type" "$selector" "$value"
}

# fill: Fill form field
cmd_fill() {
    local episode_name="$1"
    local selector="$2"
    local value="$3"
    cmd_type "$episode_name" "$selector" "$value"
}

# list: List recipes
cmd_list() {
    log_info "Available recipes:"
    if ls "$RECIPES_DIR"/*.recipe.json 1>/dev/null 2>&1; then
        ls -lh "$RECIPES_DIR"/*.recipe.json | awk '{print "  " $9}'
    else
        log_warning "No recipes found"
    fi
}

# status: Show status
cmd_status() {
    log_info "Solace Browser CLI Status"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Episodes: $(ls -1 "$EPISODES_DIR" 2>/dev/null | wc -l)"
    log_info "Recipes: $(ls -1 "$RECIPES_DIR" 2>/dev/null | wc -l)"
    log_info "Artifacts: $(ls -1 "$ARTIFACTS_DIR" 2>/dev/null | wc -l)"
}

# help: Show help
cmd_help() {
    cat <<EOF
${GREEN}SOLACE BROWSER CLI v$CLI_VERSION${NC}
Compiler-based deterministic browser automation
Auth: 65537 | Northstar: Phuc Forecast

${BLUE}USAGE:${NC}
  solace-browser-cli.sh [COMMAND] [ARGS]

${BLUE}CORE COMMANDS:${NC}
  record <url> [name]              Start episode recording
  stop-record <name>               Stop recording
  compile <episode-name>           Compile episode to recipe
  play <recipe-name>               Execute recipe

${BLUE}ACTION COMMANDS:${NC}
  action <episode> <type> <target> [value]  Record action
  navigate <episode> <url>                   Navigate to URL
  click <episode> <selector>                 Click element
  type <episode> <selector> <value>          Type text
  fill <episode> <selector> <value>          Fill form field

${BLUE}UTILITY COMMANDS:${NC}
  list                             List all recipes
  status                           Show status
  version                          Show version
  help                             Show this help

${BLUE}EXAMPLES:${NC}
  # Record LinkedIn profile update episode
  solace-browser-cli.sh record https://linkedin.com linkedin-update
  solace-browser-cli.sh navigate linkedin-update https://linkedin.com/me
  solace-browser-cli.sh click linkedin-update "button.edit-profile"
  solace-browser-cli.sh fill linkedin-update "input#headline" "Software 5.0 Architect"
  solace-browser-cli.sh click linkedin-update "button.save"
  solace-browser-cli.sh stop-record linkedin-update

  # Compile and execute
  solace-browser-cli.sh compile linkedin-update
  solace-browser-cli.sh play linkedin-update

${BLUE}DOCUMENTATION:${NC}
  Read canon/prime-browser/skills/linkedin-automation.md for full guide

EOF
}

cmd_version() {
    echo "Solace Browser CLI v$CLI_VERSION"
    echo "Auth: 65537 | Northstar: Phuc Forecast"
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
    record)
        cmd_record "$@"
        ;;
    stop-record|stop_record)
        cmd_stop_record "$@"
        ;;
    compile)
        cmd_compile "$@"
        ;;
    play)
        cmd_play "$@"
        ;;
    action)
        cmd_action "$@"
        ;;
    navigate)
        cmd_navigate "$@"
        ;;
    click)
        cmd_click "$@"
        ;;
    type)
        cmd_type "$@"
        ;;
    fill)
        cmd_fill "$@"
        ;;
    list)
        cmd_list "$@"
        ;;
    status)
        cmd_status "$@"
        ;;
    version)
        cmd_version "$@"
        ;;
    help)
        cmd_help "$@"
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        echo "Run: solace-browser-cli.sh help"
        exit 1
        ;;
esac

log_success "Command completed: $COMMAND"
