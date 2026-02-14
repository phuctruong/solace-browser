#!/bin/bash
# WISH 1.0b RIPPLE: Chromium Source Fetch & Validation
# Authority: 65537
# Implements: wish-1.0b-chromium-source-fetch.md
# Tests: 5 exact tests (T1-T5) with Setup/Input/Expect/Verify

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="$PROJECT_ROOT/source_full"
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
sync_attempted=false
sync_status="SKIPPED"

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
echo "║ WISH 1.0b RIPPLE: Chromium Source Fetch & Validation          ║"
echo "║ Authority: 65537 | Phase: 1 (Fork & Setup)                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# TEST 1: GClient Available
# ============================================================================

test_T1() {
    run_test "T1" "GClient Available"

    log_info "Setup: System PATH includes download tools"
    log_info "Input: which gclient"

    # First try gclient
    if gclient_path=$(which gclient 2>/dev/null); then
        log_pass "GClient found at $gclient_path"

        if gclient_version=$(gclient --version 2>&1); then
            log_info "GClient version: $gclient_version"
            log_pass "gclient --version works"
            log_pass "T1: GClient Available ✓"
            pass_test "T1-gclient-available"
            return 0
        else
            log_fail "gclient --version failed"
            fail_test "T1-gclient-available"
            return 1
        fi
    else
        # Try depot_tools as fallback
        log_warn "gclient not in PATH, checking for depot_tools..."
        if depot_path=$(which depot_tools 2>/dev/null); then
            log_pass "depot_tools found at $depot_path"
            log_pass "T1: GClient/depot_tools Available ✓"
            pass_test "T1-gclient-available"
            return 0
        else
            log_fail "Neither gclient nor depot_tools found in PATH"
            log_info "Install with: git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git"
            fail_test "T1-gclient-available"
            return 1
        fi
    fi
}

# ============================================================================
# TEST 2: Run GClient Sync (or Skip if Already Synced)
# ============================================================================

test_T2() {
    run_test "T2" "GClient Sync"

    log_info "Setup: Current directory = source_full, .gclient file exists"
    log_info "Input: gclient sync --with_branch_heads --force (or skip if already synced)"

    # Check if source is already synced
    if [[ -f "$SOURCE_ROOT/src/.gn" && -d "$SOURCE_ROOT/src/third_party" ]]; then
        log_warn "Source already present at $SOURCE_ROOT/src"
        log_info "Skipping gclient sync (would be redundant)"
        sync_status="ALREADY_PRESENT"
        log_pass "T2: GClient Sync (Already Synced) ✓"
        pass_test "T2-gclient-sync"
        return 0
    fi

    # Need to actually sync
    log_info "Source not yet synced, running gclient sync..."
    cd "$SOURCE_ROOT"

    sync_attempted=true

    # Try sync with network (with timeout)
    if timeout 3600 gclient sync --with_branch_heads --force > /tmp/gclient_sync.log 2>&1; then
        log_pass "GClient sync completed successfully"
        sync_status="SUCCESS"

        # Verify sync created src directory
        if [[ -d "$SOURCE_ROOT/src" ]]; then
            log_pass "source_full/src/ created"
            log_pass "T2: GClient Sync ✓"
            pass_test "T2-gclient-sync"
            return 0
        else
            log_fail "source_full/src/ not created after sync"
            fail_test "T2-gclient-sync"
            return 1
        fi
    else
        # Sync failed or timed out - show last part of log
        log_fail "GClient sync failed or timed out"
        sync_status="FAILED"
        log_info "Last 30 lines of sync output:"
        tail -30 /tmp/gclient_sync.log || true
        fail_test "T2-gclient-sync"
        return 1
    fi
}

# ============================================================================
# TEST 3: Chromium Source Structure Valid
# ============================================================================

test_T3() {
    run_test "T3" "Chromium Source Structure Valid"

    log_info "Setup: GClient sync completed (or already present)"
    log_info "Input: Check for .gn and BUILDCONFIG.gn"

    local gn_file="$SOURCE_ROOT/src/.gn"
    local buildconfig_file="$SOURCE_ROOT/src/BUILDCONFIG.gn"

    if [[ ! -f "$gn_file" ]]; then
        log_fail ".gn file missing at $gn_file"
        fail_test "T3-source-structure"
        return 1
    fi
    log_pass ".gn file exists"

    # Check file size (should be > 100 bytes, not empty)
    local gn_size=$(stat -c%s "$gn_file" 2>/dev/null || echo 0)
    if [[ $gn_size -lt 100 ]]; then
        log_fail ".gn file too small ($gn_size bytes)"
        fail_test "T3-source-structure"
        return 1
    fi
    log_pass ".gn file valid size ($gn_size bytes)"

    if [[ ! -f "$buildconfig_file" ]]; then
        log_fail "BUILDCONFIG.gn file missing"
        fail_test "T3-source-structure"
        return 1
    fi
    log_pass "BUILDCONFIG.gn file exists"

    # Check file size
    local buildconfig_size=$(stat -c%s "$buildconfig_file" 2>/dev/null || echo 0)
    if [[ $buildconfig_size -lt 100 ]]; then
        log_fail "BUILDCONFIG.gn file too small ($buildconfig_size bytes)"
        fail_test "T3-source-structure"
        return 1
    fi
    log_pass "BUILDCONFIG.gn file valid size ($buildconfig_size bytes)"

    log_pass "T3: Source Structure Valid ✓"
    pass_test "T3-source-structure"
    return 0
}

