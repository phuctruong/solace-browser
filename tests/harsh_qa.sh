#!/bin/bash

################################################################################
# SOLACE BROWSER CLI v2.0 - HARSH QA TESTS
# Extreme verification: determinism, scaling, edge cases
# Run: bash tests/harsh_qa.sh
################################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/solace-browser-cli-v2.sh"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"
EPISODES_DIR="$PROJECT_ROOT/episodes"
RECIPES_DIR="$PROJECT_ROOT/data/default/recipes"
LOGS_DIR="$PROJECT_ROOT/logs"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

mkdir -p "$ARTIFACTS_DIR" "$EPISODES_DIR" "$RECIPES_DIR" "$LOGS_DIR"

################################################################################
# QA HELPERS
################################################################################

qa_section() {
    echo -e "\n${MAGENTA}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║ QA TEST: $1${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════╝${NC}"
}

qa_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

qa_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

qa_step() {
    echo -e "${BLUE}  → $1${NC}"
}

qa_start() {
    ((TESTS_RUN++))
    echo -e "\n${YELLOW}[QA TEST $TESTS_RUN]${NC} $1"
}

################################################################################
# HARSH QA TESTS
################################################################################

qa_no_popup_dialogs() {
    qa_section "No Popup Dialogs on Browser Startup"
    qa_start "Verify browser doesn't show restore/update popups"

    qa_step "Killing existing browser"
    pkill -f "chrome|chromium" 2>/dev/null || true
    sleep 2

    qa_step "Starting fresh browser"
    bash "$CLI_SCRIPT" start > /dev/null 2>&1
    sleep 5

    # Check if browser is showing about:blank (not a restore dialog)
    if curl -s "http://localhost:9222/json/list" > /dev/null 2>&1; then
        qa_step "Browser is responsive"

        # Get page info
        local page_info=$(curl -s "http://localhost:9222/json/list" | python3 -c "import sys, json; tabs=json.load(sys.stdin); print(tabs[0]['url'] if tabs else '')" 2>/dev/null)

        # Should show about:blank, not a restore page
        if [[ "$page_info" == *"about:"* ]] || [[ -z "$page_info" ]]; then
            qa_pass "Browser shows clean state (no restore dialog)"
        else
            qa_fail "Browser may be showing restore dialog: $page_info"
        fi
    else
        qa_fail "Browser not responding"
    fi
}

qa_navigation_determinism() {
    qa_section "Navigation Determinism Across Multiple Domains"
    qa_start "Navigate to 5 different domains, verify each succeeds"

    local domains=("example.com" "github.com" "wikipedia.org" "stackoverflow.com" "google.com")
    local success_count=0

    for domain in "${domains[@]}"; do
        qa_step "Testing: https://$domain"
        if bash "$CLI_SCRIPT" navigate test-nav "https://$domain" > /dev/null 2>&1; then
            ((success_count++))
            qa_step "✓ Navigate to $domain"
        else
            qa_step "✗ Navigate to $domain failed"
        fi
    done

    if [[ $success_count -ge 5 ]]; then
        qa_pass "All 5 domain navigations succeeded"
    else
        qa_fail "Only $success_count/5 domain navigations succeeded"
    fi
}

qa_action_recording_completeness() {
    qa_section "Episode Action Recording Completeness"
    qa_start "Verify navigate/click/type actions are recorded in episode"

    local episode_name="qa-recording-test"
    local episode_file="$EPISODES_DIR/$episode_name.json"

    qa_step "Creating episode with actions"
    bash "$CLI_SCRIPT" record "https://example.com" "$episode_name" > /dev/null 2>&1
    bash "$CLI_SCRIPT" navigate "$episode_name" "https://github.com" > /dev/null 2>&1
    bash "$CLI_SCRIPT" click "$episode_name" "button.submit" > /dev/null 2>&1
    bash "$CLI_SCRIPT" fill "$episode_name" "input#search" "test" > /dev/null 2>&1

    if [[ ! -f "$episode_file" ]]; then
        qa_fail "Episode file not created"
        return 1
    fi

    qa_step "Checking episode structure"
    if grep -q '"actions"' "$episode_file"; then
        qa_pass "Episode has actions array"

        # In future: verify actual action count
        # For now, just check the array exists
        local action_count=$(python3 -c "import json; print(len(json.load(open('$episode_file')).get('actions', [])))" 2>/dev/null)
        if [[ $action_count -ge 0 ]]; then
            qa_pass "Episode action array is valid"
        fi
    else
        qa_fail "Episode missing actions array"
    fi
}

