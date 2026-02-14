# Phase 2: Episode Recording - Test Specification

**Status**: READY FOR TESTING
**Auth**: 65537 | **Verification Ladder**: 641 → 274177 → 65537

---

## Verification Ladder

### OAuth Foundation (39, 63, 91) - 25 Tests

**Care (39) - 10 tests**: Basic sanity checks
1. `test_oauth_care_001`: Recording can be started
2. `test_oauth_care_002`: Recording can be stopped
3. `test_oauth_care_003`: Episode structure exists
4. `test_oauth_care_004`: Actions array initialized
5. `test_oauth_care_005`: Metadata captured
6. `test_oauth_care_006`: Storage directory created
7. `test_oauth_care_007`: Single action recorded
8. `test_oauth_care_008`: Timestamp format valid
9. `test_oauth_care_009`: Episode ID unique
10. `test_oauth_care_010`: JSON structure valid

**Bridge (63) - 8 tests**: Connector functionality
11. `test_oauth_bridge_001`: Browser-renderer IPC working
12. `test_oauth_bridge_002`: Action serializer invoked
13. `test_oauth_bridge_003`: Snapshot capture triggered
14. `test_oauth_bridge_004`: Event listeners registered
15. `test_oauth_bridge_005`: DOM changes detected
16. `test_oauth_bridge_006`: Buffer flushed correctly
17. `test_oauth_bridge_007`: Episode saved to file
18. `test_oauth_bridge_008`: Index updated

**Stability (91) - 7 tests**: Reliability checks
19. `test_oauth_stability_001`: No memory leaks (100 actions)
20. `test_oauth_stability_002`: Recording stable across pages
21. `test_oauth_stability_003`: No lost actions
22. `test_oauth_stability_004`: Concurrent operations safe
23. `test_oauth_stability_005`: File I/O robust
24. `test_oauth_stability_006`: Error recovery works
25. `test_oauth_stability_007`: Deterministic results

---

### RIVAL-EDGE (641) - 29 Tests

**Navigation Tests (5)**
- `test_navigate_001`: Simple URL change recorded
- `test_navigate_002`: Fragment navigation recorded
- `test_navigate_003`: Relative URL converted to absolute
- `test_navigate_004`: Back/forward navigation recorded
- `test_navigate_005`: Redirects (30x) reach final URL

**Click Tests (6)**
- `test_click_001`: Button with ID selector
- `test_click_002`: Link (a tag) click
- `test_click_003`: Hidden element (display: none)
- `test_click_004`: Nested element in div
- `test_click_005`: Double-click (single or dual action?)
- `test_click_006`: Click with modifier keys (Shift, Ctrl)

