# Solace Browser CLI v2.0 - Test Suite

This directory contains comprehensive tests for the Solace Browser CLI v2.0 refactoring. Tests are organized into three layers: **Unit**, **Integration**, and **Harsh QA**.

## Test Architecture

### Layer 1: Unit Tests (`unit_tests.sh`)
**Purpose:** Verify each CLI function works in isolation

Tests individual CDP functions without requiring browser automation:
- ✅ `test_cdp_detection` - Verify browser availability on CDP port
- ✅ `test_browser_start` - Verify browser can start and listen
- ✅ `test_navigate_to` - Verify Page.navigate CDP command works
- ✅ `test_click_element` - Verify Runtime.evaluate click command works
- ✅ `test_type_text` - Verify Input.dispatchKeyEvent typing works
- ✅ `test_screenshot` - Verify Page.captureScreenshot works
- ✅ `test_snapshot` - Verify DOM.getOuterHTML works
- ✅ `test_episode_creation` - Verify episode JSON structure
- ✅ `test_recipe_compilation` - Verify episode → recipe compilation
- ✅ `test_proof_generation` - Verify recipe → proof execution

**Run Unit Tests:**
```bash
bash tests/unit_tests.sh
```

**Expected Output:**
```
✓ PASS: Browser detected on CDP port
✓ PASS: Browser start command executed
✓ PASS: Navigate command executed
✓ PASS: All 10 unit tests passed
```

**Timeline:** ~2-3 minutes

---

### Layer 2: Integration Tests (`integration_tests.sh`)
**Purpose:** Verify full workflows work end-to-end

Tests the complete cycle: record → compile → play → verify

**Tests:**
- ✅ `test_full_workflow_mock` - Mock mode: episode → recipe → proof
- ✅ `test_deterministic_replay` - Same recipe, 3 executions, identical proofs
- ✅ `test_compilation_idempotency` - Compiling twice produces identical recipe
- ✅ `test_multiple_episodes` - Multiple independent episodes coexist
- ✅ `test_recipe_immutability` - Locked recipes have immutability flag

**Run Integration Tests:**
```bash
bash tests/integration_tests.sh
```

**Expected Output:**
```
✓ PASS: Episode file created
✓ PASS: Recipe file created
✓ PASS: Recipe is locked (immutable)
✓ PASS: Proof artifact generated
✓ PASS: All 5 integration tests passed
```

**Timeline:** ~3-4 minutes

---

### Layer 3: Harsh QA Tests (`harsh_qa.sh`)
**Purpose:** Verify edge cases, determinism, and scaling

Extreme verification for production readiness:

**Tests:**
- ✅ `qa_no_popup_dialogs` - Browser shows clean state (no restore dialog)
- ✅ `qa_navigation_determinism` - Navigate to 5 domains, all succeed
- ✅ `qa_action_recording_completeness` - Actions recorded in episode
- ✅ `qa_deterministic_compilation` - 5 compilations, identical hashes
- ✅ `qa_concurrent_execution` - Execute 3 recipes in parallel
- ✅ `qa_proof_integrity` - All proofs have required fields
- ✅ `qa_episode_to_proof_chain` - Unbroken chain: episode → recipe → proof
- ✅ `qa_stress_large_batch` - Create/compile/execute 10 recipes

**Run Harsh QA Tests:**
```bash
bash tests/harsh_qa.sh
```

**Expected Output:**
```
✓ PASS: Browser shows clean state (no restore dialog)
✓ PASS: All 5 domain navigations succeeded
✓ PASS: All 10 recipes compiled successfully
✓ PASS: All 8 harsh QA tests passed
```

**Timeline:** ~5-6 minutes

---

## Test Workflow

### Quick Validation (Unit Only)
```bash
bash tests/unit_tests.sh
# Expected: All 10 tests pass in ~2-3 minutes
```

### Full Validation (Unit + Integration)
```bash
bash tests/unit_tests.sh && bash tests/integration_tests.sh
# Expected: All 15 tests pass in ~5-6 minutes
```

### Complete Validation (Unit + Integration + Harsh QA)
```bash
bash tests/unit_tests.sh && bash tests/integration_tests.sh && bash tests/harsh_qa.sh
# Expected: All 23 tests pass in ~10-15 minutes
```

### Continuous Validation Script
```bash
#!/bin/bash
echo "Starting full test suite..."
bash tests/unit_tests.sh || exit 1
bash tests/integration_tests.sh || exit 1
bash tests/harsh_qa.sh || exit 1
echo "All test layers passed!"
```

---

## Test Results Interpretation

### ✅ All Tests Pass
Indicates:
- CDP integration working correctly
- Episode → recipe → proof pipeline functional
- Determinism verified (same recipe, identical proofs)
- No popup dialogs or browser issues
- Ready for production use

### ⚠️ Some Unit Tests Fail
Indicates:
- Specific CDP function issue
- Browser connectivity problem
- WebSocket communication issue
- Fix: Run `bash tests/unit_tests.sh` individually to isolate

### ⚠️ Some Integration Tests Fail
Indicates:
- Episode/recipe/proof structure problem
- Compilation or execution issue
- File system problem
- Fix: Check logs in `logs/solace.log`

### ⚠️ Some Harsh QA Tests Fail
Indicates:
- Determinism not verified
- Browser UI issues (popups, dialogs)
- Scaling problem (concurrent execution)
- Fix: Review QA test and adjust thresholds

---

## Debugging Failed Tests

### Enable Verbose Logging
```bash
bash -x tests/unit_tests.sh 2>&1 | tee test_debug.log
```

### Check CLI Logs
```bash
tail -f logs/solace.log
tail -f logs/cdp.log
```