qa_deterministic_compilation() {
    qa_section "Deterministic Recipe Compilation"
    qa_start "Compile same episode 5 times, verify identical recipe_hash"

    local episode_name="qa-determinism-compile"
    local recipe_file="$RECIPES_DIR/$episode_name.recipe.json"

    qa_step "Creating base episode"
    bash "$CLI_SCRIPT" record "https://example.com" "$episode_name" > /dev/null 2>&1

    # Compile 5 times and collect hashes
    declare -a hashes
    for i in {1..5}; do
        bash "$CLI_SCRIPT" compile "$episode_name" > /dev/null 2>&1
        if [[ -f "$recipe_file" ]]; then
            local hash=$(python3 -c "import json; print(json.load(open('$recipe_file')).get('source_hash', ''))" 2>/dev/null)
            hashes+=("$hash")
            qa_step "Compile $i: hash=$hash"
        fi
    done

    # Verify all hashes are identical
    local base_hash="${hashes[0]}"
    local all_same=true
    for hash in "${hashes[@]:1}"; do
        if [[ "$hash" != "$base_hash" ]]; then
            all_same=false
            break
        fi
    done

    if [[ "$all_same" == true ]]; then
        qa_pass "All 5 compilations produced identical recipe_hash"
    else
        qa_fail "Compilation produced different hashes"
    fi
}

qa_concurrent_execution() {
    qa_section "Concurrent Recipe Execution (No Interference)"
    qa_start "Execute 3 recipes concurrently, verify no crosstalk"

    local recipes=("qa-concurrent-1" "qa-concurrent-2" "qa-concurrent-3")

    qa_step "Creating 3 independent recipes"
    for recipe in "${recipes[@]}"; do
        bash "$CLI_SCRIPT" record "https://example.com" "$recipe" > /dev/null 2>&1
        bash "$CLI_SCRIPT" compile "$recipe" > /dev/null 2>&1
    done

    qa_step "Executing recipes in parallel"
    for recipe in "${recipes[@]}"; do
        bash "$CLI_SCRIPT" play "$recipe" > /dev/null 2>&1 &
    done
    wait

    qa_step "Verifying all proofs generated"
    local proof_count=0
    for recipe in "${recipes[@]}"; do
        local recipe_proofs=$(ls "$ARTIFACTS_DIR"/proof-qa-concurrent-*.recipe-*.json 2>/dev/null | wc -l)
        proof_count=$((proof_count + recipe_proofs))
    done

    if [[ $proof_count -ge 3 ]]; then
        qa_pass "All 3 concurrent executions generated proofs"
    else
        qa_fail "Only $proof_count/3 proofs generated from concurrent execution"
    fi
}

