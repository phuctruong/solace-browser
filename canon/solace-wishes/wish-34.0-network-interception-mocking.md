# WISH 34.0: Network Interception & Mocking

**Spec ID:** wish-34.0-network-interception-mocking
**Authority:** 65537
**Phase:** 34 (Network Layer Control)
**Depends On:** wish-33.0 (recipe composition verified)
**Status:** 🎮 ACTIVE (RTC 10/10)
**XP:** 2500 | **GLOW:** 220+ | **DIFFICULTY:** ADVANCED

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Network requests can be intercepted and logged
  Verification:    All HTTP calls captured, modified, and replayed deterministically
  Proof:           Request/response audit trail in execution trace
  Authority:       Network mocking is deterministic (same seed → same responses)
```

---

## 1. Observable Wish

> "I can record a recipe that intercepts all HTTP requests to LinkedIn, logs them with full request/response bodies, optionally modifies responses for testing edge cases, and replays the recipe with mocked responses deterministically, all without changing the browser automation logic."

---

## 2. Scope & Exclusions

**INCLUDED:**
- ✅ HTTP request interception (via Chrome DevTools Protocol)
- ✅ Request logging (method, URL, headers, body)
- ✅ Response capture (status, headers, body)
- ✅ Response mocking (inject custom responses)
- ✅ Request modification (change headers, delay)
- ✅ Network replay (reuse recorded responses)
- ✅ Deterministic replay (same mocks every time)

**EXCLUDED:**
- ❌ WebSocket interception
- ❌ SSL/TLS certificate pinning bypass
- ❌ DNS spoofing
- ❌ Real network fallback (if mock missing, request fails)

---

## 3. State Space: 9 States

```
[*] --> IDLE
IDLE --> ENABLE_INTERCEPTION: start_network_interception()
ENABLE_INTERCEPTION --> INTERCEPTOR_READY: interception_active()
INTERCEPTOR_READY --> RECORD_MODE: begin_episode_with_recording()
RECORD_MODE --> CAPTURE_REQUEST: intercept_http_request()
CAPTURE_REQUEST --> LOG_REQUEST: store_request_metadata()
LOG_REQUEST --> SEND_REAL: forward_request_to_real_server()
SEND_REAL --> CAPTURE_RESPONSE: intercept_http_response()
CAPTURE_RESPONSE --> LOG_RESPONSE: store_response_metadata()
LOG_RESPONSE --> RECIPE_COMPLETE: all_requests_logged()
RECIPE_COMPLETE --> SAVE_NETWORK_LOG: save_request_response_pairs()
SAVE_NETWORK_LOG --> COMPILE: create_network_mocks()
COMPILE --> MOCK_MODE: enable_request_mocking()
MOCK_MODE --> LOAD_MOCKS: load_recorded_responses()
LOAD_MOCKS --> REPLAY: replay_recipe_with_mocks()
REPLAY --> INTERCEPT_REQUEST_REPLAY: request_intercepted()
INTERCEPT_REQUEST_REPLAY --> MATCH_MOCK: find_matching_mock()
MATCH_MOCK --> RETURN_MOCK: inject_mocked_response()
RETURN_MOCK --> REQUEST_COMPLETE: continue_recipe_with_mock()
REQUEST_COMPLETE --> VERIFY_DETERMINISM: same_recipe_same_mocks()
VERIFY_DETERMINISM --> COMPLETE: [*]
CAPTURE_REQUEST --> ERROR: unsupported_protocol
ERROR --> [*]
```

---

## 4. Invariants (7 Total)

**INV-1:** All HTTP requests must be intercepted and logged
- Enforced by: Network.enable() in CDP, all requests captured before sending
- Proof: execution_trace.network_requests.count > 0

**INV-2:** Request/response pairs must be stored in canonical format
- Enforced by: { method, url, headers, body, status, response_headers, response_body, timing }
- Fail mode: Test FAILS if any field missing

**INV-3:** Mocking must be deterministic (seed-based)
- Enforced by: Same seed → same mock responses returned
- Proof: Execute 5 times with same seed, all responses identical

**INV-4:** Mocks must match requests by URL and method
- Enforced by: When intercepting request, find mock with matching (method, url)
- Fail mode: Test FAILS if wrong mock returned

**INV-5:** Real network must not be contacted in mock mode
- Enforced by: Request intercepted, mock injected, no upstream server contact
- Proof: No outbound connections in mock mode (can verify with tcpdump)

**INV-6:** Modified responses must preserve determinism
- Enforced by: Same modification logic → same result every time
- Proof: Modification functions deterministic (no random values)

**INV-7:** Network audit trail must be complete and unmodified
- Enforced by: All requests/responses locked in network log file
- Fail mode: Test FAILS if network log tamperable

---

## 5. Exact Tests (6 Total)

### T1: Network Interception Setup & Logging

```
Setup:   Solace Browser running, network interception disabled
Input:   Enable network interception, begin recording episode
Expect:  All HTTP requests are captured
Verify:
  - Execute: ./solace-browser-cli.sh record-with-network-intercept https://linkedin.com
  - Network interception enabled: ✅
  - CDP Network domain listening: ✅
  - User navigates to linkedin.com: ✅
  - Capture all requests:
    - GET https://www.linkedin.com/ (page load)
    - GET https://www.linkedin.com/static/... (assets)
    - POST https://api.linkedin.com/login (authentication)
    - GET https://www.linkedin.com/me (profile fetch)
    - Other XHR, fetch requests: ✅

  Network Log Contents:
    - Request 0: { method: "GET", url: "https://www.linkedin.com/", headers: {...}, status: 200, response_body_size: 45230 }
    - Request 1: { method: "GET", url: "https://static.linkedin.com/...", headers: {...}, status: 200, response_body_size: 127483 }
    - Request 2: { method: "POST", url: "https://api.linkedin.com/login", body: {...}, status: 200, response: {...} }
    - ... (all requests logged)

  Verification:
    - Network log file exists: ~/.solace-browser/network-logs/linkedin.network.json
    - Request count > 10: ✅
    - All requests have: method, url, headers, body (if POST/PUT), status, response_body
    - No null values in required fields: ✅
    - Timestamps chronological: ✅

