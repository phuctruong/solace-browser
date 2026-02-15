#!/bin/bash

################################################################################
# QUICK VALIDATION TEST - Simplified, Fast Verification
# Tests the core workflow without browser startup
# Run: bash tests/quick_validation.sh
################################################################################

set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/solace-browser-cli-v2.sh"
EPISODES_DIR="$PROJECT_ROOT/episodes"
RECIPES_DIR="$PROJECT_ROOT/recipes"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  QUICK VALIDATION - Core Workflow Test                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

# Test 1: Record Episode
echo -e "${YELLOW}[1/5]${NC} Testing: Record Episode"
EPISODE_NAME="quick-validation-$(date +%s)"
if timeout 5 bash "$CLI_SCRIPT" record "https://example.com" "$EPISODE_NAME" > /dev/null 2>&1; then
    if [[ -f "$EPISODES_DIR/$EPISODE_NAME.json" ]]; then
        echo -e "${GREEN}✓ PASS${NC}: Episode created successfully"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: Episode file not found"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}✗ FAIL${NC}: Record command failed"
    ((TESTS_FAILED++))
fi

# Test 2: Compile Recipe
echo -e "${YELLOW}[2/5]${NC} Testing: Compile Episode to Recipe"
if timeout 5 bash "$CLI_SCRIPT" compile "$EPISODE_NAME" > /dev/null 2>&1; then
    RECIPE_FILE="$RECIPES_DIR/$EPISODE_NAME.recipe.json"
    if [[ -f "$RECIPE_FILE" ]]; then
        # Verify it has locked=true
        if grep -q '"locked": true' "$RECIPE_FILE"; then
            echo -e "${GREEN}✓ PASS${NC}: Recipe compiled and locked"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC}: Recipe not locked"
            ((TESTS_FAILED++))
        fi
    else
        echo -e "${RED}✗ FAIL${NC}: Recipe file not found"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}✗ FAIL${NC}: Compile command failed"
    ((TESTS_FAILED++))
fi

# Test 3: Play Recipe
echo -e "${YELLOW}[3/5]${NC} Testing: Play Recipe (Generate Proof)"
if timeout 5 bash "$CLI_SCRIPT" play "$EPISODE_NAME" > /dev/null 2>&1; then
    # Check if proof was generated
    PROOF_COUNT=$(ls "$ARTIFACTS_DIR"/proof-$EPISODE_NAME.recipe-*.json 2>/dev/null | wc -l)
    if [[ $PROOF_COUNT -gt 0 ]]; then
        echo -e "${GREEN}✓ PASS${NC}: Proof artifact generated"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: Proof artifact not found"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}✗ FAIL${NC}: Play command failed"
    ((TESTS_FAILED++))
fi

# Test 4: Verify JSON Structure
echo -e "${YELLOW}[4/5]${NC} Testing: JSON Structure Validation"
PROOF_FILE=$(ls "$ARTIFACTS_DIR"/proof-$EPISODE_NAME.recipe-*.json 2>/dev/null | head -1)
if [[ -n "$PROOF_FILE" ]]; then
    if python3 -m json.tool "$PROOF_FILE" > /dev/null 2>&1; then
        # Verify required fields
        if grep -q '"status": "SUCCESS"' "$PROOF_FILE" && \
           grep -q '"recipe_id"' "$PROOF_FILE" && \
           grep -q '"proof_id"' "$PROOF_FILE"; then
            echo -e "${GREEN}✓ PASS${NC}: Proof has valid structure"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC}: Proof missing required fields"
            ((TESTS_FAILED++))
        fi
    else
        echo -e "${RED}✗ FAIL${NC}: Proof JSON is invalid"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}✗ FAIL${NC}: No proof file to validate"
    ((TESTS_FAILED++))
fi

# Test 5: CLI Syntax & Help
echo -e "${YELLOW}[5/5]${NC} Testing: CLI Syntax & Commands"
if timeout 5 bash "$CLI_SCRIPT" help > /dev/null 2>&1; then
    # Verify help output contains expected commands
    HELP_OUTPUT=$(bash "$CLI_SCRIPT" help 2>&1)
    if echo "$HELP_OUTPUT" | grep -q "record" && \
       echo "$HELP_OUTPUT" | grep -q "compile" && \
       echo "$HELP_OUTPUT" | grep -q "play"; then
        echo -e "${GREEN}✓ PASS${NC}: CLI syntax and commands valid"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: Help output missing commands"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}✗ FAIL${NC}: CLI help failed"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    SUMMARY                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED/5${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED/5${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "Core workflow verified:"
    echo "  1. Episode created: $EPISODES_DIR/$EPISODE_NAME.json"
    echo "  2. Recipe compiled: $RECIPES_DIR/$EPISODE_NAME.recipe.json"
    echo "  3. Proof generated: $PROOF_FILE"
    echo ""
    echo "✨ Implementation working correctly!"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