### Inspect Generated Files
```bash
# Check episode structure
cat episodes/*.json | jq '.'

# Check recipe structure
cat recipes/*.recipe.json | jq '.'

# Check proof structure
cat artifacts/proof-*.json | jq '.'
```

### Manual Function Testing
```bash
# Test navigate
bash solace-browser-cli-v2.sh navigate test "https://example.com"

# Test click
bash solace-browser-cli-v2.sh click test "button.submit"

# Test type
bash solace-browser-cli-v2.sh fill test "input#search" "hello"

# Test screenshot
bash solace-browser-cli-v2.sh screenshot test.png

# Test snapshot
bash solace-browser-cli-v2.sh snapshot
```

---

## Test Environment Requirements

### Required
- Bash 4.0+
- Python 3.6+
- curl
- jq (optional, for JSON inspection)
- Chrome/Chromium/Edge browser
- websocket-client Python library: `pip install websocket-client`

### Optional
- GNU parallel (for batch testing)
- htop (for monitoring concurrent execution)

### Install Dependencies
```bash
# Install Python websocket library
pip install websocket-client

# Install Chrome/Chromium
sudo apt-get install chromium-browser  # Debian/Ubuntu
# or
brew install chromium  # macOS
```

---

## Test Metrics

### Success Criteria

| Test Suite | Tests | Expected | Timeline |
|-----------|-------|----------|----------|
| Unit      | 10    | 10 pass  | 2-3 min  |
| Integration | 5    | 5 pass   | 3-4 min  |
| Harsh QA  | 8     | 8 pass   | 5-6 min  |
| **Total** | **23** | **23 pass** | **10-15 min** |

### Quality Gates
- ✅ All unit tests must pass
- ✅ All integration tests must pass
- ✅ All harsh QA tests must pass
- ✅ No browser popups or dialogs
- ✅ Determinism verified (3x executions identical)
- ✅ No errors in logs

---

## File Organization

```
tests/
├── unit_tests.sh           # Layer 1: Unit tests (10 tests)
├── integration_tests.sh     # Layer 2: Integration tests (5 tests)
├── harsh_qa.sh             # Layer 3: Harsh QA tests (8 tests)
└── README_TESTS.md         # This file

Related Files:
├── solace-browser-cli-v2.sh # Main CLI (modified with CDP fixes)
├── episodes/               # Episode JSON files
├── recipes/                # Locked recipe JSON files
├── artifacts/              # Proof and screenshot files
└── logs/                   # Test logs (solace.log, cdp.log)
```

---

## Contributing New Tests

### Test Template
```bash
test_feature_name() {
    log_test_header "Feature Name"
    test_start "Verify feature does X"

    # Setup
    bash "$CLI_SCRIPT" command arg > /dev/null 2>&1

    # Verify
    if [[ -f "$expected_file" ]]; then
        test_pass "File created as expected"
    else
        test_fail "File not created"
    fi
}
```

### Adding to Test Suite
1. Define function in appropriate layer (unit/integration/qa)
2. Call function in `run_all_tests()` section
3. Update counters at end of test

---

## Performance Benchmarks

### Unit Test Execution
- `test_cdp_detection`: 1-2 seconds
- `test_browser_start`: 5-10 seconds (includes browser startup)
- `test_navigate_to`: 2-3 seconds
- `test_click_element`: 1-2 seconds
- `test_type_text`: 1-2 seconds
- `test_screenshot`: 1-2 seconds
- `test_snapshot`: 1-2 seconds
- **Total Unit Tests:** 2-3 minutes

### Integration Test Execution
- `test_full_workflow_mock`: 1-2 seconds
- `test_deterministic_replay`: 3-5 seconds (3x executions)
- `test_compilation_idempotency`: 1-2 seconds
- `test_multiple_episodes`: 1-2 seconds
- `test_recipe_immutability`: 1 second
- **Total Integration Tests:** 3-4 minutes

### Harsh QA Test Execution
- `qa_no_popup_dialogs`: 5-10 seconds
- `qa_navigation_determinism`: 5 seconds
- `qa_action_recording_completeness`: 2 seconds
- `qa_deterministic_compilation`: 3-5 seconds
- `qa_concurrent_execution`: 5 seconds
- `qa_proof_integrity`: 2 seconds
- `qa_episode_to_proof_chain`: 2-3 seconds
- `qa_stress_large_batch`: 10-15 seconds
- **Total Harsh QA Tests:** 5-6 minutes

---

## Troubleshooting

### Browser Fails to Start
```bash
# Kill any stuck processes
pkill -9 chrome chromium

# Clear profile cache
rm -rf logs/browser-profile

# Check if port 9222 is in use
lsof -i :9222

# Try with explicit browser path
BROWSER_PATH=/usr/bin/chromium bash solace-browser-cli-v2.sh start
```

### WebSocket Connection Fails
```bash
# Verify CDP endpoint responds
curl http://localhost:9222/json/list

# Check if websocket-client is installed
python3 -c "import websocket; print(websocket.__version__)"

# Install if missing
pip install websocket-client
```

### Tests Timeout
```bash
# Increase timeout in test functions
# Default: 10 seconds for CDP operations
# Increase to 30 seconds for slower systems

# Edit test files and change:
# timeout = 10  →  timeout = 30
```

---

## Next Steps

After all tests pass:
1. ✅ Commit changes: `git commit -m "feat: Add comprehensive test suite"`
2. ✅ Document in README: Update project README with test instructions
3. ✅ Setup CI/CD: Add tests to GitHub Actions or Jenkins
4. ✅ Monitor: Watch test metrics over time

---

## Contact & Support

For issues or questions about tests:
- Check logs: `cat logs/solace.log`
- Review CLI output: `-v` flag for verbose mode
- File issue: Include test output and logs/solace.log