**Type Tests (6)**
- `test_type_001`: Single character
- `test_type_002`: Full word
- `test_type_003`: Uppercase with Shift
- `test_type_004`: Special characters (!@#$)
- `test_type_005`: Paste operation (Ctrl+V)
- `test_type_006`: Clear field (select all + delete)

**Select Tests (4)**
- `test_select_001`: Dropdown selection
- `test_select_002`: Multi-select option
- `test_select_003`: Radio button group
- `test_select_004`: Checkbox toggle

**Submit Tests (4)**
- `test_submit_001`: Form submit with Enter key
- `test_submit_002`: Form submit with button click
- `test_submit_003`: Validation error handling
- `test_submit_004`: AJAX submit (no navigation)

**Snapshot Tests (4)**
- `test_snapshot_001`: Deterministic canonicalization
- `test_snapshot_002`: Size bounds (< 10MB per action)
- `test_snapshot_003`: Dynamic content handling
- `test_snapshot_004`: Iframe content inclusion

---

### RIVAL-STRESS (274177) - 18 Tests

**Scaling Tests (6)**
- `test_stress_scale_001`: 100 consecutive actions
- `test_stress_scale_002`: 50 episodes in sequence
- `test_stress_scale_003`: 1000+ element DOM
- `test_stress_scale_004`: Rapid-fire clicks (100/sec)
- `test_stress_scale_005`: Long text input (10K chars)
- `test_stress_scale_006`: Mixed action types (20 of each)

**Memory Tests (4)**
- `test_stress_memory_001`: Memory after 100 episodes (< 500MB)
- `test_stress_memory_002`: Memory with large snapshots
- `test_stress_memory_003`: Long-running recording (1 hour sim)
- `test_stress_memory_004`: Concurrent recordings (memory linear)

**Reliability Tests (4)**
- `test_stress_reliability_001`: Survive page reload
- `test_stress_reliability_002`: Survive tab visibility change
- `test_stress_reliability_003`: Survive rapid navigation
- `test_stress_reliability_004`: Survive network interruption

**Concurrency Tests (4)**
- `test_stress_concurrent_001`: Multiple tabs (episode isolation)
- `test_stress_concurrent_002`: Recording while browser busy
- `test_stress_concurrent_003`: Simultaneous page load + recording
- `test_stress_concurrent_004`: Recording + heavy JS execution

---

### GOD-APPROVAL (65537) - 28 Tests

**Phase B Integration (8)**
- `test_god_phase_b_001`: Episode matches Phase B schema
- `test_god_phase_b_002`: Snapshot RTC roundtrip (encode/decode)
- `test_god_phase_b_003`: Action types match Phase B enum
- `test_god_phase_b_004`: Timestamp format ISO 8601
- `test_god_phase_b_005`: Episode serialization determinism
- `test_god_phase_b_006`: Unicode character handling
- `test_god_phase_b_007`: Empty episode structure valid
- `test_god_phase_b_008`: Episode export to file

**End-to-End Workflows (10)**
- `test_god_workflow_001`: Reddit post (navigate→type→submit)
- `test_god_workflow_002`: Search result (navigate→type→click→read)
- `test_god_workflow_003`: Form filling (5 fields + submit)
- `test_god_workflow_004`: Multi-page (3 pages, 3 navigations)
- `test_god_workflow_005`: Modal dialog (open→fill→ok)
- `test_god_workflow_006`: Dropdown + action (select→click)
- `test_god_workflow_007`: Table row selection + action
- `test_god_workflow_008`: Authentication (login→redirect)
- `test_god_workflow_009`: File upload (select→submit)
- `test_god_workflow_010`: Complex form with validation

**Phase A Compatibility (6)**
- `test_god_compat_a_001`: Snapshot format compatible
- `test_god_compat_a_002`: Episode readable by Phase A
- `test_god_compat_a_003`: Action types recognized
- `test_god_compat_a_004`: Selector format compatible
- `test_god_compat_a_005`: Timestamp precision compatible
- `test_god_compat_a_006`: Episode size within limits (< 50MB)

**Evidence & Proof (4)**
- `test_god_evidence_001`: Episode has canonical hash
- `test_god_evidence_002`: Content immutability (hash change on mod)
- `test_god_evidence_003`: Timestamp accuracy (within 1 sec)
- `test_god_evidence_004`: Provenance metadata (browser version)

---

## Test Infrastructure

### Test Framework
- **Language**: Python + pytest
- **Browser Automation**: Chrome DevTools Protocol (CDP)
- **Validation**: JSON schema, hash verification
- **Reporting**: JUnit XML, coverage reports

### Test Data
- 10 sample websites (reddit, github, wikipedia, etc.)
- 20 pre-recorded interaction sequences
- Golden file reference episodes

### Measurement
- Per-test pass/fail
- Execution time tracking
- Memory usage profiling
- Test coverage reporting

---

## Success Criteria

✅ Phase 2 Testing Complete When:

1. **All 75 tests passing**:
   - 25 OAuth tests ✓
   - 29 edge tests (641) ✓
   - 18 stress tests (274177) ✓
   - 28 god tests (65537) ✓

2. **Quality gates**:
   - Zero unresolved defects
   - RTC verified (snapshot encode/decode roundtrip)
   - Determinism verified (same input = same output)
   - Memory stable (< 10% growth per hour)

3. **Documentation**:
   - API fully documented
   - Examples provided
   - Integration guide completed

---

**Next Step**: Begin implementation and testing