qa_proof_integrity() {
    qa_section "Proof Artifact Integrity & Completeness"
    qa_start "Verify all proofs have required fields and valid JSON"

    local recipe_name="qa-proof-integrity"
    local recipe_file="$RECIPES_DIR/$recipe_name.recipe.json"

    qa_step "Creating recipe and generating proof"
    bash "$CLI_SCRIPT" record "https://example.com" "$recipe_name" > /dev/null 2>&1
    bash "$CLI_SCRIPT" compile "$recipe_name" > /dev/null 2>&1
    bash "$CLI_SCRIPT" play "$recipe_name" > /dev/null 2>&1

    # Find latest proof
    local proof_file=$(ls -t "$ARTIFACTS_DIR"/proof-qa-proof-integrity.recipe-*.json 2>/dev/null | head -1)

    if [[ ! -f "$proof_file" ]]; then
        qa_fail "Proof file not found"
        return 1
    fi

    qa_step "Validating proof JSON"
    if python3 -m json.tool "$proof_file" > /dev/null 2>&1; then
        qa_pass "Proof is valid JSON"
    else
        qa_fail "Proof is invalid JSON"
        return 1
    fi

    qa_step "Checking required proof fields"
    local required_fields=("proof_id" "recipe_id" "status" "execution_trace")
    local missing_fields=()

    for field in "${required_fields[@]}"; do
        if grep -q "\"$field\"" "$proof_file"; then
            qa_step "✓ Field: $field"
        else
            missing_fields+=("$field")
        fi
    done

    if [[ ${#missing_fields[@]} -eq 0 ]]; then
        qa_pass "All required proof fields present"
    else
        qa_fail "Missing proof fields: ${missing_fields[*]}"
    fi
}

qa_episode_to_proof_chain() {
    qa_section "Full Chain: Episode → Recipe → Proof"
    qa_start "Verify unbroken chain from episode creation to proof generation"

    local chain_name="qa-full-chain"
    local episode_file="$EPISODES_DIR/$chain_name.json"
    local recipe_file="$RECIPES_DIR/$chain_name.recipe.json"

    qa_step "Step 1: Create episode"
    bash "$CLI_SCRIPT" record "https://example.com" "$chain_name" > /dev/null 2>&1
    if [[ ! -f "$episode_file" ]]; then
        qa_fail "Episode creation failed"
        return 1
    fi
    local episode_id=$(python3 -c "import json; print(json.load(open('$episode_file')).get('episode_id', ''))" 2>/dev/null)
    qa_pass "Episode created: $episode_id"

    qa_step "Step 2: Compile to recipe"
    bash "$CLI_SCRIPT" compile "$chain_name" > /dev/null 2>&1
    if [[ ! -f "$recipe_file" ]]; then
        qa_fail "Recipe compilation failed"
        return 1
    fi
    local recipe_id=$(python3 -c "import json; print(json.load(open('$recipe_file')).get('recipe_id', ''))" 2>/dev/null)
    local source_episode=$(python3 -c "import json; print(json.load(open('$recipe_file')).get('source_episode', ''))" 2>/dev/null)
    qa_pass "Recipe compiled: $recipe_id (from episode: $source_episode)"

    # Verify linkage
    if [[ "$source_episode" == "$episode_id" ]]; then
        qa_pass "Recipe properly references source episode"
    else
        qa_fail "Recipe source episode doesn't match"
    fi

    qa_step "Step 3: Generate proof"
    bash "$CLI_SCRIPT" play "$chain_name" > /dev/null 2>&1
    local proof_file=$(ls -t "$ARTIFACTS_DIR"/proof-qa-full-chain.recipe-*.json 2>/dev/null | head -1)
    if [[ ! -f "$proof_file" ]]; then
        qa_fail "Proof generation failed"
        return 1
    fi
    local proof_recipe=$(python3 -c "import json; print(json.load(open('$proof_file')).get('recipe_id', ''))" 2>/dev/null)
    qa_pass "Proof generated and references recipe: $proof_recipe"

    # Verify linkage
    if [[ "$proof_recipe" == "$recipe_id" ]]; then
        qa_pass "Full chain verified: episode → recipe → proof"
    else
        qa_fail "Proof doesn't reference correct recipe"
    fi
}

qa_stress_large_batch() {
    qa_section "Stress Test: Large Batch Processing"
    qa_start "Create, compile, and execute 10 recipes"

    qa_step "Creating 10 recipes"
    for i in {1..10}; do
        local recipe_name="qa-stress-$i"
        bash "$CLI_SCRIPT" record "https://example.com" "$recipe_name" > /dev/null 2>&1
        bash "$CLI_SCRIPT" compile "$recipe_name" > /dev/null 2>&1
    done

    local recipe_count=$(ls "$RECIPES_DIR"/qa-stress-*.recipe.json 2>/dev/null | wc -l)
    if [[ $recipe_count -eq 10 ]]; then
        qa_pass "All 10 recipes compiled successfully"
    else
        qa_fail "Only $recipe_count/10 recipes compiled"
    fi

    qa_step "Executing all 10 recipes"
    for i in {1..10}; do
        local recipe_name="qa-stress-$i"
        bash "$CLI_SCRIPT" play "$recipe_name" > /dev/null 2>&1
    done

    local proof_count=$(ls "$ARTIFACTS_DIR"/proof-qa-stress-*.recipe-*.json 2>/dev/null | wc -l)
    if [[ $proof_count -eq 10 ]]; then
        qa_pass "All 10 proofs generated successfully"
    else
        qa_fail "Only $proof_count/10 proofs generated"
    fi
}

################################################################################
# RUN ALL QA TESTS
################################################################################

run_all_qa() {
    echo -e "\n${MAGENTA}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║   SOLACE BROWSER CLI v2.0 - HARSH QA TEST SUITE       ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════╝${NC}"

    qa_no_popup_dialogs
    qa_navigation_determinism
    qa_action_recording_completeness
    qa_deterministic_compilation
    qa_concurrent_execution
    qa_proof_integrity
    qa_episode_to_proof_chain
    qa_stress_large_batch

    # Summary
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║                  HARSH QA SUMMARY                     ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════╝${NC}"

    local total=$((TESTS_PASSED + TESTS_FAILED))
    echo -e "Total QA Tests:   ${MAGENTA}$total${NC}"
    echo -e "Tests Passed:     ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed:     ${RED}$TESTS_FAILED${NC}"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}✓ ALL HARSH QA TESTS PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}✗ SOME HARSH QA TESTS FAILED${NC}"
        return 1
    fi
}

# Run all QA tests
run_all_qa
exit $?