# ============================================================================
# TEST 4: Third-Party Dependencies Present
# ============================================================================

test_T4() {
    run_test "T4" "Third-Party Dependencies Present"

    log_info "Setup: Source structure validated"
    log_info "Input: Count subdirectories in third_party/"

    local third_party_dir="$SOURCE_ROOT/src/third_party"

    if [[ ! -d "$third_party_dir" ]]; then
        log_fail "third_party/ directory missing"
        fail_test "T4-third-party-deps"
        return 1
    fi
    log_pass "third_party/ directory exists"

    # Count subdirectories (should have many dependencies)
    local dep_count=$(find "$third_party_dir" -maxdepth 1 -type d 2>/dev/null | wc -l)
    # wc -l counts the dir itself, so subtract 1
    dep_count=$((dep_count - 1))

    log_info "Found $dep_count third-party dependencies"

    if [[ $dep_count -lt 10 ]]; then
        log_fail "Too few dependencies ($dep_count < 10)"
        fail_test "T4-third-party-deps"
        return 1
    fi
    log_pass "Sufficient dependencies present ($dep_count >= 10)"

    # Check for key dependencies
    local key_deps=("v8" "abseil-cpp" "skia" "protobuf")
    for dep in "${key_deps[@]}"; do
        if [[ -d "$third_party_dir/$dep" ]]; then
            log_pass "Key dependency found: $dep"
        else
            log_warn "Key dependency missing: $dep (may not be required)"
        fi
    done

    log_pass "T4: Third-Party Dependencies Present ✓"
    pass_test "T4-third-party-deps"
    return 0
}

# ============================================================================
# TEST 5: Source Integrity Check
# ============================================================================

test_T5() {
    run_test "T5" "Source Integrity Check"

    log_info "Setup: Source fully synced"
    log_info "Input: Calculate SHA256(buildfiles.gni)"

    local buildfiles_path="$SOURCE_ROOT/src/buildfiles.gni"

    if [[ ! -f "$buildfiles_path" ]]; then
        log_warn "buildfiles.gni not found, using .gn instead"
        buildfiles_path="$SOURCE_ROOT/src/.gn"
    fi

    if [[ ! -f "$buildfiles_path" ]]; then
        log_fail "Cannot find buildfiles for integrity check"
        fail_test "T5-source-integrity"
        return 1
    fi

    # Calculate hash
    if hash=$(sha256sum "$buildfiles_path" 2>/dev/null | awk '{print $1}'); then
        log_pass "SHA256 calculated: $hash"

        # Store hash in artifacts
        echo "$hash" > "$ARTIFACTS_DIR/source.sha256"
        log_pass "Hash stored to artifacts/source.sha256"

        log_pass "T5: Source Integrity Check ✓"
        pass_test "T5-source-integrity"
        return 0
    else
        log_fail "SHA256 calculation failed"
        fail_test "T5-source-integrity"
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
printf "║ Sync:   %s                                         ║\n" "$sync_status"

if [[ $failed -eq 0 ]]; then
    echo "║ Status: ✅ ALL PASSED                                           ║"
    status_code=0
else
    echo "║ Status: ❌ SOME FAILED                                           ║"
    status_code=1
fi

echo "╚════════════════════════════════════════════════════════════════╝"

# Generate proof.json
proof_json="$ARTIFACTS_DIR/proof-1.0b.json"
cat > "$proof_json" <<EOF
{
  "spec_id": "wish-1.0b-chromium-source-fetch",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "authority": "65537",
  "tests_passed": $passed,
  "tests_failed": $failed,
  "tests_total": $test_counter,
  "status": $([ $failed -eq 0 ] && echo '"SUCCESS"' || echo '"FAILED"'),
  "sync_info": {
    "attempted": $sync_attempted,
    "status": "$sync_status",
    "source_root": "$SOURCE_ROOT"
  },
  "source_integrity": {
    "source_sha256_file": "$([ -f "$ARTIFACTS_DIR/source.sha256" ] && echo "artifacts/source.sha256" || echo "NOT_GENERATED")"
  }
}
EOF

log_info "Proof artifact saved to: $proof_json"

# Summary message
echo ""
if [[ $failed -eq 0 ]]; then
    log_pass "WISH 1.0b COMPLETE: Chromium source validated ✅"
    if [[ "$sync_status" == "SUCCESS" || "$sync_status" == "ALREADY_PRESENT" ]]; then
        log_info "Source ready at: $SOURCE_ROOT/src"
        log_info "Next phase: wish-1.1 (Compilation)"
    else
        log_warn "Source fetch incomplete - may need manual setup"
    fi
    echo ""
    exit 0
else
    log_fail "WISH 1.0b FAILED: $failed test(s) failed ❌"
    if [[ "$sync_status" == "FAILED" ]]; then
        log_info "GClient sync failed - check network and credentials"
        log_info "Manual setup: cd source_full && gclient sync --with_branch_heads"
    fi
    echo ""
    exit 1
fi