Harsh QA:
  - If any request missed: FAIL
  - If network log empty: FAIL
  - If required fields missing: FAIL
```

### T2: Save & Compile Network Mocks

```
Setup:   Network recording complete, network log saved
Input:   Compile network log into reusable mock file
Expect:  Mock file created with all request/response pairs
Verify:
  - Execute: ./solace-browser-cli.sh compile-network-mocks linkedin.network.json
  - Output file: linkedin-network-mocks.json
  - File structure:
    ```json
    {
      "mocks": [
        {
          "mock_id": 0,
          "request": {
            "method": "GET",
            "url": "https://www.linkedin.com/",
            "headers": {...}
          },
          "response": {
            "status": 200,
            "headers": {...},
            "body": "...html content..."
          },
          "timing_ms": 250
        },
        { "mock_id": 1, ... },
        ...
      ],
      "mock_count": 47,
      "signature": "sha256_hash_of_all_mocks"
    }
    ```
  - All 47 requests → 47 mocks: ✅
  - Each mock valid JSON: ✅
  - All response bodies present: ✅
  - Mock signature computed: ✅

Harsh QA:
  - If any request missing mock: FAIL
  - If mock body empty/null: FAIL
  - If mock status code missing: FAIL
```

### T3: Mock-Based Replay (Same Responses)

```
Setup:   Mock file compiled, recipe ready to replay
Input:   Enable mock mode and replay recipe
Expect:  All requests intercepted and mocked responses returned
Verify:
  - Execute: ./solace-browser-cli.sh play linkedin-profile-update --use-mocks linkedin-network-mocks.json
  - Mode: MOCK (not REAL)
  - Recipe begins execution: ✅
  - Request 1 (GET https://www.linkedin.com/):
    - Intercepted: ✅
    - Mock found: ✅
    - Response injected: ✅ (status 200, original body)
    - No upstream server contacted: ✅ (verify no network egress)
    - Browser continues seamlessly: ✅
  - Request 2 (POST /login):
    - Intercepted: ✅
    - Mock found: ✅
    - Mocked response returned: ✅
    - Authentication succeeds (mock response was successful): ✅
  - ... (all requests mocked)

  Timing:
    - Recipe with real network: 30 seconds
    - Recipe with mocks: 2 seconds (no network delay)
    - Difference: 28 seconds (network latency eliminated)

  Final State:
    - Recipe completes successfully: ✅
    - Profile updates visible (same as real run): ✅
    - All pages loaded: ✅
    - All forms filled: ✅

Harsh QA:
  - If any request not mocked: FAIL (real request attempted)
  - If wrong mock returned: FAIL
  - If recipe fails in mock mode: FAIL
  - If recipe result differs from real run: FAIL
```

### T4: Request Modification (Testing Edge Cases)

```
Setup:   Mocks loaded, ready to test error scenarios
Input:   Modify mock responses to simulate edge cases
Expect:  Recipe handles mocked error responses gracefully
Verify:
  SCENARIO 1: Rate Limit (429 Response)
    - Original mock for POST /login: status 200, success
    - Modified mock: status 429, body: { error: "Too many requests" }
    - Execute recipe with modified mock
    - Result: Recipe detects 429 error, logs it, possibly retries
    - Expected behavior: Handle gracefully or fail with clear error

  SCENARIO 2: Server Error (500 Response)
    - Original mock for GET /api/profile: status 200, profile_data
    - Modified mock: status 500, body: { error: "Internal Server Error" }
    - Execute recipe
    - Result: Recipe detects 500, handles or retries

  SCENARIO 3: Partial Response (Incomplete Data)
    - Original mock for GET /api/profile: { name: "John", headline: "Engineer" }
    - Modified mock: { name: "John" } (missing headline)
    - Execute recipe
    - Result: Recipe handles missing field gracefully or fails cleanly

  Modification Workflow:
    - Load mock file
    - Find mock by URL: POST /login
    - Modify: status 429, headers: { "Retry-After": "60" }
    - Save modified mock: linkedin-network-mocks-429.json
    - Execute recipe with modified mocks
    - Capture result in execution trace

Harsh QA:
  - If modification not applied: FAIL
  - If wrong mock modified: FAIL
  - If recipe crashes on error response: FAIL (should handle)
  - If modification changes determinism: FAIL
```

### T5: Deterministic Mock Replay (5 Runs)

```
Setup:   Mock file compiled, modification rules defined
Input:   Execute recipe 5 times with same mocks
Expect:  All 5 executions produce identical results
Verify:
  EXECUTION 1:
    - Load mocks from file: linkedin-network-mocks.json
    - Execute recipe
    - Capture all responses: 47 requests → 47 mocked responses
    - Result: Profile updated with headline "Software 5.0 Architect..."
    - Proof hash: abc123...

  EXECUTIONS 2-5:
    - Load same mocks (same file, same seed)
    - Execute recipe
    - Capture all responses: identical to execution 1
    - Result: identical profile update
    - Proof hash: abc123... (MATCH)

  DETERMINISM VERIFICATION:
    - All 5 executions identical: ✅
    - SHA256(proof_1) == SHA256(proof_2) == ... == SHA256(proof_5): ✅
    - Response body byte-identical: ✅
    - Timing identical (execution trace matches): ✅
    - Network requests in same order: ✅
    - Mock responses unchanged: ✅
    - Determinism rate: 5/5 (100%): ✅

  Network Audit Trail:
    - Requests in execution trace: all 47 requests listed
    - Mock responses in trace: all 47 responses listed
    - No real network calls: VERIFIED (no egress)
    - Timing consistent: ±50ms across runs

Harsh QA:
  - If any execution differs: FAIL (not deterministic)
  - If mock responses changed between runs: FAIL
  - If proof hashes don't match: FAIL
  - If real network contacted: FAIL
```

### T6: Network Audit Trail & Verification

```
Setup:   Recipe executed with network mocking
Input:   Examine complete network audit trail
Expect:  Full request/response audit trail in proof artifact
Verify:
  Proof Artifact Network Section:
    ```json
    {
      "network_mode": "MOCKED",
      "network_requests_total": 47,
      "network_requests_captured": 47,
      "network_mocks_used": 47,
      "audit_trail": [
        {
          "sequence": 1,
          "timestamp": "2026-02-15T02:00:00Z",
          "request": {
            "method": "GET",
            "url": "https://www.linkedin.com/",
            "headers": {...},
            "body": null
          },
          "response": {
            "status": 200,
            "headers": {...},
            "body_size": 45230,
            "body_hash": "sha256_xyz"
          },
          "latency_ms": 0,
          "mocked": true,
          "mock_source": "linkedin-network-mocks.json"
        },
        {
          "sequence": 2,
          "timestamp": "2026-02-15T02:00:00.250Z",
          "request": {
            "method": "POST",
            "url": "https://api.linkedin.com/login",
            "headers": {...},
            "body": {...credentials...}
          },
          "response": {
            "status": 200,
            "headers": {...},
            "body": {...session...}
          },
          "latency_ms": 0,
          "mocked": true,
          "mock_source": "linkedin-network-mocks.json"
        },
        ...
      ],
      "network_summary": {
        "real_requests": 0,
        "mocked_requests": 47,
        "total_real_latency_ms": 0,
        "total_mock_latency_ms": 0,
        "network_free_run": true
      }
    }
    ```

  Audit Trail Verification:
    - All 47 requests in audit trail: ✅
    - All marked as "mocked": true: ✅
    - No real network latency: ✅
    - Sequence numbers continuous (1-47): ✅
    - Timestamps chronological: ✅
    - All responses complete (status, headers, body): ✅

Harsh QA:
  - If any request missing from audit: FAIL
  - If real request in audit: FAIL (should be mocked)
  - If audit trail incomplete: FAIL
  - If mock source not documented: FAIL
```

---

## 6. Success Criteria

- [x] All 6 tests pass (6/6)
- [x] Network interception working (all requests captured)
- [x] Mocks compiled from recorded responses
- [x] Mock-based replay successful
- [x] Request modification for edge case testing
- [x] Deterministic replay (5-run verification)
- [x] Complete audit trail in proof artifacts
- [x] No real network calls in mock mode

---

## 7. Proof Artifact Structure

```json
{
  "spec_id": "wish-34.0-network-interception-mocking",
  "timestamp": "2026-02-15T02:15:00Z",
  "execution_id": "network-interception-001",
  "recipe_id": "linkedin-profile-update.recipe",
  "tests_passed": 6,
  "tests_failed": 0,
  "network_configuration": {
    "mode": "MOCKED",
    "interception_enabled": true,
    "mocks_loaded": true,
    "mock_source": "linkedin-network-mocks.json",
    "mock_count": 47
  },
  "network_requests_captured": {
    "total": 47,
    "by_method": {
      "GET": 32,
      "POST": 10,
      "PUT": 3,
      "DELETE": 2
    },
    "by_domain": {
      "www.linkedin.com": 20,
      "api.linkedin.com": 15,
      "static.linkedin.com": 12
    }
  },
  "audit_trail": [
    {
      "sequence": 1,
      "timestamp": "2026-02-15T02:00:00Z",
      "request": {
        "method": "GET",
        "url": "https://www.linkedin.com/",
        "headers": {
          "User-Agent": "Chrome/120.0",
          "Accept": "text/html"
        }
      },
      "response": {
        "status": 200,
        "headers": {
          "Content-Type": "text/html",
          "Content-Length": "45230"
        },
        "body_hash": "sha256_abc123"
      },
      "mocked": true
    },
    {
      "sequence": 2,
      "timestamp": "2026-02-15T02:00:00.250Z",
      "request": {
        "method": "POST",
        "url": "https://api.linkedin.com/login",
        "headers": {...},
        "body": {...}
      },
      "response": {
        "status": 200,
        "body": {...}
      },
      "mocked": true
    }
  ],
  "request_modifications": {
    "applied": [
      {
        "request_match": "POST /login",
        "modification": "inject_429_rate_limit",
        "original_status": 200,
        "modified_status": 429,
        "applied": true
      }
    ]
  },
  "determinism": {
    "executions_count": 5,
    "executions_identical": 5,
    "determinism_rate": 1.0,
    "proof_hashes_match": true
  },
  "network_summary": {
    "real_requests": 0,
    "mocked_requests": 47,
    "network_free_run": true,
    "total_real_latency_ms": 0,
    "total_mock_latency_ms": 0
  },
  "verification_ladder": {
    "oauth_39_63_91": "PASS",
    "edge_641": "PASS (network layer)",
    "stress_274177": "PASS (determinism)",
    "god_65537": "APPROVED"
  }
}
```

---

## 8. RTC Checklist

- [x] **R1: Readable** — All 6 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns PASS/FAIL with clear criteria
- [x] **R3: Complete** — Network interception fully specified
- [x] **R4: Deterministic** — Mocked responses identical across runs
- [x] **R5: Hermetic** — Only depends on browser + mock files (no real network)
- [x] **R6: Idempotent** — Multiple mock executions don't interfere
- [x] **R7: Fast** — All tests complete in 30 minutes (mock mode: no network latency)
- [x] **R8: Locked** — Mock definitions locked, cannot change during replay
- [x] **R9: Reproducible** — Same mocks → identical execution
- [x] **R10: Verifiable** — Audit trail proves all requests mocked

**RTC Status: 10/10 ✅ PRODUCTION READY**

---

## 9. Implementation Commands

```bash
# Start browser with network interception
./solace-browser-cli.sh start --enable-network-intercept

# Record episode with network logging
./solace-browser-cli.sh record-with-network-intercept https://linkedin.com linkedin-with-network

# Compile network mocks from recorded session
./solace-browser-cli.sh compile-network-mocks \
  ~/.solace-browser/network-logs/linkedin.network.json \
  --output linkedin-network-mocks.json

# Replay recipe with mocks (no real network)
./solace-browser-cli.sh play linkedin-profile-update \
  --use-mocks linkedin-network-mocks.json \
  --network-mode MOCK

# Modify mock for testing (inject error)
./solace-browser-cli.sh modify-mock linkedin-network-mocks.json \
  --request "POST /login" \
  --response-status 429 \
  --output linkedin-network-mocks-429.json

# Execute recipe with modified mock
./solace-browser-cli.sh play linkedin-profile-update \
  --use-mocks linkedin-network-mocks-429.json

# Audit network requests
./solace-browser-cli.sh audit-network artifacts/proof-34.0-*.json --verbose
```

---

## 10. Next Phase

→ **wish-35.0** (Accessibility Testing & Screen Reader Support): Test recipes with ARIA labels and semantic HTML

---

**Wish:** wish-34.0-network-interception-mocking
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 ✅ PRODUCTION READY
**Impact:** Enables network-independent testing, edge case simulation, and offline recipe execution

*"Network intercepted. Requests logged. Responses mocked. Deterministic replay. No real network calls. That's network abstraction."*

---
