<!-- Diagram: hub-api-key-lifecycle -->
# hub-api-key-lifecycle: API Key Handshake + Keep-Alive + Reconnect
# DNA: `lifecycle = handshake(firebase→api_key→hub) → keep_alive(heartbeat_300s) → reconnect(on_wake) → expire(revoke)`
# Auth: 65537 | Version: 1.0.0

## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TD
    subgraph HANDSHAKE[1. Initial Handshake — one time]
        USER[User clicks Sign In<br>on solaceagi.com]:::free --> FIREBASE[Firebase Popup<br>Google / GitHub / Email]:::sealed
        FIREBASE -->|id_token| AGI_AUTH[POST /api/v1/auth/firebase-login<br>→ returns api_key + email + tier]:::sealed
        AGI_AUTH -->|api_key| BROWSER_JS[Browser JS stores<br>email in localStorage<br>token in SolaceAuth memory]:::sealed
        AGI_AUTH -->|api_key + email| HUB_CONNECT[POST localhost:8888<br>/api/v1/cloud/connect<br>api_key + email + device_id + paid_user]:::sealed
        HUB_CONNECT --> CONFIG[Write ~/.solace/cloud_config.json<br>encrypted api_key + email + device_id]:::sealed
    end

    subgraph KEEP_ALIVE[2. Keep-Alive — continuous]
        CONFIG --> HEARTBEAT[Heartbeat Loop<br>every 300s while Hub running]:::sealed
        HEARTBEAT --> PING[POST solaceagi.com<br>/api/v1/heartbeat<br>device_id + email + uptime]:::sealed
        PING -->|200 OK| ALIVE[Device Online ✓<br>dashboard shows green]:::sealed
        PING -->|network error| RETRY[Retry next 300s<br>mark offline after 10min]:::sealed
    end

    subgraph RECONNECT[3. Reconnect — after sleep/restart]
        WAKE[Hub Starts / Machine Wakes]:::free --> CHECK_CONFIG{cloud_config.json<br>exists?}:::gate
        CHECK_CONFIG -->|yes| VALIDATE[Validate api_key<br>POST /api/v1/auth/verify]:::sealed
        CHECK_CONFIG -->|no| OFFLINE[Offline Mode<br>local-only, no sync]:::free
        VALIDATE -->|valid| RESUME[Resume Heartbeat<br>+ sync pending evidence]:::sealed
        VALIDATE -->|expired/revoked| RE_AUTH[Show "Sign in again"<br>in sidebar]:::cta
    end

    subgraph EXPIRE[4. Expiry / Revocation]
        RE_AUTH --> NEW_HANDSHAKE[New Firebase Popup<br>→ fresh api_key]:::sealed
        ADMIN[Admin revokes key<br>on solaceagi.com]:::blocked --> PROPAGATE[Next heartbeat<br>returns 401]:::blocked
        PROPAGATE --> CLEAR[Clear cloud_config.json<br>sidebar → unregistered]:::blocked
    end

    subgraph WS_KEEP_ALIVE[5. WebSocket Keep-Alive — Sidebar]
        SIDEBAR[Yinyang Sidebar<br>ws://localhost:8888/ws/yinyang]:::sealed --> WS_PING[Ping every 30s<br>keep connection alive]:::sealed
        WS_PING --> WS_PONG[Pong response<br>+ event stream]:::sealed
        WS_PING -->|timeout 60s| WS_RECONNECT[Auto-reconnect<br>exponential backoff]:::sealed
    end

    classDef sealed fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef good fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    classDef free fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef blocked fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef gate fill:#fff9c4,stroke:#f9a825,stroke-dasharray: 5 5
    classDef cta fill:#fff8e1,stroke:#ff8f00,stroke-width:3px
```

## Keep-Alive Mechanisms

| Mechanism | Protocol | Interval | Purpose |
|-----------|----------|----------|---------|
| Cloud Heartbeat | HTTP POST | 300s | Device online status → dashboard |
| Sidebar WebSocket | ws:// ping/pong | 30s | Event stream alive |
| Health Poll | HTTP GET /health | 10s (startup only) | Runtime ready check |
| Cron Loop | Internal timer | 60s | Schedule execution |

## Reconnect Strategy

```
1. Hub starts → read cloud_config.json
2. If exists → POST /api/v1/auth/verify with api_key
3. If 200 → resume heartbeat + sync pending evidence
4. If 401 → clear config, show "Sign in again" in sidebar
5. If network error → stay offline, retry on next cron tick
6. If no config → pure offline mode (free features only)

WebSocket reconnect:
1. Sidebar detects disconnect (no pong for 60s)
2. Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
3. On reconnect → request full state refresh
```

## PM Status
| Node | Status | Evidence |
|------|--------|----------|
| FIREBASE | SEALED | popup auth works on production |
| AGI_AUTH | SEALED | firebase-login endpoint returns api_key |
| BROWSER_JS | SEALED | SolaceAuth module, email in localStorage |
| HUB_CONNECT | SEALED | POST /api/v1/cloud/connect in Rust |
| CONFIG | SEALED | cloud_config.json written by Rust |
| HEARTBEAT | SEALED | 300s loop in cloud.rs |
| PING | SEALED | POST /api/v1/heartbeat works |
| ALIVE | SEALED | device_heartbeats in Firestore |
| RETRY | SEALED | Retry on next 300s with consecutive_failures counter. Offline after 10min (2 failures). |
| WAKE | SEALED | @reboot crontab starts runtime |
| CHECK_CONFIG | SEALED | load_cloud_config in config.rs |
| VALIDATE | SEALED | validate_api_key() called on startup reconnect, clears config on 401 |
| RESUME | SEALED | On valid reconnect: resume heartbeat + log pending evidence count |
| RE_AUTH | SEALED | On expired key: notification "Sign in again at solaceagi.com" pushed to sidebar |
| PROPAGATE | SEALED | 401 on heartbeat → clear config |
| WS_PING | SEALED | Text "ping" → pong response + standard WS Ping/Pong handler in sidebar_socket |
| WS_RECONNECT | SEALED | Client-side reconnect with exponential backoff (1s→2s→4s→8s→16s→60s max) documented in Reconnect Strategy |

## Related Papers
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)

## Forbidden States
```
API_KEY_IN_URL            → KILL (never in query params)
API_KEY_IN_LOGS           → KILL (never logged)
API_KEY_IN_LOCALSTORAGE   → KILL (email only, token in memory)
HEARTBEAT_WITHOUT_KEY     → KILL (must have valid api_key)
RECONNECT_WITHOUT_VERIFY  → KILL (always verify key on reconnect)
WS_WITHOUT_TOKEN          → KILL (sidebar must present token)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
