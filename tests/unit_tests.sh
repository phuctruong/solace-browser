#!/bin/bash

################################################################################
# SOLACE BROWSER CLI v2.0 - UNIT TESTS
# Tests each CLI function in isolation
# Run: bash tests/unit_tests.sh
################################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/solace-browser-cli-v2.sh"
TEST_DIR="$PROJECT_ROOT/tests"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"
LOGS_DIR="$PROJECT_ROOT/logs"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

mkdir -p "$ARTIFACTS_DIR" "$LOGS_DIR"

################################################################################
# TEST HELPERS
################################################################################

log_test_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}TEST: $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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
    echo -e "${YELLOW}Running test $TESTS_RUN: $1${NC}"
}

assert_file_exists() {
    local file="$1"
    if [[ -f "$file" ]]; then
        test_pass "File exists: $file"
        return 0
    else
        test_fail "File not found: $file"
        return 1
    fi
}

assert_json_valid() {
    local file="$1"
    if python3 -m json.tool "$file" > /dev/null 2>&1; then
        test_pass "Valid JSON: $file"
        return 0
    else
        test_fail "Invalid JSON: $file"
        return 1
    fi
}

assert_contains() {
    local file="$1"
    local pattern="$2"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        test_pass "File contains: $pattern"
        return 0
    else
        test_fail "File missing: $pattern"
        return 1
    fi
}

################################################################################
# UNIT TESTS
################################################################################

test_cdp_detection() {
    log_test_header "CDP Detection (Browser Availability)"
    test_start "Verify curl can reach CDP endpoint"

    # Try to detect browser
    if bash "$CLI_SCRIPT" browser-info > /dev/null 2>&1; then
        test_pass "Browser detected on CDP port"
    else
        test_fail "Browser not running (expected for isolated test - may be OK)"
    fi
}

test_browser_start() {
    log_test_header "Browser Start/Stop Lifecycle"
    test_start "Verify browser can start"

    # Kill any existing browser
    pkill -f "chrome|chromium" || true
    sleep 2

    # Try to start browser
    if bash "$CLI_SCRIPT" start > /dev/null 2>&1; then
        test_pass "Browser start command executed"

        # Check if browser is listening
        sleep 3
        if curl -s "http://localhost:9222/json/list" > /dev/null 2>&1; then
            test_pass "Browser listening on CDP port 9222"
        else
            test_fail "Browser not responding on CDP port"
        fi
    else
        test_fail "Browser start command failed"
    fi
}

test_navigate_to() {
    log_test_header "Navigate Function (CDP Page.navigate)"
    test_start "Verify navigate_to can send CDP command"

    # First ensure browser is running
    if ! curl -s "http://localhost:9222/json/list" > /dev/null 2>&1; then
        bash "$CLI_SCRIPT" start > /dev/null 2>&1
        sleep 3
    fi

    # Try navigation
    if bash "$CLI_SCRIPT" navigate test-episode "https://example.com" > /dev/null 2>&1; then
        test_pass "Navigate command executed"
    else
        test_fail "Navigate command failed"
    fi
}

test_click_element() {
    log_test_header "Click Element Function (CDP Runtime.evaluate)"
    test_start "Verify click_element can send CDP command"

    if bash "$CLI_SCRIPT" click test-episode "button.submit" > /dev/null 2>&1; then
        test_pass "Click command executed"
    else
        test_fail "Click command failed"
    fi
}

test_type_text() {
    log_test_header "Type Text Function (CDP Input.dispatchKeyEvent)"
    test_start "Verify type_text can send CDP command"

    if bash "$CLI_SCRIPT" fill test-episode "input#search" "test query" > /dev/null 2>&1; then
        test_pass "Type command executed"
    else
        test_fail "Type command failed"
    fi
}

test_screenshot() {
    log_test_header "Screenshot Function (CDP Page.captureScreenshot)"
    test_start "Verify take_screenshot can capture screenshot"

    if bash "$CLI_SCRIPT" screenshot "test-screenshot.png" > /dev/null 2>&1; then
        test_pass "Screenshot command executed"
        # Note: In real mode, file would be created. In mock mode, just command executed.
    else
        test_fail "Screenshot command failed"
    fi
}

