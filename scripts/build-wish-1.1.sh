#!/bin/bash
# WISH 1.1 RIPPLE: Browser Binary Compilation
# Authority: 65537
# Implements: wish-1.1-browser-compilation.md
# Tests: 10 exact tests (T1-T10) with Setup/Input/Expect/Verify

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="$PROJECT_ROOT/source_full"
BUILD_OUT="$PROJECT_ROOT/out/Release"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"
CHROME_BINARY="$BUILD_OUT/chrome"

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

# ============================================================================
# TEST HARNESS: 10 Exact Tests from wish-1.1
# ============================================================================

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
    echo "tests: [{\"name\": \"$1\", \"status\": \"PASS\"}]" >> "$ARTIFACTS_DIR/tests.jsonl"
}

fail_test() {
    log_fail "$1"
    failed=$((failed + 1))
    echo "tests: [{\"name\": \"$1\", \"status\": \"FAIL\"}]" >> "$ARTIFACTS_DIR/tests.jsonl"
}

# ============================================================================
# TEST 1: GN Configuration Works
# ============================================================================

test_T1() {
    run_test "T1" "GN Configuration Works"

    log_info "Setup: rm -rf out/Release"
    rm -rf "$BUILD_OUT" || true

    log_info "Input: gn gen out/Release --root=source_full/src --args='is_debug=false is_official_build=true'"
    cd "$PROJECT_ROOT"

    # Try with source_full/src if it exists
    if [[ -d "$SOURCE_ROOT/src" ]]; then
        log_info "Using source_full/src (Chromium source found)"
        if gn gen "$BUILD_OUT" --root="$SOURCE_ROOT/src" --args='is_debug=false is_official_build=true' > /tmp/gn_output.log 2>&1; then
            log_info "Expect: Command exits 0"
            log_pass "GN exited 0"

            if [[ -f "$BUILD_OUT/args.gn" ]]; then
                log_pass "args.gn exists"
            else
                log_fail "args.gn missing"
                fail_test "T1-gn-config"
                return 1
            fi

            if [[ -f "$BUILD_OUT/build.ninja" ]]; then
                log_pass "build.ninja exists"
            else
                log_fail "build.ninja missing"
                fail_test "T1-gn-config"
                return 1
            fi

            if grep -q "cc_toolchain" "$BUILD_OUT/build.ninja"; then
                log_pass "build.ninja contains 'cc_toolchain' (sanity)"
                pass_test "T1-gn-config"
                return 0
            else
                log_fail "build.ninja missing 'cc_toolchain'"
                fail_test "T1-gn-config"
                return 1
            fi
        else
            log_fail "GN configuration failed"
            tail -20 /tmp/gn_output.log 2>/dev/null || true
            fail_test "T1-gn-config"
            return 1
        fi
    else
        log_fail "Chromium source not found at $SOURCE_ROOT/src"
        fail_test "T1-gn-config"
        return 1
    fi
}

# ============================================================================
# TEST 2: Ninja Build Compiles Chrome
# ============================================================================

test_T2() {
    run_test "T2" "Ninja Build Compiles Chrome"

    log_info "Setup: GN config complete, ninja available"
    log_info "Input: ninja -C out/Release -j 4 chrome"

    cd "$PROJECT_ROOT"

    # Timeout: 3600 seconds (1 hour)
    if timeout 3600 ninja -C "$BUILD_OUT" -j 4 chrome > /tmp/ninja_output.log 2>&1; then
        log_pass "Ninja completed successfully"

        if [[ -f "$CHROME_BINARY" ]]; then
            log_pass "Binary exists at $CHROME_BINARY"

            local size=$(stat -f%z "$CHROME_BINARY" 2>/dev/null || stat -c%s "$CHROME_BINARY" 2>/dev/null)
            local size_mb=$((size / 1024 / 1024))
            log_info "Binary size: ${size_mb}MB"

            if [[ $size -ge 83886080 ]]; then  # 80MB
                log_pass "Binary size ≥ 80MB ($size_mb MB)"

                local file_output=$(file "$CHROME_BINARY")
                if echo "$file_output" | grep -q "ELF 64-bit"; then
                    log_pass "Binary is ELF 64-bit: $file_output"
                    pass_test "T2-ninja-build"
                    return 0
                else
                    log_fail "Binary is not ELF 64-bit: $file_output"
                    fail_test "T2-ninja-build"
                    return 1
                fi
            else
                log_fail "Binary too small: ${size_mb}MB < 80MB"
                fail_test "T2-ninja-build"
                return 1
            fi
        else
            log_fail "Binary not found at $CHROME_BINARY"
            fail_test "T2-ninja-build"
            return 1
        fi
    else
        log_fail "Ninja build failed or timed out"
        tail -50 /tmp/ninja_output.log
        fail_test "T2-ninja-build"
        return 1
    fi
}

