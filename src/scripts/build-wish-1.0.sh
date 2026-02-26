#!/bin/bash
# WISH 1.0 RIPPLE: Build Infrastructure Setup
# Authority: 65537
# Implements: wish-1.0-build-infrastructure.md
# Tests: 5 exact tests (T1-T5) with Setup/Input/Expect/Verify

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

# Test tracking
mkdir -p "$ARTIFACTS_DIR"
test_counter=0
passed=0
failed=0

run_test() {
    local test_id=$1
    local test_name=$2
    test_counter=$((test_counter + 1))

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST $test_counter: $test_id - $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

pass_test() {
    log_pass "$1"
    passed=$((passed + 1))
}

fail_test() {
    log_fail "$1"
    failed=$((failed + 1))
}

# ============================================================================
# BANNER
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ WISH 1.0 RIPPLE: Build Infrastructure Setup                   ║"
echo "║ Authority: 65537 | Phase: 1 (Fork & Setup)                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# TEST 1: GN Tool Available
# ============================================================================

test_T1() {
    run_test "T1" "GN Tool Available"

    log_info "Setup: System PATH includes /usr/bin"
    log_info "Input: which gn"

    if gn_path=$(which gn 2>/dev/null); then
        log_pass "GN found at $gn_path"

        if gn_version=$(gn --version 2>&1); then
            log_info "GN version: $gn_version"
            log_pass "gn --version works"

            # Verify version is >= 1.0
            major_version=$(echo "$gn_version" | grep -oE "^[0-9]+" || echo "0")
            if [[ $major_version -ge 1 ]]; then
                log_pass "T1: GN Tool Available ✓"
                pass_test "T1-gn-available"
                return 0
            else
                log_fail "GN version too old: $gn_version"
                fail_test "T1-gn-available"
                return 1
            fi
        else
            log_fail "gn --version failed"
            fail_test "T1-gn-available"
            return 1
        fi
    else
        log_fail "GN not found in PATH"
        fail_test "T1-gn-available"
        return 1
    fi
}

# ============================================================================
# TEST 2: Ninja Tool Available
# ============================================================================

test_T2() {
    run_test "T2" "Ninja Tool Available"

    log_info "Setup: System PATH includes /usr/bin"
    log_info "Input: which ninja"

    if ninja_path=$(which ninja 2>/dev/null); then
        log_pass "Ninja found at $ninja_path"

        if ninja_version=$(ninja --version 2>&1); then
            log_info "Ninja version: $ninja_version"
            log_pass "ninja --version works"

            log_pass "T2: Ninja Tool Available ✓"
            pass_test "T2-ninja-available"
            return 0
        else
            log_fail "ninja --version failed"
            fail_test "T2-ninja-available"
            return 1
        fi
    else
        log_fail "Ninja not found in PATH"
        fail_test "T2-ninja-available"
        return 1
    fi
}

# ============================================================================
# TEST 3: Build Script Exists & Executable
# ============================================================================

test_T3() {
    run_test "T3" "Build Script Exists & Executable"

    local build_script="$PROJECT_ROOT/build_solace.sh"
    log_info "Setup: Current directory = $PROJECT_ROOT"
    log_info "Input: ls -la $build_script"

    if [[ -f "$build_script" ]]; then
        log_pass "build_solace.sh exists"

        if [[ -x "$build_script" ]]; then
            log_pass "build_solace.sh is executable"
        else
            log_warn "build_solace.sh not executable, making it so..."
            chmod +x "$build_script"
            log_pass "build_solace.sh is now executable"
        fi

        # Verify bash shebang
        if head -1 "$build_script" | grep -q "^#!/bin/bash"; then
            log_pass "Bash shebang found"

            # Verify readable
            if [[ -r "$build_script" ]]; then
                log_pass "build_solace.sh is readable"
                log_pass "T3: Build Script Valid ✓"
                pass_test "T3-build-script"
                return 0
            else
                log_fail "build_solace.sh not readable"
                fail_test "T3-build-script"
                return 1
            fi
        else
            log_fail "build_solace.sh missing bash shebang"
            fail_test "T3-build-script"
            return 1
        fi
    else
        log_fail "build_solace.sh not found at $build_script"
        fail_test "T3-build-script"
        return 1
    fi
}

# ============================================================================
# TEST 4: Directory Structure Correct
# ============================================================================

test_T4() {
    run_test "T4" "Directory Structure Correct"

    log_info "Setup: Current directory = $PROJECT_ROOT"
    log_info "Input: Check required directories exist"

    local required_dirs=("source_full" "out" "artifacts" "canon" "scripts")
    local all_exist=true

    for dir in "${required_dirs[@]}"; do
        dir_path="$PROJECT_ROOT/$dir"
        if [[ -d "$dir_path" ]]; then
            log_pass "$dir/ exists"
        else
            log_fail "$dir/ missing"
            all_exist=false
        fi
    done

    if [[ "$all_exist" == true ]]; then
        log_pass "T4: Directory Structure Correct ✓"
        pass_test "T4-directory-structure"
        return 0
    else
        log_fail "Some required directories missing"
        fail_test "T4-directory-structure"
        return 1
    fi
}

# ============================================================================
# TEST 5: Project Configuration & Files Present
# ============================================================================

test_T5() {
    run_test "T5" "Project Configuration & Files Present"

    log_info "Setup: Current directory = $PROJECT_ROOT"
    log_info "Input: Check key files exist"

    local required_files=("README.md" ".claude" "canon" "scripts")
    local all_exist=true

    for file in "${required_files[@]}"; do
        file_path="$PROJECT_ROOT/$file"
        if [[ -e "$file_path" ]]; then
            log_pass "$file exists"
        else
            log_fail "$file missing"
            all_exist=false
        fi
    done

    if [[ "$all_exist" == true ]]; then
        log_pass "T5: Project Configuration Valid ✓"
        pass_test "T5-project-config"
        return 0
    else
        log_fail "Some required files missing"
        fail_test "T5-project-config"
        return 1
    fi
}

# ============================================================================
# RUN ALL TESTS
# ============================================================================

test_T1 || true
test_T2 || true
test_T3 || true
test_T4 || true
test_T5 || true

# ============================================================================
# SUMMARY & PROOF ARTIFACTS
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ TEST SUMMARY                                                   ║"
echo "╠════════════════════════════════════════════════════════════════╣"
printf "║ Total:  %d tests                                         ║\n" "$test_counter"
printf "║ Passed: %d tests                                         ║\n" "$passed"
printf "║ Failed: %d tests                                         ║\n" "$failed"

if [[ $failed -eq 0 ]]; then
    echo "║ Status: ✅ ALL PASSED                                           ║"
    status_code=0
else
    echo "║ Status: ❌ SOME FAILED                                           ║"
    status_code=1
fi

echo "╚════════════════════════════════════════════════════════════════╝"

# Generate proof.json
proof_json="$ARTIFACTS_DIR/proof.json"
cat > "$proof_json" <<EOF
{
  "spec_id": "wish-1.0-build-infrastructure",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "authority": "65537",
  "tests_passed": $passed,
  "tests_failed": $failed,
  "tests_total": $test_counter,
  "status": $([ $failed -eq 0 ] && echo '"SUCCESS"' || echo '"FAILED"'),
  "tools": {
    "gn": "$(which gn 2>/dev/null || echo 'NOT FOUND')",
    "ninja": "$(which ninja 2>/dev/null || echo 'NOT FOUND')",
    "gn_version": "$(gn --version 2>/dev/null || echo 'UNKNOWN')",
    "ninja_version": "$(ninja --version 2>/dev/null || echo 'UNKNOWN')"
  },
  "directories": {
    "project_root": "$PROJECT_ROOT",
    "artifacts": "$ARTIFACTS_DIR"
  }
}
EOF

log_info "Proof artifact saved to: $proof_json"

# Summary message
echo ""
if [[ $failed -eq 0 ]]; then
    log_pass "WISH 1.0 COMPLETE: Build infrastructure verified ✅"
    log_info "Next phase: wish-1.0b (Source Fetch) or wish-1.1 (Compilation)"
    echo ""
    exit 0
else
    log_fail "WISH 1.0 FAILED: $failed test(s) failed ❌"
    echo ""
    exit 1
fi