test_snapshot() {
    log_test_header "Snapshot Function (CDP DOM.getOuterHTML)"
    test_start "Verify get_snapshot can retrieve DOM"

    if bash "$CLI_SCRIPT" snapshot > /dev/null 2>&1; then
        test_pass "Snapshot command executed"
    else
        test_fail "Snapshot command failed"
    fi
}

test_episode_creation() {
    log_test_header "Episode File Creation"
    test_start "Verify episode JSON is created with proper structure"

    local episode_file="$PROJECT_ROOT/episodes/unit-test-episode.json"

    # Create episode
    bash "$CLI_SCRIPT" record "https://example.com" "unit-test-episode" > /dev/null 2>&1

    # Verify file exists
    if assert_file_exists "$episode_file"; then
        # Verify JSON is valid
        if assert_json_valid "$episode_file"; then
            # Verify required fields
            if assert_contains "$episode_file" '"episode_id"'; then
                test_pass "Episode file has required fields"
            fi
        fi
    fi
}

test_recipe_compilation() {
    log_test_header "Recipe Compilation (Episode → Locked Recipe)"
    test_start "Verify compile creates locked recipe from episode"

    local episode_file="$PROJECT_ROOT/episodes/unit-test-episode.json"
    local recipe_file="$PROJECT_ROOT/recipes/unit-test-episode.recipe.json"

    # Ensure episode exists
    if [[ ! -f "$episode_file" ]]; then
        bash "$CLI_SCRIPT" record "https://example.com" "unit-test-episode" > /dev/null 2>&1
    fi

    # Compile
    bash "$CLI_SCRIPT" compile "unit-test-episode" > /dev/null 2>&1

    # Verify recipe
    if assert_file_exists "$recipe_file"; then
        if assert_json_valid "$recipe_file"; then
            if assert_contains "$recipe_file" '"locked": true'; then
                test_pass "Recipe is properly locked"
            fi
        fi
    fi
}

test_proof_generation() {
    log_test_header "Proof Generation (Recipe → Execution Proof)"
    test_start "Verify play generates valid proof artifact"

    local recipe_file="$PROJECT_ROOT/recipes/unit-test-episode.recipe.json"

    # Ensure recipe exists
    if [[ ! -f "$recipe_file" ]]; then
        bash "$CLI_SCRIPT" record "https://example.com" "unit-test-episode" > /dev/null 2>&1
        bash "$CLI_SCRIPT" compile "unit-test-episode" > /dev/null 2>&1
    fi

    # Play recipe
    bash "$CLI_SCRIPT" play "unit-test-episode" > /dev/null 2>&1

    # Check for proof artifact
    local proof_count=$(ls "$ARTIFACTS_DIR"/proof-unit-test-episode.recipe-*.json 2>/dev/null | wc -l)
    if [[ $proof_count -gt 0 ]]; then
        test_pass "Proof artifact created"

        # Verify proof JSON
        local latest_proof=$(ls -t "$ARTIFACTS_DIR"/proof-unit-test-episode.recipe-*.json 2>/dev/null | head -1)
        if assert_json_valid "$latest_proof"; then
            if assert_contains "$latest_proof" '"status": "SUCCESS"'; then
                test_pass "Proof shows successful execution"
            fi
        fi
    else
        test_fail "No proof artifact created"
    fi
}

################################################################################
# RUN ALL TESTS
################################################################################

run_all_tests() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     SOLACE BROWSER CLI v2.0 - UNIT TEST SUITE          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Core tests
    test_cdp_detection
    test_browser_start
    test_navigate_to
    test_click_element
    test_type_text
    test_screenshot
    test_snapshot

    # Workflow tests
    test_episode_creation
    test_recipe_compilation
    test_proof_generation

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
        echo -e "\n${GREEN}✓ ALL TESTS PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}✗ SOME TESTS FAILED${NC}"
        return 1
    fi
}

# Run all tests
run_all_tests
exit $?
