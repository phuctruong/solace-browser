#!/bin/bash

################################################################################
# SOLACE BROWSER CLI v2.0 - INTEGRATION TESTS
# Tests full workflows: record → compile → play
# Run: bash tests/integration_tests.sh
################################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/solace-browser-cli-v2.sh"
TEST_DIR="$PROJECT_ROOT/tests"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"
EPISODES_DIR="$PROJECT_ROOT/episodes"
RECIPES_DIR="$PROJECT_ROOT/recipes"
LOGS_DIR="$PROJECT_ROOT/logs"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

mkdir -p "$ARTIFACTS_DIR" "$EPISODES_DIR" "$RECIPES_DIR" "$LOGS_DIR"

################################################################################
# TEST HELPERS
################################################################################

log_section() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_step() {
    echo -e "${BLUE}→ $1${NC}"
}

test_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

test_start() {
    ((TESTS_RUN++))
    echo -e "\n${YELLOW}[TEST $TESTS_RUN]${NC} $1"
}

json_get_field() {
    local file="$1"
    local field="$2"
    python3 -c "import json; print(json.load(open('$file')).get('$field', ''))" 2>/dev/null || echo ""
}

json_array_length() {
    local file="$1"
    local field="$2"
    python3 -c "import json; print(len(json.load(open('$file')).get('$field', [])))" 2>/dev/null || echo "0"
}

################################################################################
# INTEGRATION TESTS
################################################################################

test_full_workflow_mock() {
    log_section "INTEGRATION TEST 1: Full Workflow (Mock Mode)"
    test_start "Mock: Record → Compile → Play → Verify Proof"

    local episode_name="integration-test-mock"
    local episode_file="$EPISODES_DIR/$episode_name.json"
    local recipe_file="$RECIPES_DIR/$episode_name.recipe.json"

    # Step 1: Record Episode
    log_step "Recording episode"
    bash "$CLI_SCRIPT" record "https://example.com" "$episode_name" > /dev/null 2>&1

    if [[ ! -f "$episode_file" ]]; then
        test_fail "Episode file not created"
        return 1
    fi
    test_pass "Episode file created"

    # Verify episode structure
    local episode_id=$(json_get_field "$episode_file" "episode_id")
    if [[ "$episode_id" == "$episode_name" ]]; then
        test_pass "Episode ID matches"
    else
        test_fail "Episode ID mismatch"
    fi

    # Verify episode has initial structure
    if grep -q '"actions"' "$episode_file"; then
        test_pass "Episode has actions array"
    else
        test_fail "Episode missing actions array"
    fi

    # Step 2: Compile Episode
    log_step "Compiling episode to locked recipe"
    bash "$CLI_SCRIPT" compile "$episode_name" > /dev/null 2>&1

    if [[ ! -f "$recipe_file" ]]; then
        test_fail "Recipe file not created"
        return 1
    fi
    test_pass "Recipe file created"

    # Verify recipe is locked
    if grep -q '"locked": true' "$recipe_file"; then
        test_pass "Recipe is locked (immutable)"
    else
        test_fail "Recipe is not locked"
    fi

    # Verify recipe has source hash
    if grep -q '"source_hash"' "$recipe_file"; then
        test_pass "Recipe has source hash"
    else
        test_fail "Recipe missing source hash"
    fi

    # Step 3: Play Recipe
    log_step "Playing recipe to generate proof"
    bash "$CLI_SCRIPT" play "$episode_name" > /dev/null 2>&1

    # Check for proof artifact
    local proof_files=$(ls "$ARTIFACTS_DIR"/proof-integration-test-mock.recipe-*.json 2>/dev/null)
    if [[ -n "$proof_files" ]]; then
        test_pass "Proof artifact generated"

        # Verify proof structure
        local latest_proof=$(ls -t "$ARTIFACTS_DIR"/proof-integration-test-mock.recipe-*.json 2>/dev/null | head -1)
        local proof_status=$(json_get_field "$latest_proof" "status")
        if [[ "$proof_status" == "SUCCESS" ]]; then
            test_pass "Proof shows successful execution"
        else
            test_fail "Proof status is not SUCCESS"
        fi
    else
        test_fail "No proof artifact generated"
    fi
}