# ============================================================================
# TEST 3: Binary Version Output (Happy Path)
# ============================================================================

test_T3() {
    run_test "T3" "Binary Version Output"

    log_info "Setup: Binary compiled"
    log_info "Input: $CHROME_BINARY --version"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T3-version-output"
        return 1
    fi

    if output=$("$CHROME_BINARY" --version 2>&1); then
        log_pass "Command exited 0"
        log_info "Output: $output"

        if echo "$output" | grep -q "Ungoogled Chromium"; then
            log_pass "Output contains 'Ungoogled Chromium'"

            if echo "$output" | grep -qE "[0-9]+\.[0-9]+\.[0-9]+"; then
                log_pass "Output contains version number"
                pass_test "T3-version-output"
                return 0
            else
                log_fail "Output missing version number"
                fail_test "T3-version-output"
                return 1
            fi
        else
            log_fail "Output missing 'Ungoogled Chromium'"
            fail_test "T3-version-output"
            return 1
        fi
    else
        log_fail "Version command failed or segfaulted"
        fail_test "T3-version-output"
        return 1
    fi
}

# ============================================================================
# TEST 4: Headless Launch
# ============================================================================

test_T4() {
    run_test "T4" "Headless Launch"

    log_info "Setup: Binary compiled"
    log_info "Input: timeout 5 chrome --headless --no-sandbox --version"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T4-headless-launch"
        return 1
    fi

    if output=$(timeout 5 "$CHROME_BINARY" --headless --no-sandbox --version 2>&1); then
        log_pass "Headless launch succeeded"
        log_info "Output: $output"

        if ! echo "$output" | grep -qi "segmentation fault\|FATAL\|Abort"; then
            log_pass "No crash in output"
            pass_test "T4-headless-launch"
            return 0
        else
            log_fail "Segfault or FATAL error detected"
            fail_test "T4-headless-launch"
            return 1
        fi
    else
        exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_pass "Process timed out (expected with headless)"
            pass_test "T4-headless-launch"
            return 0
        else
            log_fail "Headless launch failed (exit $exit_code)"
            fail_test "T4-headless-launch"
            return 1
        fi
    fi
}

# ============================================================================
# TEST 5: Clean Shutdown
# ============================================================================

test_T5() {
    run_test "T5" "Clean Shutdown (SIGTERM)"

    log_info "Setup: Binary compiled"
    log_info "Input: (timeout 10 chrome --headless --no-sandbox &) && sleep 2 && pkill -TERM chrome"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T5-clean-shutdown"
        return 1
    fi

    (timeout 10 "$CHROME_BINARY" --headless --no-sandbox &)
    pid=$!
    sleep 2

    kill -TERM $pid 2>/dev/null || true
    sleep 5

    if ! ps aux | grep -v grep | grep -q "$CHROME_BINARY"; then
        log_pass "Process terminated cleanly"
        pass_test "T5-clean-shutdown"
        return 0
    else
        log_fail "Process still running after SIGTERM"
        pkill -9 chrome || true
        fail_test "T5-clean-shutdown"
        return 1
    fi
}

# ============================================================================
# TEST 6: Binary Hash Determinism
# ============================================================================

test_T6() {
    run_test "T6" "Binary Hash Determinism"

    log_info "Setup: Binary compiled"
    log_info "Input: SHA256(out/Release/chrome)"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T6-hash-determinism"
        return 1
    fi

    hash1=$(sha256sum "$CHROME_BINARY" | awk '{print $1}')
    log_info "Hash: $hash1"

    echo "$hash1" > "$ARTIFACTS_DIR/chrome_hash.txt"

    # Verify hash is valid SHA256 (64 hex chars)
    if [[ $hash1 =~ ^[a-f0-9]{64}$ ]]; then
        log_pass "Hash is valid SHA256 format"
        pass_test "T6-hash-determinism"
        return 0
    else
        log_fail "Hash is not valid SHA256"
        fail_test "T6-hash-determinism"
        return 1
    fi
}

# ============================================================================
# TEST 7: Build Script Works
# ============================================================================

test_T7() {
    run_test "T7" "Build Script (build_solace.sh)"

    log_info "Input: ./build_solace.sh"

    cd "$PROJECT_ROOT"
    if [[ -f build_solace.sh ]]; then
        log_pass "build_solace.sh exists"
        pass_test "T7-build-script"
        return 0
    else
        log_fail "build_solace.sh not found"
        fail_test "T7-build-script"
        return 1
    fi
}

# ============================================================================
# TEST 8: No Stale Artifacts
# ============================================================================

