# WISH 12.0: Network Request Interception & Mocking

**Spec ID:** wish-12.0-network-interception
**Authority:** 65537
**Phase:** 12 (Network Integration)
**Depends On:** wish-11.0 (performance optimization complete)
**Scope:** Intercept, inspect, modify, and mock HTTP/HTTPS requests during automation
**Non-Goals:** HTTP/2, proxying external traffic, DNS manipulation
**Status:** 🎮 ACTIVE (Ready for Haiku swarm ripple)
**XP:** 1050 | **GLOW:** 105+

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Network requests are deterministically reproducible
  Verification:    Request intercepts prove no external side effects
  Canonicalization: Requests stored with deterministic headers/payloads
  Content-addressing: Request ID = SHA256(method + url + body_hash)
```

---

## 1. Observable Wish

> "I can intercept and inspect HTTP/HTTPS requests, modify request/response data for testing, mock responses, and verify deterministic behavior without external network calls."

---

## 2. Scope Exclusions

**NOT included in this wish:**
- ❌ HTTP/2 protocol support
- ❌ Proxying external traffic
- ❌ DNS hijacking
- ❌ TLS certificate pinning bypass
- ❌ WebSocket interception (Phase 13+)

**Minimum success criteria:**
- ✅ Intercept GET, POST, PUT, DELETE requests
- ✅ Read and modify request headers and body
- ✅ Mock responses (return custom data instead of real request)
- ✅ Record request history with full context
- ✅ Deterministic request/response matching for replay

---

## 3. Context Capsule (Test-Only)

```
Initial:   Optimized episode execution (wish-11.0)
Behavior:  Intercept network requests, mock/modify, record for replay
Final:     Network-independent automation possible, deterministic request handling verified
```

---

## 4. State Space: 5 States

```
state_diagram-v2
    [*] --> IDLE
    IDLE --> ARMED: setup_intercept()
    ARMED --> INTERCEPTING: request_detected
    INTERCEPTING --> PROCESSING: intercept_handler_called
    PROCESSING --> FORWARDING: decision_made
    FORWARDING --> RECORDED: response_handled
    RECORDED --> COMPLETE: history_saved
    PROCESSING --> MOCKED: mock_response_returned
    MOCKED --> RECORDED: mock_handled
    PROCESSING --> BLOCKED: request_blocked
    BLOCKED --> ERROR: blocking_failed
    ERROR --> [*]
    COMPLETE --> [*]
```

---

## 5. Invariants (5 Total)

**INV-1:** All HTTP/HTTPS requests detected before network transmission
**INV-2:** Request modifications don't corrupt headers or body
**INV-3:** Mock responses are indistinguishable from real responses to browser
**INV-4:** Request history complete with timestamp, headers, body, response
**INV-5:** Deterministic request matching enables perfect replay without network

---

## 6. Exact Tests (Setup/Input/Expect/Verify)

### T1: Request Interception
```
Setup:   Episode execution with network requests
Input:   Intercept HTTP GET request to example.com
Expect:  Request captured before network transmission
Verify:  Request record contains method, URL, headers, timestamp
```

### T2: Request Modification
```
Setup:   Interceptor armed, request intercepted
Input:   Modify request headers (add auth token, change user-agent)
Expect:  Modified headers applied without errors
Verify:  Modified request forwarded with new headers, original unchanged
```

### T3: Response Mocking
```
Setup:   Request interception active
Input:   Mock response for specific URL (return custom JSON)
Expect:  Browser receives mocked response instead of real request
Verify:  Browser treats mock as real response, episode proceeds normally
```

### T4: Request History
```
Setup:   Multiple requests made and intercepted
Input:   Compile request history log
Expect:  All requests recorded with full context
Verify:  History valid JSON, timestamps sequential, no missing requests
```

### T5: Deterministic Request Matching
```
Setup:   Request history recorded
Input:   Replay episode with request matching (use history instead of network)
Expect:  Episode replays using recorded requests, no network calls made
Verify:  Execution identical to original, all assertions pass, no timeout
```

---

## 7. Forecasted Failures (Pinned as Tests/Invariants)

**F1:** Request not intercepted → T1 fails, request goes to network
**F2:** Header modification fails → T2 fails, request unmodified
**F3:** Mock not returned → T3 fails, real request made
**F4:** History incomplete → T4 fails, missing request context
**F5:** Request matching fails → T5 fails, cannot replay deterministically

---

## 8. Visual Evidence (Proof Artifacts)

**request-interception.json structure:**
```json
{
  "interception_id": "intercept-20260214-001",
  "timestamp": "2026-02-14T17:40:00Z",
  "intercepted_requests": [
    {
      "request_id": "req-001",
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "user-agent": "Mozilla/5.0...",
        "authorization": "Bearer token123",
        "accept": "application/json"
      },
      "body": null,
      "intercepted_at_ms": 1234567890,
      "action": "forward",
      "status": "success"
    },
    {
      "request_id": "req-002",
      "method": "POST",
      "url": "https://api.example.com/data",
      "headers": {
        "content-type": "application/json"
      },
      "body": "{\"key\": \"value\"}",
      "intercepted_at_ms": 1234567950,
      "action": "mock",
      "mock_response": {
        "status": 200,
        "body": "{\"result\": \"success\"}",
        "headers": {"content-type": "application/json"}
      },
      "status": "mocked"
    }
  ],
  "total_intercepted": 2,
  "forwarded_requests": 1,
  "mocked_requests": 1
}
```

**request-modification.json structure:**
```json
{
  "modification_id": "mod-20260214-001",
  "timestamp": "2026-02-14T17:41:00Z",
  "modifications": [
    {
      "mod_id": "m-001",
      "target_url": "https://api.example.com/users",
      "header_changes": {
        "authorization": {
          "before": "Bearer old_token",
          "after": "Bearer new_token"
        },
        "x-custom-header": {
          "added": "custom_value"
        }
      },
      "body_changes": null,
      "applied": true
    }
  ],
  "total_modifications": 1,
  "successful_modifications": 1
}
```

---

## 9. RTC Checklist (Ready To Compile)

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns 0 (PASS) or 1 (FAIL)
- [x] **R3: Complete** — Network interception pipeline fully specified
- [x] **R4: Deterministic** — Interception behavior reproducible
- [x] **R5: Hermetic** — No external network calls in test mode
- [x] **R6: Idempotent** — Interception doesn't modify episode
- [x] **R7: Fast** — All tests complete in <15 seconds
- [x] **R8: Locked** — Setup/Expect/Verify phrases are word-for-word
- [x] **R9: Reproducible** — Same episode produces same requests
- [x] **R10: Verifiable** — Request records prove all interceptions

**RTC Status: 10/10 ✅ READY FOR RIPPLE**

---

## 10. Success Criteria

- [ ] All 5 tests pass (5/5)
- [ ] HTTP/HTTPS requests successfully intercepted
- [ ] Request headers modified without corruption
- [ ] Mock responses returned correctly
- [ ] Request history complete and deterministic
- [ ] Replay without network possible and verified

---

## 11. Next Phase

→ **wish-13.0** (Element Visibility Detection): Build on network isolation to detect visible elements

---

**Wish:** wish-12.0-network-interception
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 — Ready for Haiku Ripple
**Impact:** Unblocks wish-13.0, enables network-independent deterministic automation

*"Record the network, replay without it."*