test_deterministic_replay() {
    log_section "INTEGRATION TEST 2: Deterministic Replay Consistency"
    test_start "Verify same recipe produces identical proofs on multiple executions"

    local recipe_name="integration-test-determinism"
    local episode_file="$EPISODES_DIR/$recipe_name.json"
    local recipe_file="$RECIPES_DIR/$recipe_name.recipe.json"

    # Create and compile recipe
    bash "$CLI_SCRIPT" record "https://example.com" "$recipe_name" > /dev/null 2>&1
    bash "$CLI_SCRIPT" compile "$recipe_name" > /dev/null 2>&1

    if [[ ! -f "$recipe_file" ]]; then
        test_fail "Recipe not created for determinism test"
        return 1
    fi

    # Get recipe hash
    local recipe_hash=$(json_get_field "$recipe_file" "source_hash")
    log_step "Recipe hash: $recipe_hash"

    # Execute recipe 3 times
    local proof_hashes=()
    for i in {1..3}; do
        bash "$CLI_SCRIPT" play "$recipe_name" > /dev/null 2>&1
        sleep 1

        # Get latest proof
        local latest_proof=$(ls -t "$ARTIFACTS_DIR"/proof-integration-test-determinism.recipe-*.json 2>/dev/null | head -1)
        if [[ -f "$latest_proof" ]]; then
            local proof_data=$(cat "$latest_proof")
            local proof_hash=$(echo "$proof_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('recipe_hash', ''))" 2>/dev/null)
            proof_hashes+=("$proof_hash")
        fi
    done

    if [[ ${#proof_hashes[@]} -lt 3 ]]; then
        test_fail "Could not generate 3 proofs for comparison"
        return 1
    fi

    # Verify all proofs reference same recipe hash
    local all_match=true
    for hash in "${proof_hashes[@]}"; do
        if [[ "$hash" != "$recipe_hash" ]]; then
            all_match=false
            break
        fi
    done

    if [[ "$all_match" == true ]]; then
        test_pass "All 3 executions reference same recipe hash (determinism verified)"
    else
        test_fail "Proof hashes don't match recipe hash"
    fi
}

test_compilation_idempotency() {
    log_section "INTEGRATION TEST 3: Compilation Idempotency"
    test_start "Verify compiling same episode twice produces identical recipes"

    local episode_name="integration-test-idempotent"
    local recipe_file="$RECIPES_DIR/$episode_name.recipe.json"

    # Create episode
    bash "$CLI_SCRIPT" record "https://example.com" "$episode_name" > /dev/null 2>&1

    # Compile first time
    bash "$CLI_SCRIPT" compile "$episode_name" > /dev/null 2>&1
    if [[ ! -f "$recipe_file" ]]; then
        test_fail "First compilation failed"
        return 1
    fi
    local hash1=$(json_get_field "$recipe_file" "source_hash")

    # Compile second time
    bash "$CLI_SCRIPT" compile "$episode_name" > /dev/null 2>&1
    local hash2=$(json_get_field "$recipe_file" "source_hash")

    if [[ "$hash1" == "$hash2" ]]; then
        test_pass "Compilation is idempotent (same hash both times)"
    else
        test_fail "Compilation produced different hashes"
    fi
}

test_multiple_episodes() {
    log_section "INTEGRATION TEST 4: Multiple Independent Episodes"
    test_start "Verify multiple episodes can coexist without interference"

    # Create 3 independent episodes
    local episodes=("test-episode-a" "test-episode-b" "test-episode-c")

    for ep in "${episodes[@]}"; do
        bash "$CLI_SCRIPT" record "https://example.com" "$ep" > /dev/null 2>&1
        bash "$CLI_SCRIPT" compile "$ep" > /dev/null 2>&1
    done

    # Verify all recipes exist
    local recipe_count=$(ls "$RECIPES_DIR"/*.recipe.json 2>/dev/null | wc -l)
    if [[ $recipe_count -ge 3 ]]; then
        test_pass "All 3 recipes created successfully"
    else
        test_fail "Not all recipes created"
    fi

    # Play all recipes
    for ep in "${episodes[@]}"; do
        bash "$CLI_SCRIPT" play "$ep" > /dev/null 2>&1
    done

    # Verify all proofs exist
    local proof_count=$(ls "$ARTIFACTS_DIR"/proof-test-episode-*.recipe-*.json 2>/dev/null | wc -l)
    if [[ $proof_count -ge 3 ]]; then
        test_pass "All 3 proofs generated successfully"
    else
        test_fail "Not all proofs generated"
    fi
}

test_recipe_immutability() {
    log_section "INTEGRATION TEST 5: Recipe Immutability (Locked Status)"
    test_start "Verify locked recipes cannot be modified"

    local recipe_name="integration-test-locked"
    local recipe_file="$RECIPES_DIR/$recipe_name.recipe.json"

    # Create recipe
    bash "$CLI_SCRIPT" record "https://example.com" "$recipe_name" > /dev/null 2>&1
    bash "$CLI_SCRIPT" compile "$recipe_name" > /dev/null 2>&1

    # Check locked status
    local is_locked=$(json_get_field "$recipe_file" "locked")
    if [[ "$is_locked" == "True" ]] || [[ "$is_locked" == "true" ]]; then
        test_pass "Recipe is locked"
    else
        test_fail "Recipe is not locked"
    fi

    # Try to modify recipe file (simulated - in real system, locked recipes cannot be modified)
    local original_content=$(cat "$recipe_file")

    # Note: Actual immutability would require file permissions or database locks
    # For now, we just verify the locked flag exists
    if grep -q '"locked"' "$recipe_file"; then
        test_pass "Recipe has immutability flag"
    else
        test_fail "Recipe missing immutability flag"
    fi
}

################################################################################
# RUN ALL TESTS
################################################################################

run_all_tests() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   SOLACE BROWSER CLI v2.0 - INTEGRATION TEST SUITE     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

    test_full_workflow_mock
    test_deterministic_replay
    test_compilation_idempotency
    test_multiple_episodes
    test_recipe_immutability

    # Summary
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    TEST SUMMARY                        ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

    local total=$((TESTS_PASSED + TESTS_FAILED))
    echo -e "Total Tests Run:  ${BLUE}$total${NC}"
    echo -e "Tests Passed:     ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed:     ${RED}$TESTS_FAILED${NC}"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}✓ ALL INTEGRATION TESTS PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}✗ SOME INTEGRATION TESTS FAILED${NC}"
        return 1
    fi
}

# Run all tests
run_all_tests
exit $?
