# Browser Startup Sequence (Q1 — 3-Step Boot)

Canonical architecture for `solace-browser start`

## Mermaid Diagram

```mermaid
sequenceDiagram
    actor User
    participant solace-browser
    participant ~/.solace/pid.lock
    participant solaceagi.com as solaceagi.com<br/>(Registration)
    participant tunnel.solaceagi.com as tunnel.solaceagi.com<br/>(Tunnel Relay)

    User->>solace-browser: solace-browser start

    rect rgb(200, 220, 255)
    Note over solace-browser: STEP 1: Boot Check
    solace-browser->>~/.solace/pid.lock: Check if already running?

    alt Browser Already Running
        ~/.solace/pid.lock-->>solace-browser: pid exists
        solace-browser->>solaceagi.com: Re-use existing session_token
        solaceagi.com-->>solace-browser: Tunnel confirmed
    else First Boot
        ~/.solace/pid.lock-->>solace-browser: pid.lock not found
        solace-browser->>solace-browser: Write own pid to ~/.solace/pid.lock
    end
    end

    rect rgb(220, 250, 220)
    Note over solace-browser: STEP 2: Register with solaceagi.com
    solace-browser->>solaceagi.com: POST /api/v1/browser/register
    Note over solace-browser: {device_id, tunnel_url, version, capabilities}
    solaceagi.com->>solaceagi.com: Validate user login (OAuth3)
    solaceagi.com->>solaceagi.com: Issue session_token (AES-256-GCM)
    solaceagi.com-->>solace-browser: {session_token, cloud_twin_url, event_stream_url}
    solace-browser->>~/.solace/config/oauth3_tokens: Store encrypted session_token
    end

    rect rgb(250, 220, 220)
    Note over solace-browser: STEP 3: Start Tunnel
    solace-browser->>tunnel.solaceagi.com: Open WebSocket
    solace-browser->>tunnel.solaceagi.com: Establish mTLS + OAuth3 token validation
    tunnel.solaceagi.com-->>solace-browser: Connection confirmed
    solace-browser->>solace-browser: Write tunnel_url to ~/.solace/config/tunnel.json
    end

    solace-browser-->>User: ✅ Browser Online (visible in solaceagi.com dashboard)
```

## Detailed Spec

### Step 1: Boot Check
- **File:** `~/.solace/pid.lock`
- **Logic:**
  - If `pid.lock` exists → browser already running → skip to tunnel reconnection
  - If `pid.lock` missing → first boot → write own PID
- **Output:** Browser identifier (PID or device_id)

### Step 2: Register with solaceagi.com
- **Endpoint:** `POST /api/v1/browser/register`
- **Request Payload:**
  ```json
  {
    "device_id": "device_abc123",
    "tunnel_url": "https://tunnel.solaceagi.com/browser/device_abc123",
    "version": "1.0.0",
    "capabilities": ["navigate", "click", "fill", "screenshot"]
  }
  ```
- **Response Payload:**
  ```json
  {
    "session_token": "oauth3_token_xyz789",
    "cloud_twin_url": "https://cloud-twin-123.run.app",
    "event_stream_url": "wss://events.solaceagi.com/device_abc123"
  }
  ```
- **Storage:** Encrypted in `~/.solace/config/oauth3_tokens` (AES-256-GCM, key from system keyring)
- **Timing:** ~15 seconds (includes OAuth3 validation)

### Step 3: Start Tunnel
- **Protocol:** WebSocket + mTLS (mutual TLS with OAuth3 token as bearer)
- **Endpoint:** `wss://tunnel.solaceagi.com/browser`
- **Headers:** `Authorization: Bearer <session_token>`
- **Security:** mTLS certificate pinning + token revocation checks every 60 seconds
- **Result:** Browser now accessible from `solaceagi.com` web UI
- **User sees:** "Browser Online" badge on dashboard within 30 seconds

## Constraints (Software 5.0)
- **NO fallbacks:** If registration fails, stop (don't retry silently)
- **NO silent token expiry:** If token expires, raise error (user must re-login)
- **Determinism:** Same device_id + version = same startup behavior
- **Logging:** All 3 steps logged to `~/.solace/outbox/browser_startup.jsonl` with timestamps

## Acceptance Criteria
- ✅ Boot check succeeds (pid.lock integrity)
- ✅ Registration succeeds (OAuth3 token issued)
- ✅ Tunnel connects (mTLS + WebSocket established)
- ✅ User sees "Browser Online" in dashboard
- ✅ 3-step sequence logged to JSONL audit trail
- ✅ Timeout after 60 seconds → fail with error

---

**Source:** ARCHITECTURAL_DECISIONS_20_QUESTIONS.md § Q1
**Rung:** 641 (deterministic startup sequence)
**Status:** CANONICAL — locked for Phase 4 implementation
