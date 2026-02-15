#!/bin/bash

################################################################################
# SOLACE BROWSER - QUICK CDP TESTS
# Minimal tests to verify CDP integration is working
# Assumes browser is already running on port 9222
################################################################################

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/solace-browser-cli-v2.sh"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo -e "${GREEN}✓${NC} $*"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $*"
    ((TESTS_FAILED++))
}

echo -e "\n${BLUE}═════════════════════════════════════════${NC}"
echo -e "${BLUE}SOLACE BROWSER - QUICK CDP TESTS${NC}"
echo -e "${BLUE}═════════════════════════════════════════${NC}\n"

# Test 1: Browser detection
echo "Test 1: Browser Detection..."
if bash "$CLI_SCRIPT" browser-info > /dev/null 2>&1; then
    pass "Browser detected on CDP port 9222"
else
    fail "Browser not detected"
fi

# Test 2: Navigation
echo -e "\nTest 2: Navigation..."
if bash "$CLI_SCRIPT" navigate test-episode "https://example.com" > /dev/null 2>&1; then
    pass "Navigate command executed"
else
    fail "Navigate command failed"
fi

# Test 3: Screenshot
echo -e "\nTest 3: Screenshot..."
if bash "$CLI_SCRIPT" screenshot "test.png" > /dev/null 2>&1; then
    pass "Screenshot command executed"
else
    fail "Screenshot command failed"
fi

# Test 4: Click element
echo -e "\nTest 4: Click Element..."
if bash "$CLI_SCRIPT" click test-episode "button" > /dev/null 2>&1; then
    pass "Click command executed"
else
    fail "Click command failed"
fi

# Test 5: Fill (type text)
echo -e "\nTest 5: Fill/Type Text..."
if bash "$CLI_SCRIPT" fill test-episode "input" "test data" > /dev/null 2>&1; then
    pass "Fill command executed"
else
    fail "Fill command failed"
fi

# Test 6: Episode creation
echo -e "\nTest 6: Episode Creation..."
if bash "$CLI_SCRIPT" record "https://example.com" "quick-test" > /dev/null 2>&1; then
    if [[ -f "$PROJECT_ROOT/episodes/quick-test.json" ]]; then
        pass "Episode file created"
    else
        fail "Episode file not created"
    fi
else
    fail "Record command failed"
fi

# Test 7: Recipe compilation
echo -e "\nTest 7: Recipe Compilation..."
if bash "$CLI_SCRIPT" compile "quick-test" > /dev/null 2>&1; then
    if [[ -f "$PROJECT_ROOT/recipes/quick-test.recipe.json" ]]; then
        pass "Recipe file created"
    else
        fail "Recipe file not created"
    fi
else
    fail "Compile command failed"
fi

# Test 8: Proof generation
echo -e "\nTest 8: Proof Generation..."
if bash "$CLI_SCRIPT" play "quick-test" > /dev/null 2>&1; then
    PROOF_COUNT=$(ls "$PROJECT_ROOT/artifacts"/proof-quick-test.recipe-*.json 2>/dev/null | wc -l)
    if [[ $PROOF_COUNT -gt 0 ]]; then
        pass "Proof artifact created ($PROOF_COUNT files)"
    else
        fail "No proof artifacts created"
    fi
else
    fail "Play command failed"
fi

# Summary
echo -e "\n${BLUE}═════════════════════════════════════════${NC}"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "${BLUE}═════════════════════════════════════════${NC}\n"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}\n"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}\n"
    exit 1
fi