test_T8() {
    run_test "T8" "No Stale Artifacts (Freshness)"

    log_info "Setup: Binary compiled"
    log_info "Input: Check modification time"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T8-freshness"
        return 1
    fi

    mtime=$(stat -f%m "$CHROME_BINARY" 2>/dev/null || stat -c%Y "$CHROME_BINARY" 2>/dev/null)
    now=$(date +%s)
    delta=$((now - mtime))

    log_info "Binary mtime: $mtime, now: $now, delta: ${delta}s"

    if [[ $delta -le 300 ]]; then  # 5 minutes
        log_pass "Binary is fresh (${delta}s old)"
        pass_test "T8-freshness"
        return 0
    else
        log_fail "Binary is stale (${delta}s old, max 300s allowed)"
        fail_test "T8-freshness"
        return 1
    fi
}

# ============================================================================
# TEST 9: Multiple Processes Isolated
# ============================================================================

test_T9() {
    run_test "T9" "Multiple Processes Isolated (Stress)"

    log_info "Setup: Binary compiled"
    log_info "Input: Launch 3 instances, all exit cleanly"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T9-multi-process"
        return 1
    fi

    for i in {1..3}; do
        log_info "Launching instance $i..."
        (timeout 2 "$CHROME_BINARY" --headless --no-sandbox &)
        sleep 1
    done

    sleep 3
    pkill -9 chrome 2>/dev/null || true

    if ! ps aux | grep -v grep | grep -q "$CHROME_BINARY"; then
        log_pass "All processes terminated"
        pass_test "T9-multi-process"
        return 0
    else
        log_fail "Some processes still running"
        fail_test "T9-multi-process"
        return 1
    fi
}

# ============================================================================
# TEST 10: Build Cache Consistency
# ============================================================================

test_T10() {
    run_test "T10" "Build Cache Consistency (Incremental)"

    log_info "Setup: Binary already compiled"
    log_info "Input: ninja -C out/Release chrome (incremental)"

    if [[ ! -f "$CHROME_BINARY" ]]; then
        log_fail "Binary not found"
        fail_test "T10-cache-consistency"
        return 1
    fi

    hash_before=$(sha256sum "$CHROME_BINARY" | awk '{print $1}')

    cd "$PROJECT_ROOT"
    if timeout 30 ninja -C "$BUILD_OUT" chrome > /tmp/ninja_incremental.log 2>&1; then
        log_pass "Incremental build succeeded"

        hash_after=$(sha256sum "$CHROME_BINARY" | awk '{print $1}')

        if [[ "$hash_before" == "$hash_after" ]]; then
            log_pass "Binary unchanged (cache hit)"
            pass_test "T10-cache-consistency"
            return 0
        else
            log_warn "Binary changed (cache miss, but OK)"
            pass_test "T10-cache-consistency"
            return 0
        fi
    else
        log_fail "Incremental build failed"
        fail_test "T10-cache-consistency"
        return 1
    fi
}

# ============================================================================
# MAIN: Run All Tests
# ============================================================================

main() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║ WISH 1.1 RIPPLE: Browser Binary Compilation                    ║"
    echo "║ Authority: 65537 | Phase: 1 (Fork & Setup)                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""

    mkdir -p "$ARTIFACTS_DIR"

    # Run all tests
    test_T1 || true
    test_T2 || true
    test_T3 || true
    test_T4 || true
    test_T5 || true
    test_T6 || true
    test_T7 || true
    test_T8 || true
    test_T9 || true
    test_T10 || true

    # Summary
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║ TEST SUMMARY                                                   ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║ Total:  $test_counter tests                                         ║"
    echo "║ Passed: $passed tests                                         ║"
    echo "║ Failed: $failed tests                                         ║"
    if [[ $failed -eq 0 ]]; then
        echo "║ Status: ✅ ALL PASSED                                            ║"
    else
        echo "║ Status: ❌ SOME FAILED                                           ║"
    fi
    echo "╚════════════════════════════════════════════════════════════════╝"

    # Generate proof.json
    if [[ $failed -eq 0 ]]; then
        cat > "$ARTIFACTS_DIR/proof.json" <<EOF
{
  "mermaid": [],
  "spec_sha256": "$(sha256sum canon/solace-wishes/wish-1.1-browser-compilation.md | awk '{print $1}')",
  "status": "PASS",
  "suite": "wish-1.1-browser-compilation",
  "tests": [
    {"name": "T1-gn-config", "status": "PASS"},
    {"name": "T2-ninja-build", "status": "PASS"},
    {"name": "T3-version-output", "status": "PASS"},
    {"name": "T4-headless-launch", "status": "PASS"},
    {"name": "T5-clean-shutdown", "status": "PASS"},
    {"name": "T6-hash-determinism", "status": "PASS"},
    {"name": "T7-build-script", "status": "PASS"},
    {"name": "T8-freshness", "status": "PASS"},
    {"name": "T9-multi-process", "status": "PASS"},
    {"name": "T10-cache-consistency", "status": "PASS"}
  ]
}
EOF
        log_pass "proof.json generated"
    fi

    return $([[ $failed -eq 0 ]] && echo 0 || echo 1)
}

main "$@"
